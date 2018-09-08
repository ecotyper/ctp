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
    订阅合约 subscribe
    """

    #----------------------------------------------------------------------
    def __init__(self, eventEngine):
        """
        API对象的初始化函数
        """
        # 事件引擎，所有数据都推送到其中，再由事件引擎进行分发
        self.__eventEngine = eventEngine
        self.q = Quote()

        # 请求编号，由api负责管理
        self.__reqid = 0

        # 以下变量用于实现连接和重连后的自动登陆
        self.__userid = ''
        self.__password = ''
        self.__brokerid = ''

    def login(self):
        api = self.q.CreateApi()
        spi = self.q.CreateSpi()
        self.q.RegisterSpi(spi)
        self.q.OnFrontConnected = self.onFrontConnected  # 交易服务器登陆相应

        self.q.RegCB()
        self.q.RegisterFront('tcp://180.168.146.187:10010')
        self.q.Init()

    def onFrontConnected(self):
        """服务器连接"""
        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = ('行情服务器连接成功')
        self.__eventEngine.put(event)

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
    def __init__(self, eventEngine):
        """API对象的初始化函数"""
        # 事件引擎，所有数据都推送到其中，再由事件引擎进行分发
        self.__eventEngine = eventEngine
        self.t = Trade()

        # 请求编号，由api负责管理
        self.__reqid = 0

        # 报单编号，由api负责管理
        self.__orderref = 0

        # 以下变量用于实现连接和重连后的自动登陆
        self.__userid = ''
        self.__password = ''
        self.__brokerid = ''

    def login(self):
        api = self.t.CreateApi()
        spi = self.t.CreateSpi()
        self.t.RegisterSpi(spi)
        self.t.OnFrontConnected = self.onFrontConnected  # 交易服务器登陆相应

        self.t.RegCB()
        self.t.RegisterFront('tcp://180.168.146.187:10000')
        self.t.Init()

    def onFrontConnected(self):
        """服务器连接"""
        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = ('交易服务器连接成功')
        self.__eventEngine.put(event)



########################################################################
class MainEngine:
    """主引擎，负责对API的调度"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.ee = EventEngine()         # 创建事件驱动引擎
        self.md = MdApi(self.ee)    # 创建API接口
        self.td = TdApi(self.ee)
        self.ee.start()                 # 启动事件驱动引擎
        self.ee.register(EVENT_LOG, self.p_log)  # 打印测试



    #----------------------------------------------------------------------
    def login(self):
        """登陆"""
        self.md.login()
        self.td.login()
    def p_log(self,event):
        print(event.dict_['log'])



# 直接运行脚本可以进行测试
if __name__ == '__main__':
    import sys
    from PyQt5.QtCore import QCoreApplication
    app = QCoreApplication(sys.argv)
    main = MainEngine()
    main.login()
    app.exec_()
