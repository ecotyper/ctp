
"""这里我们试图打造一个RPC 服务，可以通过它股票变动情况。该程序需要完成以下几个操作：

1) 监听RabbitMQ队列，从中读取实时股票报价数据
2) 将实时股票报价数据写入到Redis高速缓存中

"""

## 系统模块引入
import pika 
import time 
import json 
import logging


# encoding: UTF-8
"""
CTP的底层接口来自'HaiFeng'-PY-AT
简化封装采用VN.PY的结构
"""
from py_ctp.eventEngine import  *
from py_ctp.eventType import  *
from py_ctp.ctp_struct import *
from py_ctp.quote import Quote
from py_ctp.trade import Trade
import time
import _thread


########################################################################
class MdApi:
    """
    Demo中的行情API封装
    封装后所有数据自动推送到事件驱动引擎中，由其负责推送到各个监听该事件的回调函数上
    封装RabbitMQClient
    对用户暴露的主动函数包括:
    登陆 login
    订阅合约行情 subscribe
　　  行情数据导向rabbitmq
    """
    logging.getLogger().setLevel(logging.INFO)
    #----------------------------------------------------------------------
    def __init__(self,RabbitMQClient):
        """
        API对象的初始化函数
        """

        self.q = Quote()
        self.RabbitMQClient = RabbitMQClient

        # 请求编号，由api负责管理
        self.__reqid = 0

        # 以下变量用于实现连接和重连后的自动登陆
        self.__userid = '123'
        self.__password = '123'
        self.__brokerid = '9999'
       
        #以下变量用于rabbitmq
        


    def login(self):
        api = self.q.CreateApi()
        spi = self.q.CreateSpi()
        self.q.RegisterSpi(spi)
        self.q.OnFrontConnected = self.onFrontConnected  # 行情服务器登陆相应
        self.q.OnRspUserLogin = self.onRspUserLogin  # 用户登陆

        self.q.OnRspSubMarketData=self.onRspSubMarketData  #tick返回调用
        self.q.OnRtnDepthMarketData = self.onRtnDepthMarketData   

        self.q.RegCB()
        self.q.RegisterFront('tcp://180.168.146.187:10010')
        self.q.Init()

    #创建rabbitmq交换器
    def publish(self):
        self.RabbitMQClient.declare_exchange('livedata')   #建立'livedata'通道
        self.RabbitMQClient.declare_queue('live_data_queue')
        self.RabbitMQClient.queue_bind('live_data_queue', 'livedata')

    def onFrontConnected(self):
        """服务器连接"""
        logging.info("行情服务器连接成功") 
        self.q.ReqUserLogin(BrokerID=self.__brokerid, UserID=self.__userid, Password=self.__password)  #登录请求


    def onRspUserLogin(self, data, error, n, last):    #登录请求返回信息
        """登陆回报"""
        if error.__dict__['ErrorID'] == 0:
            log = '行情服务器登陆成功'
            self.subscribe('IF1809')
        else:
            log = '登陆回报，错误代码：' + str(error.__dict__['ErrorID']) + ',   错误信息：' + str(error.__dict__['ErrorMsg']) 
        logging.info(log)

    def onRspSubMarketData(self, data, info, n, last):
        pass

    def onRtnDepthMarketData(self, data):
        """行情推送"""
        # 特定合约行情事件
        event = Event(type_=EVENT_MARKETDATA_CONTRACT)
        event.symbol= data.__dict__['InstrumentID']        
        event.dict_['data'] = data.__dict__
        self.RabbitMQClient.do_publish(json.dumps(event.dict_['data']), 'livedata')

    def subscribe(self, instrumentid):
        """订阅合约"""
        self.q.SubscribeMarketData(pInstrumentID=instrumentid)

    def unsubscribe(self, instrumentid):
        """退订合约"""
        self.q.UnSubscribeMarketData(pInstrumentID=instrumentid)
########################################################################

'''
1.设计一个类作为rabbitmq的api管理

2.设置两个通道，一个行情通道，一个通道用于机器学习结果的交易指令通道

3.行情通道与交易前置进行关联，主要负责与业务无关的通讯工作，如各类市场行情数据的订阅。行情通道按照股票代码申明队列

4.有关合约查询，对账单等直接在tdapi中处理，无需进入rabbitmq

5.交易指令通道结果直接关联tdapi

6. 行情通道采用扇形发布，一个队列用于rabbitmq的消费者端即为整个storm topology的spout，我们一方面可以自己开发spout，并且在spout中维护rabbitmq的链接，可以采用spring-rabbit进行访问。另一方面，github上流行着一个storm-rabbitmq的开源程序，本文即是采用此方法来使用该框架来集成storm-rabbitmq.　一个队列用于储存到redis数据库中


'''
class RabbitMQClient:
    def __init__(self, conn_str):         
        self.routing_key = "#"             # 路由键初始化
        self.exchange_type = "fanout"      #　交换器类型定义
        self.connection_string = "amqp:guest:guest@rabbitmq:5672/%2Fconnection_attempts=20&retry_delay=20"  # 参数conn_str = 'amqp://RightICMQ:ICHJ_678!@120.76.190.87:5672/%2F?heartbeat_interval=1&'
        self.connection = None             #连接初始化
        self.channel = None                #通道声明初始化

    def open_connection(self):　　　　         #建立连接获得通道，pika提供了两种认证方式：ConnectinParameters和URLParameters。
        self.connection = pika.BlockingConnection(pika.URLParameters(self.connection_string))
        self.channel = self.connection.channel()
        logging.info("成功连接Rabbitmq服务器")

    def close_connection(self):
        self.connection.close()
        logging.infor("成功关闭Rabbitmq服务器")
 
    def declare_exchange(self, exchange):   #对通道参数exchange的通道声明交换器
        self.channel.exchange_declare(exchange=exchange,
                                      exchange_type=self.exchange_type,
                                      durable=True)

    def declare_queue(self, queue):   #声明队列
        self.channel.queue_declare(queue=queue,
                                   durable=True,
                                   arguments={
                                       'x-dead-letter-exchange': 'RetryExchange'
                                   })

    #参数x-dead-letter-exchange，这表示拒绝的消息都会自动被放到此参数指定的交换器。
    def queue_bind(self, queue, exchange):  #通过键将队列和交换器绑定
        self.channel.queue_bind(queue=queue,
                                exchange=exchange,
                                routing_key=self.routing_key)

    def do_publish(self, msg, exchange):    #发布信息
        self.channel.basic_publish(exchange=exchange,
                                   routing_key=self.routing_key,
                                   body=msg,
                                   properties=pika.BasicProperties(
                                       delivery_mode=2,
                                       type=exchange
                                   ))

    def declare_retry_queue(self):
        """
        创建异常交换器和队列，用于存放没有正常处理的消息。
        :return:
        """
        self.channel.exchange_declare(exchange='RetryExchange',
                                      exchange_type='fanout',
                                      durable=True)
        self.channel.queue_declare(queue='RetryQueue',
                                   durable=True)
        self.queue_bind('RetryQueue', 'RetryExchange') 

########################################################################

class TdApi:
    """
    Demo中的交易API封装
    主动函数包括：
    login 登陆
    getInstrument 查询合约信息
    getAccount 查询账号资金
    getInvestor 查询投资者
    getPosition 查询持仓
    sendOrder 发单
    cancelOrder 撤单
    """

    #----------------------------------------------------------------------
    def __init__(self):
        """API对象的初始化函数"""

        self.t = Trade()

        # 请求编号，由api负责管理
        self.__reqid = 0

        # 报单编号，由api负责管理
        self.__orderref = 0

        # 以下变量用于实现连接和重连后的自动登陆
        self.__userid = '099829'
        self.__password = '123456'
        self.__brokerid = '9999'

    def login(self):
        api = self.t.CreateApi()
        spi = self.t.CreateSpi()
        self.t.RegisterSpi(spi)
        self.t.OnFrontConnected = self.onFrontConnected  # 交易服务器登陆相应
        self.t.OnRspUserLogin = self.onRspUserLogin  # 用户登陆
        self.t.OnRtnInstrumentStatus = self.OnRtnInstrumentStatus  #这个函数在合约交易状态发生改变时会被调用（会通知当前交易所状态变化开市，休市，闭市时）

        self.t.RegCB()
        self.t.RegisterFront('tcp://180.168.146.187:10000')  #注册前置地址
        self.t.Init()                                        #初始化接口线程

    def onFrontConnected(self):
        """交易服务器连接"""
        logging.info("交易服务器连接成功")   #也可以直接print("交易服务器连接成功") 
        self.t.ReqUserLogin(BrokerID=self.__brokerid, UserID=self.__userid, Password=self.__password)
        #返回onRspUserLogin和OnRtnInstrumentStatus两个回报，

    def OnRtnInstrumentStatus(self, data):            #合约的情况，pass不处理信息
        pass


    def onRspUserLogin(self, data, error, n, last):
        """登陆回报"""
        if error.__dict__['ErrorID'] == 0:
            self.Investor = data.__dict__['UserID']
            self.BrokerID = data.__dict__['BrokerID']
            log = data.__dict__['UserID'] + '交易服务器登陆成功'
            #self.t.ReqSettlementInfoConfirm(self.BrokerID, self.Investor)  # 对账单确认，现在时注销状态
        else:
            log = '登陆回报，错误代码：' + str(error.__dict__['ErrorID']) + ',   错误信息：' + str(error.__dict__['ErrorMsg'])
        logging.info(log)


########################################################################
class MainEngine:
    """主引擎，负责对API的调度"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.RabbitMQClient = RabbitMQClient()   #创建rabbitmq连接
        self.md = MdApi(self.RabbitMQClient)    # 创建API接口
        self.td = TdApi()

    #----------------------------------------------------------------------
    def login(self):
        """登陆"""
        self.md.login()
        self.td.login()
#----------------------------------------------------------------------



# 直接运行脚本可以进行测试
if __name__ == '__main__':
    import sys
    from PyQt5.QtCore import QCoreApplication
    app = QCoreApplication(sys.argv)
    main = MainEngine()
    main.login()
    app.exec_()
