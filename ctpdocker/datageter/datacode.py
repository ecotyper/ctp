
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

    对用户暴露的主动函数包括:
    登陆 login
    订阅合约行情 subscribe
　　  行情数据导向rabbitmq
    """
    logging.getLogger().setLevel(logging.INFO)
    #----------------------------------------------------------------------
    def __init__(self):
        """
        API对象的初始化函数
        """

        self.q = Quote()

        # 请求编号，由api负责管理
        self.__reqid = 0

        # 以下变量用于实现连接和重连后的自动登陆
        self.__userid = '123'
        self.__password = '123'
        self.__brokerid = '9999'

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
        print(event.dict_['data'])

    def subscribe(self, instrumentid):
        """订阅合约"""
        self.q.SubscribeMarketData(pInstrumentID=instrumentid)

    def unsubscribe(self, instrumentid):
        """退订合约"""
        self.q.UnSubscribeMarketData(pInstrumentID=instrumentid)
########################################################################

#留给rabbitmq服务器

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

        self.md = MdApi()    # 创建API接口
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
