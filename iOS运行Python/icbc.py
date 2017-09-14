# -*- coding: utf-8 -*-
"""
Created on Thu Jan  5 17:02:41 2017

@author: lwx
@bank: ICBC Bank
"""

import base64
import json
import re
import time
import datetime

from bs4 import BeautifulSoup
import requests
import traceback
import urllib.parse
# from pip._vendor.distlib.compat import raw_input

class Bank():
    '''工商银行爬虫
    '''
    #初始化配置信息
    def initCfg(self, params):
        if 'cfg' not in params.keys():
            return
        
        try:
            cfg = json.loads(params['cfg'])
            if 'serviceUrl' in cfg.keys():
                self.crawlerServiceUrl = cfg['serviceUrl']
            if 'logUrl' in cfg.keys():
                self.uploadExceptionUrl = cfg['logUrl']
        except Exception:
            return
   
    def init(self, params = None):
        
        #防止重复初始化覆盖新值
        if not hasattr(self, 'crawlerServiceUrl'):
            self.crawlerServiceUrl = 'http://192.168.1.82:8081/creditcrawler/common/service'
        if not hasattr(self, 'uploadExceptionUrl'):
            self.uploadExceptionUrl = 'http://192.168.1.82:8081/creditcrawler/base/addErrorInfo'
            
        #self.crawlerServiceUrl = 'http://192.168.1.82:8081/creditcrawler/common/service'
        #self.jiamiUrl = 'http://192.168.1.82:8081/creditcrawler/bank/getEncryptParams'
        self.jiamiUrl = 'http://api.edata.yuancredit.com/bankEncrypt/'
        #self.jiamiUrl = 'http://10.10.10.74:8888/bankEncrypt/'
        #self.uploadExceptionUrl = 'http://192.168.1.82:8081/creditcrawler/base/addErrorInfo'    
        
        if params :
            self.initCfg(self, params)  
   
    
        self.session = requests.Session()

        self.DEBUG = False
        self.DEBUG_LOCAL = False
        self.RECORD_COUNT = 0
        self.URI = ''
        self.encripCode = ''
        self.errExceptInfo = {}
        self.transList = {}
        self.status = 'true'
        self.UserId = ''
        self.creditCardNum = ''

        result = {
            'status':'true',
            'again':'true',
            'step':'0',
            'words':[
                        {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'网银用户名或卡号', 'type': 'text'},
                        {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                        {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                    ]
        }
        return json.dumps(result)

    def doCapture(self,jsonParams):
        try:
            return Bank.doCapture1(self,jsonParams)
        except:
            print(traceback.format_exc())
            ErrCode = ''
            if 'requests.exceptions.ConnectionError' in traceback.format_exc():
                ErrCode = '网络连接异常'
                respText = 'Code_000 except:  requests.exceptions.ConnectionError 网络连接异常'
            else:
                respText = 'Code_000 except:'+traceback.format_exc()
            Bank.uploadException(self,self.UserId,'doCapture',respText)
            result = {
                'status':'true',
                'again':'true',
                'step':'0',
                'msg':'操作失败,Code:000 '+ErrCode,
                'words':[
                            {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                            {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                            {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                        ]
            }
            return json.dumps(result)


    def doCapture1(self,jsonParams):
        self.jsonParams = json.loads(jsonParams)
        self.flowNo = self.jsonParams['flowNo']

        #step 0
        if self.jsonParams.get('step')=='0':
            print('0')
            if 'DEBUG' in self.jsonParams:
                if self.jsonParams['DEBUG'] == '1':
                    self.DEBUG = True
                else:
                    self.DEBUG = False
            else:
                self.DEBUG = False
            if 'DEBUG_LOCAL' in self.jsonParams:
                if self.jsonParams['DEBUG_LOCAL'] == '1':
                    self.DEBUG_LOCAL = True
                else:
                    self.DEBUG_LOCAL = False
            else:
                self.DEBUG_LOCAL = False
                
            self.UserId = self.jsonParams['UserId']
            self.UserId = self.UserId.replace(' ', '')
            self.password = self.jsonParams['password']
            self.password = self.password.replace(' ', '')
            self.MobilePhone = self.jsonParams['MobilePhone']
            self.MobilePhone = self.MobilePhone.replace(' ', '')

            Bank.uploadException(self,self.UserId,'step 0','calling icbc init:'+self.UserId+' - '+self.password + ' - '+ str(self.MobilePhone))

            #打开账号主页 frame_index
            Cookie = 'ICBC_AD_ClientZONENO_DATE=2016-12-29; ICBC_AD_ClientZONENO_DATA=4000; isP3bank=1; guide_nologon=Thu, 28 Dec 2017 09:00:19 UTC; firstZoneNo=%E6%B7%B1%E5%9C%B3_4000; BIGipServerMyBankVIP_80_POOL=419559434.20480.0000; mainAreaCode=4000; first_tip=0; isP3bank=1'
            fi_url = 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp'
            fi_headers = {
                'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'zh-CN',
                'Connection': 'Keep-Alive',
                'Host': 'mybank.icbc.com.cn',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2;  QIHU 360EE)'
            }
            
            fi_resp = self.session.get(fi_url, headers = fi_headers, verify=False)
            svrId = re.compile(r'var serviceId = \"(.*?)\"', re.S | re.M | re.I).findall(fi_resp.text)
            soup = BeautifulSoup(fi_resp.text,'html.parser')
            self.zoneNo  = soup.find('input',attrs={'name':'zoneNo'}).get('value')
            if len(svrId) > 0:
                self.serviceId = svrId[0]
                print('self.serviceId:' + self.serviceId)
            else:
                print('fail can not find self.serviceId \n')
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'0',
                    'msg':'初始化失败,Code:001',
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                return json.dumps(result)

         
            #获取loginall.jsp   登录iFrame页面   获取randomId
            '''Cookie = 'guide_nologon=Thu, 28 Dec 2017 09:00:19 UTC; firstZoneNo=%E6%B7%B1%E5%9C%B3_4000; BIGipServerMyBankVIP_80_POOL=419559434.20480.0000; mainAreaCode=4000; isP3bank=1; first_tip=0'
            loginall_url = 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/login/loginall.jsp'
            loginall_header = {
                'Accept': 'text/html, application/xhtml+xml, */*',
                'Referer': 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp',
                'Accept-Language': 'zh-CN',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E;  QIHU 360EE)',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'mybank.icbc.com.cn',
                'Connection': 'Keep-Alive'
            }
            loginall_resp = self.session.get(loginall_url, headers = loginall_header, verify=False)
            #print('loginall_url cookie: ', requests.utils.dict_from_cookiejar(self.session.cookies))
            soup = BeautifulSoup(loginall_resp.content,'html.parser')
            rIDs = soup.find_all('input',attrs={'name':'randomId'})
            self.randomId = ''
            if len(rIDs) > 0:
                self.randomId = rIDs[0]['value']
            print('self.randomId:'+str(self.randomId))
             
            rIDs = soup.find_all('input',attrs={'name':'ComputID'})
            ComputID = ''
            if len(rIDs) > 0:
                ComputID = rIDs[0]['value']
            print('ComputID:'+str(ComputID))
             
            rIDs = soup.find_all('input',attrs={'name':'PlatFlag'})
            PlatFlag = ''
            if len(rIDs) > 0:
                PlatFlag = rIDs[0]['value']
            print('PlatFlag:'+str(PlatFlag))
             
            rIDs = soup.find_all('input',attrs={'name':'requestChannelzoneNo'})
            requestChannelzoneNo = ''
            if len(rIDs) > 0:
                requestChannelzoneNo = rIDs[0]['value']
            print('requestChannelzoneNo:'+str(requestChannelzoneNo))
            
            ClientIP = re.compile(r'clientIP = \'(.*?)\'', re.S | re.M | re.I).findall(loginall_resp.text)
            if len(ClientIP) > 0:
                self.clientIp = str(ClientIP[0])
                print('self.clientIp:' + self.clientIp)
            
            self.zoneNo = requestChannelzoneNo   #'0200'    by lwx 20170106
            time.sleep(0.5)'''
            self.clientIp =''
#             self.zoneNo = ''
            
            
            #ICBCPERBANKLocationServiceServlet
            Cookie = 'eADValue=20161229; isP3bank=1; guide_nologon=Thu, 28 Dec 2017 09:00:19 UTC; firstZoneNo=%E6%B7%B1%E5%9C%B3_4000; BIGipServerMyBankVIP_80_POOL=419559434.20480.0000; mainAreaCode=4000; isP3bank=1; first_tip=0'
            '''loc_url = 'https://mybank.icbc.com.cn/servlet/ICBCPERBANKLocationServiceServlet'
            loc_headers = {
                'Accept': 'text/html, application/xhtml+xml, */*',
                'Referer': 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp',
                'Accept-Language': 'zh-CN',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E;  QIHU 360EE)',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'mybank.icbc.com.cn',
                'Connection': 'Keep-Alive'
            }
            loc_data = 'transData=&serviceId='+self.serviceId+'&zoneNo=4000&serviceIdInto=&dse_sessionId=&isflot=0&Language=zh_CN&requestChannel=302'
            loc_resp = self.session.post(loc_url, headers = loc_headers, data=loc_data,verify=False)
            '''
            
            loginUrl = 'https://epass.icbc.com.cn/login/login.jsp?StructCode=1&orgurl=0&STNO=43'
            loginHeader = {
                   'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'zh-CN',
                   'Connection': 'Keep-Alive',
                   'Host': 'epass.icbc.com.cn',
                   'Referer': 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp',
                   'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)'
                }
            loginresp = self.session.get(loginUrl, headers = loginHeader, verify=False)
            login_Soup = BeautifulSoup(loginresp.text,'html.parser')
            loginStr = loginresp.text
#             print(loginStr)
            
            searchstr = ".setChangeRules('"
            endStr = "');"
            start = loginStr.find(searchstr)
            end = loginStr.find( endStr , start)
            self.setChangeRules = loginStr[start + len( searchstr ) : end]
            print( self.setChangeRules)
            
            searchstr = ".setRules('"
            endStr = "');"
            start = loginStr.find(searchstr)
            end = loginStr.find( endStr , start)
            self.setRules = loginStr[start + len( searchstr ) : end]
            print(self.setRules)
            
            searchstr = ".setRandom('"
            endStr = "');"
            start = loginStr.find(searchstr)
            end = loginStr.find( endStr , start)
            self.setRandom = loginStr[start + len( searchstr ) : end]
            print(self.setRandom)
            
            searchstr = '<input name="randomId" type="hidden" value="'
            endStr = '" />'
            start = loginStr.find(searchstr)
            end = loginStr.find( endStr , start)
            randomId = loginStr[start + len( searchstr ) : end]
            print(randomId)
            self.randomId = randomId
            #1111
            time.sleep(0.5)
            
            
            LocSS_url = 'https://mybank.icbc.com.cn/servlet/ICBCPERBANKLocationServiceServlet'
            LocSS_header = {
                'Accept': 'text/html, application/xhtml+xml, */*',
                'Referer': 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp',
                'Accept-Language': 'zh-CN',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0;  QIHU 360EE)',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'mybank.icbc.com.cn',
                'Connection': 'Keep-Alive',
                'Cache-Control': 'no-cache',
                'Content-Length': '115'
            }
            LocSS_data = 'transData=&serviceId='+ self.serviceId +'&zoneNo='+ self.zoneNo +'&serviceIdInto=&dse_sessionId=&isflot=0&Language=zh_CN&requestChannel=302'
            try:
                isSuccess = False
                LocSS_resp = self.session.post(LocSS_url,headers=LocSS_header,data=LocSS_data,verify=False)
#                 print(LocSS_resp.text)
                isSuccess = True
            except:
                print(traceback.format_exc)
            #通过randomId  获取验证码
            #第一次请求获取 disFlag=2&isCn=0
            '''verify1_url = 'https://mybank.icbc.com.cn/servlet/com.icbc.inbs.person.servlet.Verifyimage2?randomKey='+self.randomId+'&imgheight=36&imgwidth=95'
            print(verify1_url)
            verify1_headers = {
                'Accept': 'text/html, application/xhtml+xml, */*',
                'Referer': loginall_url,
                'Accept-Language': 'zh-CN',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E;  QIHU 360EE)',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'mybank.icbc.com.cn',
                'Referer':'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/login/loginall.jsp',
                'Connection': 'Keep-Alive'
            }'''
            verify1_url = 'https://epass.icbc.com.cn/servlet/ICBCVerificationCodeImageCreate?randomId='+ self.randomId +'&height=36&width=90'
            verify1_headers = {
                   'Accept': '*/*',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'zh-CN',
                   'Connection': 'Keep-Alive',
            #        Cookie: isP3bank=0; epass_Language=zh_CN; epass_Struct=1
                   'Host': 'epass.icbc.com.cn',
                   'Referer': 'https://epass.icbc.com.cn/login/login.jsp?StructCode=1&orgurl=0&STNO=43',
                   'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)'
                }
            verify1_resp = self.session.get(verify1_url, headers = verify1_headers, verify=False)
            #print('verify_url1 cookie: ', requests.utils.dict_from_cookiejar(self.session.cookies))
            '''srcs = re.compile('\<img src=\"(.*?)\"', re.S | re.M | re.I).findall(verify1_resp.text)
            if len(srcs) > 0:
                verify2_url = 'https://mybank.icbc.com.cn'+srcs[0]
            else:
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'0',
                    'msg':'初始化失败,Code:002',
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                return json.dumps(result)            
            
            #第二次请求  获取验证码图片
            #verify_url2 = 'https://mybank.icbc.com.cn/servlet/com.icbc.inbs.person.servlet.Verifyimage2?disFlag=2&isCn=0&randomKey='+self.randomId+'&imgheight=36&imgwidth=95'
            print(verify2_url)
            verify2_headers = {
                'Accept': 'image/png, image/svg+xml, image/*;q=0.8, */*;q=0.5',
                'Referer': verify1_url,
                'Accept-Language': 'zh-CN',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E;  QIHU 360EE)',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'mybank.icbc.com.cn',
                'Connection': 'Keep-Alive'
            }
            verify2_resp = self.session.get(verify2_url, headers = verify2_headers, verify=False)
            #print('verify_url2 cookie: ', requests.utils.dict_from_cookiejar(self.session.cookies))'''
            
            if self.DEBUG_LOCAL:
                try :
                    #保存图片验证码
                    picCodePath = 'C:/work/temp/icbc.jpg'
                    binfile = open(picCodePath, 'wb')
                    binfile.write(verify1_resp.content)
                    binfile.close()
                    #print('保存图片验证码成功,路径:' + picCodePath)
                    print('self.randomId:'+self.randomId)
                except:
                    print('get piccode error')
                    result = {
                        'status':'true',
                        'again':'true',
                        'step':'0',
                        'msg':'初始化失败,Code:003',
                        'words':[
                                    {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                    {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                    {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                                ]
                    }
                    return json.dumps(result)
            
            try:
                byt = base64.b64encode(verify1_resp.content)
                self.PicCode_byt = byt.decode(encoding= 'utf-8')
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'1',
                    'msg':'请输入验证码',
                    'words':[
                                {'ID':'PicCode','index': '3','needUserInput':'true', 'label':'验证码', 'type': 'piccode', 'source':self.PicCode_byt}
                            ]
                }
                #需要输入验证码,以及正确的用户名密码
                return json.dumps(result)
            except:
                respText = 'PicCode_byt except:'+traceback.format_exc()
                Bank.uploadException(self,self.UserId,'doCapture',respText)
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'0',
                    'msg':'初始化失败,Code:004',
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                return json.dumps(result)
            
        if self.jsonParams.get('step')=='1':
            if self.DEBUG:
                #获取URI加密字符串
                self.URI = self.jsonParams.get('URI')
            else:
                self.PicCode = self.jsonParams['PicCode']
                self.PicCode = self.PicCode.replace(' ', '')
                
                
                
                #调用加密服务,获取加密后的URI
                #randomId,login_account,login_password,verifyCode,clientIp,serviceId,zoneNo, setChangeRule,setRules,setRandom
                Bank.jiamiData1(self, self.randomId, self.UserId, self.password, self.PicCode, self.clientIp, self.serviceId, self.zoneNo, self.setChangeRules, self.setRules, self.setRandom)
#                 self.URI = raw_input("self.URI:")
            if len(self.URI) < 20:
                respText = '系统繁忙,产生内部错误  except:'+self.URI+'      ||| randomId='+self.randomId+' password='+self.password+' UserId='+self.UserId+' PicCode='+self.PicCode+' clientIp='+self.clientIp+' serviceId='+self.serviceId+' zoneNo='+self.zoneNo + ' setChangeRules='+self.setChangeRules+' setRules='+ self.setRules+'  setRandom='+ self.setRandom
                Bank.uploadException(self,self.UserId,'doCapture Code:102 -->',respText)
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'0',
                    'msg':'系统繁忙,请退出重新验证',
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                time.sleep(1)
                return json.dumps(result)
                
            Cookie = 'eADValue=20161229; isP3bank=1; guide_nologon=Thu, 28 Dec 2017 09:00:19 UTC; firstZoneNo=%E6%B7%B1%E5%9C%B3_4000; BIGipServerMyBankVIP_80_POOL=419559434.20480.0000; mainAreaCode=4000; first_tip=0; isP3bank=1'
            '''estses_url = 'https://mybank.icbc.com.cn/servlet/com.icbc.inbs.servlet.ICBCINBSEstablishSessionServlet?'+self.URI'''
            
            estses_url = 'https://epass.icbc.com.cn/servlet/ICBCINBSEstablishSessionServlet'
            
            logHeader = {
               'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
               'Accept-Encoding': 'gzip, deflate',
               'Accept-Language': 'zh-CN',
               'Cache-Control': 'no-cache',
               'Connection': 'Keep-Alive',
               'Content-Type': 'application/x-www-form-urlencoded',
               'Host': 'epass.icbc.com.cn',
               'Referer': 'https://epass.icbc.com.cn/login/login.jsp?StructCode=1&orgurl=0&STNO=43',
               'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)'
            }
            '''estses_resp = self.session.get(estses_url, headers = estses_headers, verify=False)'''
            self.URI = self.URI.replace('"', "")
#             self.URI = self.URI.replace('"', "")
            #loginData = 'AutoVerify=4&requestChannelInput=302&requestChannelzoneNo=0200&serviceId=&serviceIdInto=&transData=&loginCardFlag=0&ua=Mozilla%2F4.0+%28compatible%3B+MSIE+7.0%3B+Windows+NT+10.0%3B+WOW64%3B+Trident%2F7.0%3B+.NET4.0C%3B+.NET4.0E%3B+.NET+CLR+2.0.50727%3B+.NET+CLR+3.0.30729%3B+.NET+CLR+3.5.30729%3B+InfoPath.2%29&language=zh-cn&netType=130&randomId='+ self.randomId +'&data=&ComputID=10&PlatFlag=0&logonSrc=1&serviceIdfirst=&orgurl=0&APPNO=43&ccsi=&resolution=1920*1080&logonCardNum='+ self.UserId +'&logonCardPass_cryptAlg=1&HWInfo=+&verifyCodeCn='+ self.PicCode +'&verifyCode='+ self.PicCode+'&'+ self.URI 
            #loginData = 'AutoVerify=4&requestChannelInput='+self.zoneNo+'&requestChannelzoneNo=1302&serviceId=&serviceIdInto=&transData=&loginCardFlag=0&ua=Mozilla%2F4.0+%28compatible%3B+MSIE+7.0%3B+Windows+NT+10.0%3B+WOW64%3B+Trident%2F7.0%3B+.NET4.0C%3B+.NET4.0E%3B+.NET+CLR+2.0.50727%3B+.NET+CLR+3.0.30729%3B+.NET+CLR+3.5.30729%3B+InfoPath.2%29&language=zh-cn&netType=130&randomId='+ self.randomId +'&data=&ComputID=10&PlatFlag=0&logonSrc=1&serviceIdfirst=&orgurl=0&APPNO=43&ccsi=&resolution=1920*1080&logonCardNum='+ self.UserId +'&logonCardPass_cryptAlg=1&HWInfo=+&verifyCodeCn='+ self.PicCode +'&verifyCode='+ self.PicCode+'&'+ self.URI
            loginData = 'AutoVerify=4&requestChannelInput=302&requestChannelzoneNo=0200&serviceId=&serviceIdInto=&transData=&loginCardFlag=0&ua=Mozilla%2F4.0+%28compatible%3B+MSIE+7.0%3B+Windows+NT+10.0%3B+WOW64%3B+Trident%2F7.0%3B+.NET4.0C%3B+.NET4.0E%3B+.NET+CLR+2.0.50727%3B+.NET+CLR+3.0.30729%3B+.NET+CLR+3.5.30729%3B+InfoPath.2%29&language=zh-cn&netType=130&randomId='+ self.randomId +'&data=&ComputID=10&PlatFlag=0&logonSrc=1&serviceIdfirst=&orgurl=0&APPNO=43&ccsi=&resolution=1920*1080&logonCardNum='+ self.UserId +'&logonCardPass_cryptAlg=1&HWInfo=+&verifyCodeCn='+ self.PicCode +'&verifyCode='+ self.PicCode+'&'+ self.URI
#             print(loginData) 
            #logresp = session.post(log_url, headers = logHeader , data = loginData, verify=False)
            #print(logresp.text)
            estses_resp = self.session.post(estses_url, headers = logHeader , data = loginData, verify=False)
            isSuccess = False
            self.dse_sessionId = ''
#             print(estses_resp.text)
#             print("----")
            ErrTip = '登录账号错误,请重新登录'
            if '连续输错超过3次' in str(estses_resp.text):
                ErrTip = '连续输错超过3次,请于次日重试'
            elif '验证码输入错误' in str(estses_resp.text):
                ErrTip = '验证码输入错误或已超时失效,请重新输入'+'['+self.PicCode+']'
            elif '用户名或者密码不正确' in str(estses_resp.text):
                ErrTip = '用户名或者密码不正确,请重新输入'
            elif '该卡非网银注册卡' in str(estses_resp.text):
                ErrTip = '该卡非网银注册卡'
            elif '支付卡号输入有误' in str(estses_resp.text):
                ErrTip = '卡号输入有误'
            elif 'showErrTip' in str(estses_resp.text):
                showErrTip = re.compile(r'showErrTip\((.*?)\)', re.S | re.M | re.I).findall(estses_resp.text)
                ErrTip = showErrTip[0]
                ErrTip = '登录账号错误,请重新登录'
                isSuccess = False
            else:
                #sucText = re.compile(r'perbankAtomLocationBW\((.*?)\)', re.S | re.M | re.I).findall(estses_resp.text)
                soup = BeautifulSoup(estses_resp.text,'html.parser')
                self.dse_sessionId  = soup.find('input',attrs={'name':'dse_sessionId'}).get('value')
                self.dse_applicationId  = soup.find('input',attrs={'name':'dse_applicationId'}).get('value')
                self.dse_operationName  = soup.find('input',attrs={'name':'dse_operationName'}).get('value')
                self.dse_pageId  = soup.find('input',attrs={'name':'dse_pageId'}).get('value')
                isSuccess = True
                '''if len(sucText) == 0:
                    isSuccess = False
                    ErrTip = '登录账号错误,请重新登录'
                else:
                    st = '['+sucText[0]+']'
                    stjson = json.loads(st)
                    self.dse_sessionId = stjson[2]
                    isSuccess = True'''

            if isSuccess == False:
                respText = '登录失败 except: --- PicCode:'+self.PicCode+' ---  '+self.URI+'  --'+self.password+'   text:'+str(estses_resp.text)
                Bank.uploadException(self,self.UserId,'doCapture Code:101 -->',respText)
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'0',
                    'msg':'操作错误 Code 013 '+ErrTip,
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                return json.dumps(result)
            
            #Bank.uploadException(self,self.UserId,'LoginSuccess','calling icbc login')
            
            
            afterLoginSuccessUrl = 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet'
            after_login_Header = {
                    'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'zh-CN',
                    'Cache-Control': 'no-cache',
                    'Connection': 'Keep-Alive',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Host': 'epass.icbc.com.cn',
                    'Referer': 'https://epass.icbc.com.cn/servlet/ICBCINBSEstablishSessionServlet',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)'
                }
            after_login_data = {
                    'dse_applicationId': self.dse_applicationId,
                    'dse_operationName': self.dse_operationName,
                    'dse_pageId': self.dse_pageId,
                    'dse_sessionId': self.dse_sessionId
                }
            after_login_resp = self.session.post(afterLoginSuccessUrl, headers = after_login_Header , data = after_login_data, verify=False)
#             print(after_login_resp.text)
#             print("---- 1")
            soup = BeautifulSoup(after_login_resp.text,'html.parser')
            self.dse_operationName  = soup.find('input',attrs={'name':'dse_operationName'}).get('value')
            self.dse_pageId = soup.find('input',attrs={'name':'dse_pageId'}).get('value')
            try:
                self.tranFlag = soup.find('input',attrs={'name':'tranFlag'}).get('value')
            except Exception:
                self.tranFlag = 'null'
            
            
            afterLoginSuccessUrl_1 = 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet'
            after_login_Header_1 = {
                    'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'zh-CN',
                    'Cache-Control': 'no-cache',
                    'Connection': 'Keep-Alive',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Host': 'epass.icbc.com.cn',
                    'Referer': 'https://epass.icbc.com.cn/servlet/ICBCINBSEstablishSessionServlet',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)'
                }
            after_login_data_1 = {
                    'dse_applicationId': self.dse_applicationId,
                    'dse_operationName': self.dse_operationName,
                    'dse_pageId': self.dse_pageId,
                    'dse_sessionId': self.dse_sessionId,
                    'tranFlag' :  self.tranFlag
                }
            after_login_resp_1 = self.session.post(afterLoginSuccessUrl_1, headers = after_login_Header_1 , data = after_login_data_1, verify=False)
#             print(after_login_resp_1.text)
#             print("---- 2")
            
            soup = BeautifulSoup(after_login_resp_1.text,'html.parser')
            self.dse_operationName  = soup.find('input',attrs={'name':'dse_operationName'}).get('value')
            self.dse_pageId = soup.find('input',attrs={'name':'dse_pageId'}).get('value')
            self.tranFlag = soup.find('input',attrs={'name':'tranFlag'}).get('value')
            try:
                self.requestTokenid = soup.find('input',attrs={'name':'requestTokenid'}).get('value')
            except Exception:
                self.requestTokenid = 'null'
            
            
#    请求 URL: https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet?dse_sessionId=GYHTHBHUJPHQGWDOELHQCWITJBATAHHPASIICHIK&requestTokenid=null&dse_applicationId=-1&dse_operationName=epass_userVerifyStepOp&dse_pageId=3&tranFlag=0
            afterLoginSuccessUrl_2 = 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet?dse_sessionId='+ self.dse_sessionId + '&requestTokenid=' + self.requestTokenid + '&dse_applicationId='+ self.dse_applicationId + '&dse_operationName=' + self.dse_operationName + '&dse_pageId='+ self.dse_pageId +'&tranFlag='+ self.tranFlag
            print(afterLoginSuccessUrl_2)
            after_login_Header_2 = {
                    'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'zh-CN',
                    'Connection': 'Keep-Alive',
                    'Host': 'epass.icbc.com.cn',
                    'Referer': 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)'
                }
            
            after_login_resp_2 = self.session.get(afterLoginSuccessUrl_2, headers = after_login_Header_2 ,  verify=False)
#             print(after_login_resp_2.text)
#             print("---- 3")
            soup = BeautifulSoup(after_login_resp_2.text,'html.parser')
            self.dse_operationName  = soup.find('input',attrs={'name':'dse_operationName'}).get('value')
            self.dse_pageId = soup.find('input',attrs={'name':'dse_pageId'}).get('value')
            self.tranFlag = soup.find('input',attrs={'name':'tranFlag'}).get('value')
            try:
                self.requestTokenid = soup.find('input',attrs={'name':'requestTokenid'}).get('value')
            except Exception:
                self.requestTokenid = 'null'
            
            
            afterLoginSuccessUrl_3 = 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet'
            after_login_Header_3 = {
                    'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'zh-CN',
                    'Cache-Control': 'no-cache',
                    'Connection': 'Keep-Alive',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Host': 'epass.icbc.com.cn',
                    'Referer': afterLoginSuccessUrl_2,
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)'
                }
            after_login_data_3 = {
                    'dse_applicationId': self.dse_applicationId,
                    'dse_operationName': self.dse_operationName,
                    'dse_pageId': self.dse_pageId,
                    'dse_sessionId': self.dse_sessionId,
                    'tranFlag' :  self.tranFlag,
                    'requestTokenid': self.requestTokenid
                    
                }
            
            after_login_resp_3 = self.session.post(afterLoginSuccessUrl_3, headers = after_login_Header_3 , data=after_login_data_3,  verify=False)
#             print(after_login_resp_3.text)
#             print("---- 4")
            try:
                soup = BeautifulSoup(after_login_resp_3.text,'html.parser')
                self.dse_pageId = soup.find('input',attrs={'name':'dse_pageId'}).get('value')
                self.isAsyncronizeSMS = soup.find('input',attrs={'name':'isAsyncronizeSMS'}).get('value')
                self.tranFlag  = soup.find('input',attrs={'name':'tranFlag'}).get('value')
                SendPhoneIn_option  = soup.find('select',attrs={'id':'SendPhoneIn'}).find_all('option')
                self.MobilePhoneVal = ''
                for item in SendPhoneIn_option:
                    txt = str(item.text).strip()
                    if(txt[0:3] == self.MobilePhone[0:3] and txt[len(txt)-4 : len(txt)] == self.MobilePhone[len( self.MobilePhone)-4 : len( self.MobilePhone)]):
    #                     print(item.get('value'))
                        self.MobilePhoneVal = item.get('value')
                        
                smsStr = after_login_resp_3.text
                
                searchstr = 'var smslimit='
                endStr = ';'
                start = smsStr.find(searchstr)
                end = smsStr.find( endStr , start)
                self.smslimit = smsStr[start + len( searchstr ) : end]
                self.smslimit = str(int(self.smslimit) - 1)
                
                
                searchstr = 'sendParam["tranFlag"] = "'
                endStr = '";'
                start = smsStr.find(searchstr)
                end = smsStr.find( endStr , start)
                self.tranFlag = smsStr[start + len( searchstr ) : end]
#                 print( self.tranFlag)
                
                tranFlags = re.compile('sendParam\[\"tranFlag\"\]=\"(.*?)\";', re.S | re.M | re.I).findall(smsStr)
                if len(tranFlags) > 0:
                    print('success,tranFlag:',tranFlags[0])
                    self.tranFlag = tranFlags[0]
                    isSuccess = True
                else:
                    print('can not find tranFlag')
                    isSuccess = False
                
                searchstr = 'sendParam["tranCode"]="'
                endStr = '";'
                start = smsStr.find(searchstr)
                end = smsStr.find( endStr , start)
                self.tranCode = smsStr[start + len( searchstr ) : end]
#                 print( self.tranCode)
                
                tranCodes = re.compile('sendParam\[\"tranCode\"\]=\"(.*?)\";', re.S | re.M | re.I).findall(smsStr)
                if len(tranCodes) > 0:
                    print('success,tranCodes:',tranCodes[0])
                    self.tranCode = tranCodes[0]
                    isSuccess = True
                else:
                    print('can not find tranCode')
                    isSuccess = False
                
            except:
                
                soup = BeautifulSoup(after_login_resp_3.text,'html.parser')
                self.dse_operationName  = soup.find('input',attrs={'name':'dse_operationName'}).get('value')
                self.dse_pageId = soup.find('input',attrs={'name':'dse_pageId'}).get('value')
                self.tranFlag = soup.find('input',attrs={'name':'tranFlag'}).get('value')
                try:
                    self.requestTokenid = soup.find('input',attrs={'name':'requestTokenid'}).get('value')
                except Exception:
                    self.requestTokenid = 'null'
                    
                self.tranFlag = '6'   
                afterLoginSuccessUrl_4 = 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet'
                after_login_Header_4 = {
                        'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                        'Accept-Encoding': 'gzip, deflate',
                        'Accept-Language': 'zh-CN',
                        'Cache-Control': 'no-cache',
                        'Connection': 'Keep-Alive',
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Host': 'epass.icbc.com.cn',
                        'Referer': 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet',
                        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)'
                    }
                after_login_data_4 = {
                        'dse_applicationId': self.dse_applicationId,
                        'dse_operationName': self.dse_operationName,
                        'dse_pageId': self.dse_pageId,
                        'dse_sessionId': self.dse_sessionId,
                        'tranFlag' :  self.tranFlag,
                        'requestTokenid': self.requestTokenid
                        
                    }
    #             print(after_login_data_4)
                after_login_resp_4 = self.session.post(afterLoginSuccessUrl_4, headers = after_login_Header_4, data = after_login_data_4  ,  verify=False)
    #             print(after_login_resp_4.text)
    #             print("---- 5")
                try:
                    smsStr = after_login_resp_4.text
                    
                    searchstr = 'sendParam["tranFlag"] = "'
                    endStr = '";'
                    start = smsStr.find(searchstr)
                    end = smsStr.find( endStr , start)
                    self.tranFlag = smsStr[start + len( searchstr ) : end]
#                     print( self.tranFlag)
                    
                    tranFlags = re.compile('sendParam\[\"tranFlag\"\]=\"(.*?)\";', re.S | re.M | re.I).findall(smsStr)
                    if len(tranFlags) > 0:
                        print('success,tranFlag:',tranFlags[0])
                        self.tranFlag = tranFlags[0]
                        isSuccess = True
                    else:
                        print('can not find tranFlag')
                        isSuccess = False
                    
                    searchstr = 'sendParam["tranCode"]="'
                    endStr = '";'
                    start = smsStr.find(searchstr)
                    end = smsStr.find( endStr , start)
                    self.tranCode = smsStr[start + len( searchstr ) : end]
#                     print( self.tranCode)
                    
                    tranCodes = re.compile('sendParam\[\"tranCode\"\]=\"(.*?)\";', re.S | re.M | re.I).findall(smsStr)
                    if len(tranCodes) > 0:
                        print('success,tranCodes:',tranCodes[0])
                        self.tranCode = tranCodes[0]
                        isSuccess = True
                    else:
                        print('can not find tranCode')
                        isSuccess = False
                except:
                    respText = 'loc_url except:'+traceback.format_exc()
                    Bank.uploadException(self,self.UserId,'doCapture Code:001 -->',respText)
                    isSuccess = False
                
                try:
                    searchstr = 'var smslimit='
                    endStr = ';'
                    start = smsStr.find(searchstr)
                    end = smsStr.find( endStr , start)
                    self.smslimit = smsStr[start + len( searchstr ) : end]
                    self.smslimit = str(int(self.smslimit) - 1)
                    
                    soup = BeautifulSoup(after_login_resp_4.text,'html.parser')
                    self.dse_pageId = soup.find('input',attrs={'name':'dse_pageId'}).get('value')
                    self.isAsyncronizeSMS = soup.find('input',attrs={'name':'isAsyncronizeSMS'}).get('value')
                    self.tranFlag  = soup.find('input',attrs={'name':'tranFlag'}).get('value')
                    SendPhoneIn_option  = soup.find('select',attrs={'id':'SendPhoneIn'}).find_all('option')
                    self.MobilePhoneVal = ''
                    for item in SendPhoneIn_option:
                        txt = str(item.text).strip()
                        if(txt[0:3] == self.MobilePhone[0:3] and txt[len(txt)-4 : len(txt)] == self.MobilePhone[len( self.MobilePhone)-4 : len( self.MobilePhone)]):
        #                     print(item.get('value'))
                            self.MobilePhoneVal = item.get('value')
                            break
                    if(self.MobilePhoneVal == ''):
                        respText = 'MobilePhoneVal except:'+self.MobilePhone+'  -->REgistered SendPhoneIn_option:'+SendPhoneIn_option
                        Bank.uploadException(self,self.UserId,'MobilePhoneVal Code:001 -->',respText)
                except:
                    respText = 'smslimit except:'+traceback.format_exc()+'  -->isSuccess:'+str(isSuccess)+'   -->smsStr:'+smsStr
                    Bank.uploadException(self,self.UserId,'doCapture Code:001 -->',respText)
                    isSuccess = False
                    result = {
                        'status':'true',
                        'again':'true',
                        'step':'0',
                        'msg':'操作错误 Code 013 ',
                        'words':[
                                    {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                    {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                    {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                                ]
                    }
                    return json.dumps(result)
            
            
            
            getVerifyCodeUrl = 'https://epass.icbc.com.cn/servlet/com.icbc.inbs.person.servlet.Verifyimage2?randomKey='+ self.dse_sessionId + '&imageAlt=点击图片可刷新'
            get_verify_header = {
                    'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'zh-CN',
                    'Connection': 'Keep-Alive',
                    'Host': 'epass.icbc.com.cn',
                    'Referer': 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)'
                }
            get_verify = self.session.get(getVerifyCodeUrl, headers = get_verify_header,  verify=False)
#             self.PicCode_byt2 = get_verify.content
            
            sms_verify_url = 'https://epass.icbc.com.cn/servlet/com.icbc.inbs.person.servlet.Verifyimage2?disFlag=2&randomKey='+ self.dse_sessionId + '&width=70&height=28'
            sms_verify_header = {
                    'Accept': '*/*',
                    'Referer': getVerifyCodeUrl,
                    'Accept-Language': 'zh-CN',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)',
                    'Accept-Encoding': 'gzip, deflate',
                    'Host': 'epass.icbc.com.cn',
                    'Connection': 'Keep-Alive'
                }
            sms_verify = self.session.get(sms_verify_url, headers = get_verify_header,  verify=False)
            self.PicCode_byt2 = sms_verify.content
            
            if self.DEBUG_LOCAL:
                #保存图片验证码
                picCodePath = 'C:/work/temp/smsVerify.jpg'
                binfile = open(picCodePath, 'wb')
                binfile.write(self.PicCode_byt2)
                binfile.close()
                
            getSms_Url = 'https://epass.icbc.com.cn/servlet/AsynGetDataServlet'
            getSms_header = {
                    'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'zh-CN',
                    'Cache-Control': 'no-cache',
                    'Connection': 'Keep-Alive',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Host': 'epass.icbc.com.cn',
                    'Referer': 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)'
                }
            get_sms_data = {
                    "tranFlag" : str(int(self.tranFlag) - 1),
                    "mobileRowIdin" : self.MobilePhoneVal,
                    "smslimit" : self.smslimit,
                    "SessionId" : self.dse_sessionId,
                    "tranCode" : self.tranCode
                }
#             print(get_sms_data)
            get_sms_resp = self.session.post(getSms_Url, headers = getSms_header, data = get_sms_data,  verify=False)
                
#             print(get_sms_resp.text)
            try:
                byt = base64.b64encode(sms_verify.content)
                self.PicCode_byt2 = byt.decode(encoding= 'utf-8') 
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'2',
                    'msg':'请输入验证码',
                    'words':[
                                {'ID':'smsCode','index': 0,'needUserInput':'true', 'label':'短信验证码', 'type': 'text'},
                                {'ID':'verifyCode','index': '1','needUserInput':'true', 'label':'验证码', 'type': 'piccode', 'source':self.PicCode_byt2}
                            ]
                }
                #需要输入验证码,以及正确的用户名密码
                return json.dumps(result)
            except:
                respText = 'PicCode_byt except:'+traceback.format_exc()
                Bank.uploadException(self,self.UserId,'doCapture 003',respText)
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'0',
                    'msg':'初始化失败,Code:007',
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                return json.dumps(result)
            

        if self.jsonParams.get('step')=='2':
            if self.DEBUG:
                #获取URI加密字符串
                self.URI = self.jsonParams.get('URI')
            else:
                smsCode = self.jsonParams.get('smsCode')
                verifyCode = self.jsonParams.get('verifyCode')
                smsCode = smsCode.replace(' ', '')
                verifyCode = verifyCode.replace(' ', '')
                #调用加密服务,获取加密后的URI
                Bank.jiamiData2(self, verifyCode, self.clientIp, self.dse_sessionId)
                #self.encripCode = raw_input("Enter:")
                self.encripCode = self.encripCode.replace('"', "")

            if type(self.encripCode) == None:
                ErrTip = '系统繁忙2,请退出重新验证'
                respText = '系统繁忙2,产生内部错误  except:'+self.jmresp2+' verifyCode='+verifyCode+' clientIp='+self.clientIp+' dse_sessionId='+self.dse_sessionId
                Bank.uploadException(self,self.UserId,'doCapture Code:112 -->',respText)
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'0',
                    'msg':ErrTip,
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                time.sleep(1)
                return json.dumps(result)
            
            if len(self.encripCode) < 10:
                ErrTip = '系统繁忙22,请退出重新验证'
                respText = '系统繁忙22,产生内部错误  except:'+self.jmresp2+' verifyCode='+verifyCode+' clientIp='+self.clientIp+' dse_sessionId='+self.dse_sessionId
                Bank.uploadException(self,self.UserId,'doCapture Code:112 -->',respText)
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'0',
                    'msg':ErrTip,
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                time.sleep(1)
                return json.dumps(result)
            
            ErrTip = ''
            #ICBCINBSReqServlet   二次验证(短信)提交
            ReqS_url = 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet'
            ReqS_header = {
                'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                'Referer': 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet',
                'Accept-Language': 'zh-CN',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'epass.icbc.com.cn',
                'Connection': 'Keep-Alive',
                'Cache-Control': 'no-cache'
            }
            print('self.randomId:'+str(self.randomId))
            try:
                isSuccess = False
                ReqS_data = 'dse_sessionId='+str(self.dse_sessionId)+'&requestTokenid='+str(self.requestTokenid)+'&dse_applicationId='+str(self.dse_applicationId)+'&dse_operationName='+self.dse_operationName+'&dse_pageId='+str(self.dse_pageId)+'&isAsyncronizeSMS='+str(self.isAsyncronizeSMS)+'&tranFlag='+str(self.tranFlag)+'&randomId='+str(self.dse_sessionId)+'&operationTimesFlag=&userSubmitSignVerifyCode='+str(smsCode)+'&interval=26&'+self.encripCode
                ReqS_resp = self.session.post(ReqS_url, headers=ReqS_header, data=ReqS_data, verify=False)
                isSuccess = True
                soup = BeautifulSoup(ReqS_resp.text,'html.parser')
                self.dse_applicationId  = soup.find('input',attrs={'name':'dse_applicationId'}).get('value')
                self.dse_operationName  = soup.find('input',attrs={'name':'dse_operationName'}).get('value')
                self.dse_pageId  = soup.find('input',attrs={'name':'dse_pageId'}).get('value')
                self.requestTokenid  = soup.find('input',attrs={'name':'requestTokenid'}).get('value')
#                 print(ReqS_resp.text)
            except:
                respText = 'ReqS except 0071:'+ReqS_resp.text + '   traceback:' + traceback.format_exc()
                Bank.uploadException(self,self.UserId,'doCapture Code:0071 -->',respText)
                isSuccess = False
            
            if isSuccess:
                if 'success.png' in ReqS_resp.text:
                    print('success in the second login')
                    Bank.uploadException(self,self.UserId,'doCapture second login-->',"success in the second login")
                else:
                    print("not success")
                    respText = 'ReqS except 0072: smsCode:'+smsCode+' --- verifyCode:'+verifyCode+' --- encripCode:'+self.encripCode+' --- '+ str(ReqS_data) + '---' +ReqS_resp.text
                    Bank.uploadException(self,self.UserId,'doCapture Code:0072 -->',respText)
                    if '验证码输入错误' in ReqS_resp.text:
                        ErrTip = '验证码输入错误或已超时失效'+'['+smsCode+' | '+verifyCode+']'
                    result = {
                        'status':'true',
                        'again':'true',
                        'step':'0',
                        'msg':'验证失败,请重新登录 Code:0072 '+ErrTip,
                        'words':[
                                    {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                    {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                    {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                                ]
                    }
                    return json.dumps(result)
            if isSuccess == False:
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'0',
                    'msg':'操作失败,Code:007',
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                return json.dumps(result)
            try:
                ReqS_url = 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet'
                ReqS_header = {
                    'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                    'Referer': 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet',
                    'Accept-Language': 'zh-CN',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept-Encoding': 'gzip, deflate',
                    'Host': 'epass.icbc.com.cn',
                    'Connection': 'Keep-Alive',
                    'Cache-Control': 'no-cache'
                }
                    #'Cookie' : 'epass_Struct='+ self.session.cookies['epass_Struct'] +'; isP3bank='+ self.session.cookies['isP3bank'] +'; isP3bank='+ self.session.cookies['isP3bank'] +'; epass_Language=' + self.session.cookies['epass_Language'] 
    #             ReqS_PostData = 'dse_sessionId='+ self.dse_sessionId +'&requestTokenid='+ str(self.requestTokenid) +'&dse_applicationId='+ str(self.dse_applicationId) +'&dse_operationName='+ str(self.dse_operationName) +'&dse_pageId=' + str(self.dse_pageId)
                ReqS_PostData = {
                        'dse_sessionId' : self.dse_sessionId,
                        'requestTokenid' : self.requestTokenid,
                        'dse_applicationId' : self.dse_applicationId,
                        'dse_operationName' : self.dse_operationName,
                        'dse_pageId' : self.dse_pageId
                    }
                ReqS_resp = self.session.post(ReqS_url, headers=ReqS_header, data=ReqS_PostData, verify=False)
                soup = BeautifulSoup(ReqS_resp.text,'html.parser')
                netType  = soup.find('input',attrs={'name':'netType'}).get('value')
                signDataToApp  = soup.find('input',attrs={'name':'signDataToApp'}).get('value')
                encryptedDataToApp  = soup.find('input',attrs={'name':'encryptedDataToApp'}).get('value')
            except:
                respText = 'netType :'+ str(ReqS_PostData) + str(ReqS_resp.text) + "_" + traceback.format_exc()
                Bank.uploadException(self,self.UserId,'doCapture netType -->',respText)
                
                ReqS_url = 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet'
                ReqS_header = {
                    'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                    'Referer': 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet',
                    'Accept-Language': 'zh-CN',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept-Encoding': 'gzip, deflate',
                    'Host': 'epass.icbc.com.cn',
                    'Connection': 'Keep-Alive',
                    'Cache-Control': 'no-cache'
                }
                try:
                    soup = BeautifulSoup(ReqS_resp.text,'html.parser')
                    dse_applicationId  = soup.find('input',attrs={'name':'dse_applicationId'}).get('value')
                    dse_operationName = soup.find('input',attrs={'name':'dse_operationName'}).get('value')
                    dse_pageId = soup.find('input',attrs={'name':'dse_pageId'}).get('value')
                    tranFlag = soup.find('input',attrs={'name':'tranFlag'}).get('value')
                    ReqS_PostData = {
                            'dse_sessionId' : self.dse_sessionId,
                            'dse_applicationId' : dse_applicationId,
                            'dse_operationName' : dse_operationName,
                            'dse_pageId' : dse_pageId,
                            'tranFlag' : tranFlag
                        }
                    ReqS_resp = self.session.post(ReqS_url, headers=ReqS_header, data=ReqS_PostData, verify=False)
                    soup = BeautifulSoup(ReqS_resp.text,'html.parser')
                    netType  = soup.find('input',attrs={'name':'netType'}).get('value')
                    signDataToApp  = soup.find('input',attrs={'name':'signDataToApp'}).get('value')
                    encryptedDataToApp  = soup.find('input',attrs={'name':'encryptedDataToApp'}).get('value')
                    
                except:
                    respText = 'netType exception :'+ str(ReqS_PostData) + str(ReqS_resp.text) + "_" + traceback.format_exc()
                    Bank.uploadException(self,self.UserId,'doCapture netType -->',respText)
                    result = {
                        'status':'true',
                        'again':'true',
                        'step':'0',
                        'msg':'操作失败,Code:007',
                        'words':[
                                    {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                    {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                    {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                                ]
                    }
                    return json.dumps(result)
                
                
            try:
                establishSessionServlet = 'https://mybank.icbc.com.cn//servlet/com.icbc.inbs.servlet.ICBCINBSEstablishSessionServlet'
                establishSession_header = {
                    'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                    'Referer': 'https://epass.icbc.com.cn/servlet/ICBCINBSReqServlet',
                    'Accept-Language': 'zh-CN',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2;  QIHU 360EE)',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept-Encoding': 'gzip, deflate',
                    'Host': 'mybank.icbc.com.cn',
                    'Connection': 'Keep-Alive',
                    'Cache-Control': 'no-cache',
                    'Content-Length': '472'
                    #'Cookie': 'eADValue=20170720; guide_nologon=Tue, 17 Jul 2018 06:25:33 UTC; guide_logon=Fri, 20 Jul 2018 07:21:50 UTC; BIGipServerMyBankVIP_80_POOL=3875665930.20480.0000; mainAreaCode=4000; firstZoneNo=%E6%B7%B1%E5%9C%B3_4000; first_tip=0; isEn_US=0; isP3bank=1'
                    }
                    #'Cookie': 'eADValue=20170720; guide_nologon=Tue, 17 Jul 2018 06:25:33 UTC; guide_logon=Fri, 20 Jul 2018 07:21:50 UTC; mainAreaCode=4000; firstZoneNo=%E6%B7%B1%E5%9C%B3_4000; first_tip=0; isEn_US=0;  isP3bank=1; epass_Language=' + self.session.cookies['epass_Language']  + ';BIGipServerMyBankVIP_80_POOL=' + self.session.cookies['BIGipServerMyBankVIP_80_POOL']
                #establishSession_postData = 'netType='+ netType +'&signDataToApp='+ signDataToApp +'&encryptedDataToApp=' + encryptedDataToApp
                establishSession_postData = {
                        'netType' : netType,
                        'signDataToApp' : signDataToApp,
                        'encryptedDataToApp' : encryptedDataToApp
                    }
                ReqS_resp = self.session.post(establishSessionServlet, headers=establishSession_header, data=establishSession_postData, verify=False)
                soup = BeautifulSoup(ReqS_resp.text,'html.parser')
                self.dse_sessionId  = soup.find('input',attrs={'name':'dse_sessionId'}).get('value')
            except:
                respText = 'establishSession except:'+traceback.format_exc() + "result:" + str(ReqS_resp.text)
                Bank.uploadException(self,self.UserId,'doCapture Code:008 -->',respText)
                Bank.uploadException(self,self.UserId,'establishSession_postData:008 -->',str(establishSession_postData))
                isSuccess = False
            
            #二次验证成功后 打开frame_index
            findex_url = 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp'
            findex_header = {
                'Accept': 'text/html, application/xhtml+xml, */*',
                'Referer': 'https://mybank.icbc.com.cn//servlet/com.icbc.inbs.servlet.ICBCINBSEstablishSessionServlet',
                'Accept-Language': 'zh-CN',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0;  QIHU 360EE)',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'mybank.icbc.com.cn',
                'Connection': 'Keep-Alive',
                'Cache-Control': 'no-cache'
            }
            print('self.serviceId:************'+self.serviceId)
            self.serviceId = 'PBL200202'
            findex_data = 'transData=&serviceId='+self.serviceId+'&zoneNo='+self.zoneNo+'&serviceIdInto=&dse_sessionId='+self.dse_sessionId+'&isflot=0&Language=zh_CN&requestChannel=302'
            try:
                #isSuccess = False
                findex_resp = self.session.post(findex_url,headers=findex_header,data=findex_data,verify=False)
                soup = BeautifulSoup(findex_resp.text,'html.parser')
                rIDs = soup.find_all('input',attrs={'name':'zoneNo'})
                self.zoneNo = ''
                if len(rIDs) > 0:
                    self.zoneNo = rIDs[0]['value']
                print('self.zoneNo:'+str(self.zoneNo))
                rIDs = soup.find_all('input',attrs={'name':'requestChannel'})
                requestChannel = ''
                if len(rIDs) > 0:
                    requestChannel = rIDs[0]['value']
                print('requestChannel:'+str(requestChannel))
#                 self.serviceId = ''
                self.serviceId = soup.find('input',attrs={'name':'serviceId'}).get('value')
                tranCodes = re.compile('sendParam\[\"tranCode\"\]=\"(.*?)\";', re.S | re.M | re.I).findall(findex_resp.text)
                print(tranCodes)
                if len(tranCodes) > 0:
                    print('success finding tranCode: ',tranCodes[0])
                    self.tranCode = tranCodes[0]
                else:
                    print('fail finding tranCode \n')
                    self.tranCode = 'A00491'
                    
                result = findex_resp.text
                #print(result)
                searchstr = "frames['ICBC_login_frame_f'].location="
                endStr = '";'
                start = result.find(searchstr)
                end = result.find( endStr , start)
                loginUrl = result[start + len( searchstr ) : end]
                loginUrl = loginUrl.replace('"', "")
                #print(loginUrl)
                Bank.uploadException(self,self.UserId,'doCapture Code:008 loginUrl',str(loginUrl))
                isSuccess = True
                
                
            except:
                respText = 'findex except:'+traceback.format_exc()
                Bank.uploadException(self,self.UserId,'doCapture Code:008 -->',respText)
                isSuccess = False
            if isSuccess == False:
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'0',
                    'msg':'操作失败,Code:008',
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                return json.dumps(result)
            
            
            #二次验证成功后 loginall
            #loginall_url = 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/login/loginall.jsp'
            if 'submitFirstForm' in loginUrl:
                
                loginall_url = 'https://epass.icbc.com.cn/login/login.jsp?StructCode=1&orgurl=0&STNO=30'
                Bank.uploadException(self,self.UserId,'doCapture Code:008 inside loginUrl',str(loginall_url))
            else:
                loginall_url = loginUrl
            loginall_header = {
                'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                'Referer': 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp',
                'Accept-Language': 'zh-CN',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2)',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'epass.icbc.com.cn',
                'Connection': 'Keep-Alive'
            }
            try:
                loginall_resp = self.session.get(loginall_url,headers=loginall_header,verify=False)
                soup = BeautifulSoup(loginall_resp.text,'html.parser')
                rIDs = soup.find_all('input',attrs={'name':'randomId'})
                self.randomId = ''
                if len(rIDs) > 0:
                    self.randomId = rIDs[0]['value']
                print('self.randomId:'+str(self.randomId))
                isSuccess = True
            except:
                respText = 'loginall except:'+traceback.format_exc()
                Bank.uploadException(self,self.UserId,'doCapture Code:009 -->',respText)
                isSuccess = False
            if isSuccess == False:
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'0',
                    'msg':'操作失败,Code:009',
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                return json.dumps(result)
            
            login_after = 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/login/login_after.jsp?dse_sessionId=' + self.dse_sessionId
            login_after_header = {
                    'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                    'Referer': 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp',
                    'Accept-Language': 'zh-CN',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2;  QIHU 360EE)',
                    'Accept-Encoding': 'gzip, deflate',
                    'Host': 'mybank.icbc.com.cn',
                    'Connection': 'Keep-Alive'
                }
            login_after_resp = self.session.get(login_after, headers=login_after_header, verify=False)
            
            login_afterformsg = 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/login/login_afterformsg.jsp?dse_sessionId=' + self.dse_sessionId
            login_after_header = {
                    'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                    'Referer': 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp',
                    'Accept-Language': 'zh-CN',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2;  QIHU 360EE)',
                    'Accept-Encoding': 'gzip, deflate',
                    'Host': 'mybank.icbc.com.cn',
                    'Connection': 'Keep-Alive'
                }
            login_afterformsg_resp = self.session.get(login_afterformsg, headers=login_after_header, verify=False)
            
            login_iframe_sub = 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/index/index_favorite_iframe_sub.jsp?&dse_sessionId=' + self.dse_sessionId +'&rflag=my&Cust_Group_Num=&View_Prod_Group_Num=&Prod_Type_Cd=&Prod_Num='
            login_after_header = {
                    'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                    'Referer': 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp',
                    'Accept-Language': 'zh-CN',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2;  QIHU 360EE)',
                    'Accept-Encoding': 'gzip, deflate',
                    'Host': 'mybank.icbc.com.cn',
                    'Connection': 'Keep-Alive'
                }
            login_afterformsg_resp = self.session.get(login_iframe_sub, headers=login_after_header, verify=False)
            
            soup = BeautifulSoup(login_afterformsg_resp.text,'html.parser')
            self.dse_operationName = soup.find_all('input',attrs={'name':'dse_operationName'})
            rflag = soup.find_all('input',attrs={'name':'rflag'})
            dse_pageId = soup.find_all('input',attrs={'name':'dse_pageId'})
            
            
            
            #AsynGetDataServlet
            asynGetDS_url = 'https://mybank.icbc.com.cn/servlet/AsynGetDataServlet'
            asynGetDS_header = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': findex_url,
                'Accept-Language': 'zh-CN',
                'Accept-Encoding': 'gzip, deflate',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0;  QIHU 360EE)',
                'Host': 'mybank.icbc.com.cn',
                'Connection': 'Keep-Alive',
                'Cache-Control': 'no-cache'
            }
            asynGetDS_data = 'SessionId='+self.dse_sessionId+'&actionType=0&tranCode='+self.tranCode
            print('asynGetDS_data111:',asynGetDS_data)
            try:
                isSuccess = False
                asynGetDS_resp = self.session.post(asynGetDS_url,headers=asynGetDS_header,data=asynGetDS_data,verify=False)
                #{"filepath":null,"commonFucStr":"2","returnCode":"0"}
#                 print('asynGetDS_resp:'+asynGetDS_resp.text)
                gdsJson = json.loads(asynGetDS_resp.text)
                if 'returnCode' in gdsJson.keys():
                    if gdsJson['returnCode'] == '0':
                        print('asynGetDS success')
                    else:
                        print('asynGetDS fail:')#+gdsJson['commonFucStr'])
                isSuccess = True
            except:
                respText = 'asynGetDS except:'+traceback.format_exc()
                Bank.uploadException(self,self.UserId,'doCapture Code:010 -->',respText)
                isSuccess = False
            if isSuccess == False:
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'0',
                    'msg':'操作失败,Code:010',
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                return json.dumps(result)
            
            tranCodes = re.compile('sendParam\[\"tranCode\"\]=\"(.*?)\";', re.S | re.M | re.I).findall(login_afterformsg_resp.text)
#             print(tranCodes)
            if len(tranCodes) > 0:
                print('success finding tranCode: ',tranCodes[0])
                self.tranCode = tranCodes[0]
            else:
                print('fail finding tranCode \n')
                self.tranCode = 'A00477'
            print(self.tranCode)     
            
            
            #LocSS
            LocSS_url = 'https://mybank.icbc.com.cn/servlet/ICBCPERBANKLocationServiceServlet'
            LocSS_header = {
                'Accept': 'text/html, application/xhtml+xml, */*',
                'Referer': findex_url,
                'Accept-Language': 'zh-CN',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0;  QIHU 360EE)',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'mybank.icbc.com.cn',
                'Connection': 'Keep-Alive',
                'Cache-Control': 'no-cache'
            }
            LocSS_data = 'transData=&serviceId='+self.serviceId+'&zoneNo='+self.zoneNo+'&serviceIdInto=&dse_sessionId='+self.dse_sessionId+'&isflot=0&Language=zh_CN&requestChannel='+requestChannel
            try:
                isSuccess = False
                LocSS_resp = self.session.post(LocSS_url,headers=LocSS_header,data=LocSS_data,verify=False)
                isSuccess = True
            except:
                respText = 'asynGetDS except:'+traceback.format_exc()
                Bank.uploadException(self,self.UserId,'doCapture Code:011 -->',respText)
                isSuccess = False
            if isSuccess == False:
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'0',
                    'msg':'操作失败,Code:011',
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                return json.dumps(result)
            
            
            asynGetData = 'https://mybank.icbc.com.cn/servlet/AsynGetDataServlet'
            asynGetData_header = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://mybank.icbc.com.cn/servlet/ICBCPERBANKLocationServiceServlet',
                'Accept-Language': 'zh-CN',
                'Accept-Encoding': 'gzip, deflate',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2;  QIHU 360EE)',
                'Host': 'mybank.icbc.com.cn',
                'Connection': 'Keep-Alive',
                'Cache-Control': 'no-cache'
            
            }
            asynGetData_postData = 'SessionId='+ self.dse_sessionId+'&tranCode='+ self.tranCode +'&Tranflag=0'
            try:
                isSuccess = False
                asynGetData_resp = self.session.post(asynGetData, headers=asynGetData_header, data=asynGetData_postData, verify=False)
                isSuccess = True
            except:
                respText = 'asynGetDS except:'+traceback.format_exc()
                Bank.uploadException(self,self.UserId,'doCapture Code:011 -->',respText)
                isSuccess = False
            self.GD_serviceId = 'PBL200711'
            
            self.account_info = {}
            self.account_info['bank_code'] = 'ICBC'
            self.account_info['bankName'] = '工商银行'
            self.account_info['account_type'] = 'DebitCard'   
            self.account_info['flow_no'] = self.flowNo
            self.account_info['account_status'] = 'OK'
            
            self.account_info['translist'] = []
            self.account_info['loanList'] = []
            self.account_info['creditCardInfos'] = []
            
            loanList = []
            loanItem = {}
            loanDetail = []
            loanDetailItem = {}
            
            creditCardInfos = []
            creditCardInfo ={}
            cardsInfo = []
            historyBills =[]
            historyBillDetail =[]
            unsettledBillDetail = []
            
            isFindMybank7 = False
            #查询银行卡
            MyBank_url = 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/includes/mybank.jsp?dse_sessionId='+self.dse_sessionId
            MyBank_header = {
                'Accept': 'text/html, application/xhtml+xml, */*',
                'Referer': LocSS_url,
                'Accept-Language': 'zh-CN',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0;  QIHU 360EE)',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'mybank.icbc.com.cn',
                'Connection': 'Keep-Alive'
            }
            cardlistdata = ''
            cardNum = ''
            creditCardNum =''
            try:
                isSuccess = False
                MyBank_resp = self.session.get(MyBank_url,headers=MyBank_header,verify=False)
                soup = BeautifulSoup(MyBank_resp.text,'html.parser')
                forms = soup.find_all('form',attrs={'name':'form2'})
                mybank1 = soup.find('iframe',attrs={'id':'mybank1'}).get('src')
                mybank1Url = 'https://mybank.icbc.com.cn' + mybank1
                
                str1 =  MyBank_resp.text
                searchstr = "window.mybank7.location = '"
                endStr = "';"
                start = str1.find(searchstr)
                end = str1.find( endStr , start)
                self.ICBCINBSReqServlet = str1[start + len( searchstr ) : end]
                self.ICBCINBSReqServlet = 'https://mybank.icbc.com.cn' + self.ICBCINBSReqServlet
#                 print( self.ICBCINBSReqServlet)
                
                searchstr = 'currType="'
                endStr = '";'
                start = str1.find(searchstr)
                end = str1.find( endStr , start)
                currType = str1[start + len( searchstr ) : end]
#                 print( currType)
                
                
                if len(forms) > 0:
                    form = forms[0]
                    nIDs = form.find_all('input',attrs={'name':'requestTokenid'})
                    if len(nIDs) > 0:
                        requestTokenid = nIDs[0]['value']
                    nIDs = form.find_all('input',attrs={'name':'dse_applicationId'})
                    if len(nIDs) > 0:
                        dse_applicationId = nIDs[0]['value']
                    nIDs = form.find_all('input',attrs={'name':'dse_operationName'})
                    if len(nIDs) > 0:
                        dse_operationName = nIDs[0]['value']
                    nIDs = form.find_all('input',attrs={'name':'dse_pageId'})
                    if len(nIDs) > 0:
                        dse_pageId = nIDs[0]['value']
                
                sIDs = re.compile('window.mybank7.location = \'\/servlet\/ICBCINBSReqServlet\?(.*?)\'\;', re.S | re.M | re.I).findall(MyBank_resp.text)
                
                if len(sIDs) > 0:
                    bank7 = sIDs[0]
                    self.bankJson = postdata_map(bank7)
                    isFindMybank7 = True
                
                sIDs = re.compile('var cardlistdata(.*?)\;', re.S | re.M | re.I).findall(MyBank_resp.text)
                isFind = False
                if len(sIDs) > 0:
                    cardlistdata = sIDs[0]
                    cardlistdata = cardlistdata.replace(' ','')
                    cardlistdata = cardlistdata.replace('=','')
                    clJson = json.loads(cardlistdata)
                    accs = clJson['accountCardList']
                    Bank.uploadException(self,self.UserId,'accs Code:024 -->',str(accs))
                    for acc in accs:
                        if acc['cardType']=='011':    #cardType='007'信用卡   '011'储蓄卡
                            cardNum = acc['cardNum']
                            regCardNum = acc['cardNum']
                            entranceId = acc['entranceId']
                            cardtype = acc['cardType']
                            areaname = acc['areaName']
                            openAreaCode = acc['areaCode']
                            menuFlag = acc['menuFlag']
                            acctNum = acc['acctNo0']
                            regmode = acc['cardregmode']
                            isFind = True
                            break
                        elif acc['cardType'] == '007':
                            creditCardNum = acc['cardNum']
                            cardType = acc['cardType']
                            cardAliasName = acc['cardalias']
                            '''cardNum = acc['cardNum']
                            cardtype = acc['cardType']'''
                            
                            cardsInfo.append({'cardNo':creditCardNum,'cardType':cardType,'ownerName':'','cardAliasName':cardAliasName,'openFlag':'开卡'})
                                
                isSuccess = True
            except:
                respText = 'MyBank_url except:'+cardlistdata+' --||--  '+traceback.format_exc()+'  \n'+MyBank_resp.text
                Bank.uploadException(self,self.UserId,'doCapture Code:024 -->',respText)
                isSuccess = False
            if isSuccess == False:
                result = {
                    'status':'true',
                    'again':'true',
                    'step':'0',
                    'msg':'操作失败,Code:024',
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                return json.dumps(result)
            
            mybank1_header = {
                'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                'Referer': 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/includes/mybank.jsp?dse_sessionId=' + self.dse_sessionId,
                'Accept-Language': 'zh-CN',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2;  QIHU 360EE)',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'mybank.icbc.com.cn',
                'Connection': 'Keep-Alive'
                }
            mybank1 = self.session.get(mybank1Url, headers=mybank1_header, verify=False)
            soup = BeautifulSoup(mybank1.text,'html.parser')
            mybank1str = mybank1.text
            searchstr = 'sendParam["tranCode"]="'
            endStr = '";'
            start = mybank1str.find(searchstr)
            end = mybank1str.find( endStr , start)
            self.tranCode = mybank1str[start + len( searchstr ) : end]
            print( self.tranCode)
            
            
            icbcinBs_header = {
                    'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, application/x-ms-xbap, application/vnd.ms-excel, application/msword, */*',
                    'Referer': 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/includes/mybank.jsp?dse_sessionId=' + self.dse_sessionId,
                    'Accept-Language': 'zh-CN',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.2;  QIHU 360EE)',
                    'Accept-Encoding': 'gzip, deflate',
                    'Host': 'mybank.icbc.com.cn',
                    'Connection': 'Keep-Alive'
                }
            icbcinBs_resp = self.session.get(self.ICBCINBSReqServlet, headers=icbcinBs_header, verify=False)
            soup = BeautifulSoup(icbcinBs_resp.text,'html.parser')
            
            self.availbalance = 0
            asynGetDS_url = 'https://mybank.icbc.com.cn/servlet/AsynGetDataServlet'
            asynGetDS_header = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': mybank1Url,
                'Accept-Language': 'zh-CN',
                'Accept-Encoding': 'gzip, deflate',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0;  QIHU 360EE)',
                'Host': 'mybank.icbc.com.cn',
                'Connection': 'Keep-Alive',
                'Cache-Control': 'no-cache' 
            }
            asynGetDS_data = 'tranFlag=0&SessionId='+ self.dse_sessionId +'&tranCode=' + self.tranCode
            asynGetDS_resp = self.session.post(asynGetDS_url,headers=asynGetDS_header,data=asynGetDS_data,verify=False)
#             print(asynGetDS_resp.text)
            
            
            searchstr = 'sendParam["tranCode"]="'
            endStr = '";'
            mybank1str = icbcinBs_resp.text 
            start = mybank1str.find(searchstr)
            end = mybank1str.find( endStr , start)
            self.tranCode = mybank1str[start + len( searchstr ) : end]
            print( self.tranCode)
            
            asynGetDS_header = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': self.ICBCINBSReqServlet,
                'Accept-Language': 'zh-CN',
                'Accept-Encoding': 'gzip, deflate',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0;  QIHU 360EE)',
                'Host': 'mybank.icbc.com.cn',
                'Connection': 'Keep-Alive',
                'Cache-Control': 'no-cache' 
            }
            #asynGetDS_data = 'ajaxFlag=1&SessionId='+ self.dse_sessionId +'&tranCode=' + self.tranCode
            asynGetDS_data = {
                    'SessionId' : self.dse_sessionId,
                    'ajaxFlag': '1',
                    'tranCode': self.tranCode
                }
            asynGetDS_resp = self.session.post(asynGetDS_url,headers=asynGetDS_header,data=asynGetDS_data,verify=False)
#             print(asynGetDS_resp.text)
            
            
            searchstr = 'sendParam["tranCode"]="'
            endStr = '";'
            mybank1str = MyBank_resp.text 
            start = mybank1str.find(searchstr)
            end = mybank1str.find( endStr , start)
            self.tranCode = mybank1str[start + len( searchstr ) : end]
            print( self.tranCode)
            
            if cardNum: 
                asynGetDS_header = {
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': MyBank_url,
                    'Accept-Language': 'zh-CN',
                    'Accept-Encoding': 'gzip, deflate',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0;  QIHU 360EE)',
                    'Host': 'mybank.icbc.com.cn',
                    'Connection': 'Keep-Alive',
                    'Cache-Control': 'no-cache' 
                }
                asynGetDS_data = 'SessionId='+ self.dse_sessionId +'&cardNum='+ cardNum +'&acctNum=&acctType='+ cardtype +'&acctCode=00000&cashSign=0&currType='+ currType +'&align=&operatorFlag=0&tranflag=0&tranCode='+self.tranCode
                asynGetDS_resp = self.session.post(asynGetDS_url,headers=asynGetDS_header,data=asynGetDS_data,verify=False)
    #             print(asynGetDS_resp.text)
                
                nCount = 3
                acctCode = '00000'
                
                #此serviceId不知道从何而来
                #self.GD_serviceId = 'PBL200711'
                
                GDLocSS_url = 'https://mybank.icbc.com.cn/servlet/ICBCPERBANKLocationServiceServlet'
                GDLocSS_header = {
                    'Accept': 'text/html, application/xhtml+xml, */*',
                    'Referer': GDLocSS_url,
                    'Accept-Language': 'zh-CN',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0;  QIHU 360EE)',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept-Encoding': 'gzip, deflate',
                    'Host': 'mybank.icbc.com.cn',
                    'Connection': 'Keep-Alive',
                    'Cache-Control': 'no-cache'
                }
                GDLocSS_data = 'transData='+cardNum+'||no|000||myacct|&serviceId='+self.GD_serviceId+'&zoneNo=&serviceIdInto=&requestChannel=302&dse_sessionId='+self.dse_sessionId
                try:
                    isSuccess = False
                    GDLocSS_resp = self.session.post(GDLocSS_url,headers=GDLocSS_header,data=GDLocSS_data,verify=False)
                    isSuccess = True
                except:
                    respText = 'GDLocSS except:'+traceback.format_exc()
                    Bank.uploadException(self,self.UserId,'doCapture Code:020 -->',respText)
                    isSuccess = False
                if isSuccess == False:
                    result = {
                        'status':'true',
                        'again':'true',
                        'step':'0',
                        'msg':'操作失败,Code:020',
                        'words':[
                                    {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                    {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                    {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                                ]
                    }
                    return json.dumps(result)
                
                
                #GDAcctQryHis_url = 'https://mybank.icbc.com.cn/icbc/newperbank/account/account_query_hisdetail.jsp?card_Num='+cardNum+'&acct_Type=no&acct_Code=000&from_Mark=myacct&dse_sessionId='+self.dse_sessionId
                GDAcctQryHis_url = 'https://mybank.icbc.com.cn/servlet/ICBCINBSReqServlet?dse_operationName=per_AccountQueryHisdetailOp&firstInjectFlag=0&card_Num='+ cardNum +'&acct_Type=no&acct_Code=000&from_Mark=myacct&dse_sessionId='+self.dse_sessionId
                GDAcctQryHis_header = {
                    'Accept': 'text/html, application/xhtml+xml, */*',
                    'Referer': GDLocSS_url,
                    'Accept-Language': 'zh-CN',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0;  QIHU 360EE)',
                    'Accept-Encoding': 'gzip, deflate',
                    'Host': 'mybank.icbc.com.cn',
                    'Connection': 'Keep-Alive'
                }
                try:
                    isSuccess = False
                    GDAcctQryHis_resp = self.session.get(GDAcctQryHis_url,headers=GDAcctQryHis_header,verify=False)
                    soup = BeautifulSoup(GDAcctQryHis_resp.text,'html.parser')
                    forms = soup.find_all('form',attrs={'name':'inforForm'})
                    
                    self.requestTokenid = ''
                    self.dse_applicationId = '-1'
                    self.dse_operationName = 'per_AccountQueryHisdetailOp'
                    self.dse_pageId = '6'
                    showNum = '20'
                    Areacode = '4000'
                    days = '20170105'
                    initDate = '2017:01:05'
                    initTime = '09:38:09'
                    if len(forms) > 0:
                        form = forms[0]
                        
                        rIDs = form.find_all('input',attrs={'name':'requestTokenid'})
                        if len(rIDs) > 0:
                            self.requestTokenid = rIDs[0]['value']
                        #print('self.requestTokenid:'+str(self.requestTokenid))
                        rIDs = form.find_all('input',attrs={'name':'dse_applicationId'})
                        if len(rIDs) > 0:
                            self.dse_applicationId = rIDs[0]['value']
                        #print('self.dse_applicationId:'+str(self.dse_applicationId))
                        rIDs = form.find_all('input',attrs={'name':'dse_operationName'})
                        if len(rIDs) > 0:
                            self.dse_operationName = rIDs[0]['value']
                        #print('self.dse_operationName:'+str(self.dse_operationName))
                        rIDs = form.find_all('input',attrs={'name':'dse_pageId'})
                        if len(rIDs) > 0:
                            self.dse_pageId = rIDs[0]['value']
                        #print('self.dse_pageId:'+str(self.dse_pageId))
                        rIDs = form.find_all('input',attrs={'name':'showNum'})
                        if len(rIDs) > 0:
                            showNum = rIDs[0]['value']
                        #print('showNum:'+str(showNum))
                        rIDs = form.find_all('input',attrs={'name':'Areacode'})
                        if len(rIDs) > 0:
                            Areacode = rIDs[0]['value']
                        #print('Areacode:'+str(Areacode))
                        rIDs = form.find_all('input',attrs={'name':'days'})
                        if len(rIDs) > 0:
                            days = rIDs[0]['value']
                        #print('days:'+str(days))
                        rIDs = form.find_all('input',attrs={'name':'initDate'})
                        if len(rIDs) > 0:
                            initDate = rIDs[0]['value']
                        #print('initDate:'+str(initDate))
                        rIDs = form.find_all('input',attrs={'name':'initTime'})
                        if len(rIDs) > 0:
                            initTime = rIDs[0]['value']
                        #print('initTime:'+str(initTime))
                    
                    acts = re.compile('new Account\((.*?)\)', re.S | re.M | re.I).findall(GDAcctQryHis_resp.text)
    #                 print(acts)
                    acounts = {}
                    acctCode = '00000'
                    for act in acts:
                        #print(act)
                        act = act.replace('\"','')
                        act = act.split(',')
                        if act[0] == 'true':
                            if act[1] not in acounts:
                                acounts[act[1]] = {}
                            acounts[act[1]]['cardType'] = act[6]
                            acounts[act[1]]['Areacode'] = act[12]
                        else:
                            if act[2] == acctCode:  #'00000'
                                if act[1] not in acounts:
                                    acounts[act[1]] = {}
                                acounts[act[1]]['acctCode'] = act[2]
                                acounts[act[1]]['acctNum'] = act[3]
                    isSuccess = True
                except:
                    respText = 'GDAcctQryHis except:'+traceback.format_exc()
                    Bank.uploadException(self,self.UserId,'doCapture Code:021 -->',respText)
                    isSuccess = False
                if isSuccess == False:
                    result = {
                        'status':'true',
                        'again':'true',
                        'step':'0',
                        'msg':'操作失败,Code:021',
                        'words':[
                                    {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                    {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                    {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                                ]
                    }
                    return json.dumps(result)
                
                #Bank.uploadException(self,self.UserId,'start Capture','start Capturing')
                
                nDays = 15
                if self.UserId == 'shelvenn':
                    nDays = 15
                else:
                    nDays = 365
                #构造13个月的时间差
                beginDate,endDate = Bank.get_pre_date(self, nDays)
                
    #             print('beginDate:'+beginDate)
    #             print('endDate:'+endDate)
                
                cardType = '011'
                #acctCode = '0000'
                acctNum = '4000029301110797991'
                
                self.account_info['login_account'] = cardNum 
                #self.account_info['account_balance'] = str(self.availbalance)
    
                
                GDReqS_url = 'https://mybank.icbc.com.cn/servlet/ICBCINBSReqServlet'
                GDReqS_header = {
                    'Accept': 'text/html, application/xhtml+xml, */*',
                    'Referer': GDAcctQryHis_url,
                    'Accept-Language': 'zh-CN',
                    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0;  QIHU 360EE)',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept-Encoding': 'gzip, deflate',
                    'Host': 'mybank.icbc.com.cn',
                    'Connection': 'Keep-Alive',
                    'Cache-Control': 'no-cache'
                }
                nCount = 0
                Begin_pos = '-1'
                incomeSum = ''
                timestmp = ''
                payoutSum = ''
                init_flag = '1'
                pageflag = '0'
                flag = ''
                dse_pageId = int(self.dse_pageId)
                translist = []
                try:
                    isSuccess = False
                    while True:
                        #GDReqS_data = 'dse_sessionId='+self.dse_sessionId+'&requestTokenid='+self.requestTokenid+'&dse_applicationId='+self.dse_applicationId+'&dse_operationName='+self.dse_operationName+'&dse_pageId='+str(dse_pageId)+'&cardOwnerMark1=&fromHDM=0&cardNum='+cardNum+'&cardType='+acounts[cardNum]['cardType']+'&acctCode='+acounts[cardNum]['acctCode']+'&acctNum='+acounts[cardNum]['acctNum']+'&Begin_pos='+str(Begin_pos)+'&acctIndex=1&Tran_flag=0&acctType=01&queryType=0&cardAlias=&acctAlias=&acctTypeName=01&currTypeName=&init_flag='+init_flag+'&type=browser&showNum='+showNum+'&incomeSum='+incomeSum+'&timestmp='+timestmp+'&payoutSum='+payoutSum+'&incomeSum1=&payoutSum1=&Areacode='+Areacode+'&pageflag='+pageflag+'&days='+days+'&flag='+flag+'&initDate='+initDate+'&initTime='+initTime+'&isupdate=0&data_flag=&ishere=0&qaccf=1&FovaAcctType=0&acctSelList2Temp=&Area=&drcrFlag=0&cardOrAcct=&payCardSnap=&payAcctSnap=&cityFlagSnap=&graylink=0&amedaiSnap=&ACSTYPE=0&ACAPPNO=&SKflag=0&onoffDJFlag=&onoffJJFlag=2&DRCRF_IN=0&begDate='+beginDate+'&endDate='+endDate+'&ishomecard=0&acctSelList=0&acctSelList2=1&YETYPE=0&styFlag=0'
                        GDReqS_data = 'dse_sessionId='+self.dse_sessionId+'&requestTokenid='+self.requestTokenid+'&dse_applicationId='+self.dse_applicationId+'&dse_operationName='+self.dse_operationName+'&dse_pageId='+str(dse_pageId)+'&cardOwnerMark1=&fromHDM=0&cardNum='+cardNum+'&cardType='+acounts[cardNum]['cardType']+'&acctCode=00000&acctNum='+acounts[cardNum]['acctNum']+'&Begin_pos='+str(Begin_pos)+'&acctIndex=1&Tran_flag=0&acctType=01&queryType=0&cardAlias=&acctAlias=&acctTypeName=01&currTypeName=&init_flag='+init_flag+'&type=browser&showNum='+showNum+'&incomeSum='+incomeSum+'&timestmp='+timestmp+'&payoutSum='+payoutSum+'&incomeSum1=&payoutSum1=&Areacode='+Areacode+'&pageflag='+pageflag+'&days='+days+'&flag='+flag+'&initDate='+initDate+'&initTime='+initTime+'&isupdate=0&data_flag=&ishere=0&qaccf=1&FovaAcctType=0&acctSelList2Temp=&Area=&drcrFlag=0&cardOrAcct=&payCardSnap=&payAcctSnap=&cityFlagSnap=&graylink=0&jiedaiSnap=&ACSTYPE=0&ACAPPNO=&SKflag=0&onoffDJFlag=&onoffJJFlag=2&DRCRF_IN=0&begDate='+beginDate+'&endDate='+endDate+'&ishomecard=0&acctSelList=0&acctSelList2=1&YETYPE=0&styFlag=0'
                        print('GDReqS_data:'+GDReqS_data)
                        GDReqS_resp = self.session.post(GDReqS_url,headers = GDReqS_header,data = GDReqS_data,verify=False)
                        soup = BeautifulSoup(GDReqS_resp.text,'html.parser')
                        tables = soup.find_all('table',attrs={'class':'lst tblWidth'})
                        if len(tables) > 0:
                            table = tables[0]
                            trs = table.find_all('tr')
                            for tr in trs:
                                tds = tr.find_all('td',attrs={'align':'center'})
                                if len(tds) == 0:
                                    continue
                                index = 0
                                trans_info = {}
                                for td in tds:
                                    index = index+1
                                    if (index % 7)==1:
                                        #print('交易日期:',td.get_text())
                                        transtime = td.get_text()
                                        transtime = transtime.replace('-','')+'000000'
                                        trans_info['trans_time'] = transtime
                                    if (index % 7)==2:
                                        #print('摘要:',td.get_text())
                                        trans_info['trans_remark'] = td.get_text()
                                    if (index % 7)==3:
                                        #print('收入/支出:',td.get_text())
                                        amount = td.get_text()
                                        amount = amount.replace(',','')
                                        if float(amount) > 0:
                                            trans_info['income_money'] = str(int(abs(float(amount)*100)))
                                        else:
                                            trans_info['pay_money'] = str(int(abs(float(amount)*100)))
                                    if (index % 7)==4:
                                        #print('币种:',td.get_text())
                                        trans_info['trans_currency'] = td.get_text()
                                    if (index % 7)==5:
                                        #print('余额:',td.get_text())
                                        amount = td.get_text()
                                        amount = amount.replace(',','')
                                        trans_info['balance'] = str(int(abs(float(amount)*100)))
                                    if (index % 7)==6:
                                        #print('对方信息:',td.get_text())
                                        trans_info['other_acount_name'] = td.get_text()
                                    if (index % 7)==0:
                                        test = 0
                                
                                links = tr.find_all('a',attrs={'class':'link'})
                                if len(links) == 0:
                                    continue
                                
                                href = links[0]['href']
                                details = re.compile('javascript:showDetail\((.*?)\)', re.S | re.M | re.I).findall(href)
                                if len(details) > 0:
                                    detail = details[0]
                                    detail = detail.replace('\t','')
                                    detail = detail.replace('\n','')
                                    detail = detail.replace(' ','')
                                    detail = detail.split('\',\'')
                                    detail[0] = detail[0].replace('\'','')
                                    detail[len(detail)-1] = detail[len(detail)-1].replace('\'','')
                                    trans_info['trans_desc'] = detail[0]
                                    trans_info['other_acount'] = detail[len(detail)-1]
                        
                                href = links[0]['href']
                                details = re.compile('javascript:showHistory\((.*?)\)', re.S | re.M | re.I).findall(href)
                                if len(details) > 0:
                                    detail = details[0]
                                    detail = detail.replace('\t','')
                                    detail = detail.replace('\n','')
                                    detail = detail.replace(' ','')
                                    detail = detail.split('\',\'')
                                    detail[0] = detail[0].replace('\'','')
                                    detail[len(detail)-1] = detail[len(detail)-1].replace('\'','')
                        
                                    trans_info['other_acount'] = detail[len(detail)-1]
                                    trans_info['trans_desc'] = detail[5]
                                
                                trans_info['trans_status'] = 'OK' 
                                translist.append(trans_info)
                                nCount = nCount+1
                        sIDs = re.compile('javascript\:onNextPage\((.*?)\)\;', re.S | re.M | re.I).findall(GDReqS_resp.text)
                        if len(sIDs) > 0:
                            detail = sIDs[0].replace('\'','')
                            detail = detail.split(',')
                            Begin_pos = detail[1]
                            incomeSum = detail[4]
                            timestmp = detail[3]
                            payoutSum = detail[5]
                            #print('Begin_pos:'+Begin_pos+'   incomeSum:'+incomeSum+'   timestmp:'+timestmp+'   payoutSum:'+payoutSum)
                        else:
                            #print('end')
                            break
                        dse_pageId = dse_pageId + 1
                        init_flag = '3'
                        pageflag = '2'
                        flag = '1'
                    isSuccess = True
                except:
                    respText = 'GDReqS except:'+traceback.format_exc()
                    Bank.uploadException(self,self.UserId,'doCapture Code:022 -->',respText)
                    isSuccess = False
                if isSuccess == False:
                    result = {
                        'status':'true',
                        'again':'true',
                        'step':'0',
                        'msg':'操作失败,Code:022',
                        'words':[
                                    {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                    {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                    {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                                ]
                    }
                    return json.dumps(result)
                
                if 0:
                    #进入信用卡中心查询
                    try:
                        findex_url = 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp'
                        findex_header = {
                            'Accept' : 'text/html, application/xhtml+xml, */*',
                            'Accept-Language' : 'zh-CN',
                            'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E;  QIHU 360EE)',
                            'Content-Type' : 'application/x-www-form-urlencoded',
                            'Accept-Encoding' : 'gzip, deflate',
                            'Connection' : 'Keep-Alive',
                            'Cache-Control' : 'no-cache'
                        }
                        findex_data = 'transData=&serviceId='+self.serviceId+'&zoneNo='+self.zoneNo+'&serviceIdInto=&dse_sessionId='+self.dse_sessionId+'&isflot=0&Language=zh_CN&requestChannel=302'
                        findex_resp = self.session.post(findex_url,headers = findex_header,data = findex_data,verify=False)
        
                        
                        loginall_url = 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/login/loginall.jsp'
                        loginall_header = {
                            'Accept' : 'text/html, application/xhtml+xml, */*',
                            'Accept-Language' : 'zh-CN',
                            'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E;  QIHU 360EE)',
                            'Accept-Encoding' : 'gzip, deflate',
                            'Connection' : 'Keep-Alive'
                        }
                        loginall_resp = self.session.get(loginall_url,headers = loginall_header,verify=False)
                            
                        
                        locSS_url = 'https://mybank.icbc.com.cn/servlet/ICBCPERBANKLocationServiceServlet'
                        locSS_header = {
                            'Accept' : 'text/html, application/xhtml+xml, */*',
                            'Accept-Language' : 'zh-CN',
                            'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E;  QIHU 360EE)',
                            'Content-Type' : 'application/x-www-form-urlencoded',
                            'Accept-Encoding' : 'gzip, deflate',
                            'Connection' : 'Keep-Alive',
                            'Cache-Control' : 'no-cache'
                        }
                        locSS_data = 'transData=&serviceId='+self.serviceId+'&zoneNo='+self.zoneNo+'&serviceIdInto=&dse_sessionId='+self.dse_sessionId+'&isflot=0&Language=zh_CN&requestChannel=302'
                        locSS_resp = self.session.post(locSS_url,headers = locSS_header,data = locSS_data,verify=False)
            
                        
                        cardList_url = 'https://mybank.icbc.com.cn/icbc/newperbank/card/card_myCardList.jsp?dse_sessionId='+self.dse_sessionId
                        cardList_header = {
                            'Accept' : 'text/html, application/xhtml+xml, */*',
                            'Accept-Language' : 'zh-CN',
                            'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E;  QIHU 360EE)',
                            'Content-Type' : 'application/x-www-form-urlencoded',
                            'Accept-Encoding' : 'gzip, deflate',
                            'Connection' : 'Keep-Alive',
                            'Cache-Control' : 'no-cache'
                        }
                        cardList_resp = self.session.get(cardList_url,headers = cardList_header,verify=False)
            
                        #查询信用卡记录
                        locSS_url = 'https://mybank.icbc.com.cn/servlet/ICBCPERBANKLocationServiceServlet'
                        locSS_header = {
                            'Accept' : 'text/html, application/xhtml+xml, */*',
                            'Accept-Language' : 'zh-CN',
                            'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E;  QIHU 360EE)',
                            'Content-Type' : 'application/x-www-form-urlencoded',
                            'Accept-Encoding' : 'gzip, deflate',
                            'Connection' : 'Keep-Alive',
                            'Cache-Control' : 'no-cache'
                        }
                        locSS_data = 'transData='+cardNum+'||no|000||myacct|&serviceId='+self.serviceId+'&zoneNo=&serviceIdInto=&requestChannel=302&dse_sessionId='+self.dse_sessionId
                        #729
                        locSS_resp = self.session.post(locSS_url,headers = locSS_header,data = locSS_data,verify=False)
        
        
                        aqHis_url = 'https://mybank.icbc.com.cn/icbc/newperbank/account/account_query_hisdetail.jsp?card_Num='+cardNum+'&acct_Type=no&acct_Code=000&from_Mark=myacct&dse_sessionId='+self.dse_sessionId
                        aqHis_header = {
                            'Accept' : 'text/html, application/xhtml+xml, */*',
                            'Accept-Language' : 'zh-CN',
                            'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E;  QIHU 360EE)',
                            'Content-Type' : 'application/x-www-form-urlencoded',
                            'Accept-Encoding' : 'gzip, deflate',
                            'Connection' : 'Keep-Alive'
                        }
                        aqHis_resp = self.session.get(aqHis_url,headers = aqHis_header,verify=False)
                        soup = BeautifulSoup(aqHis_resp.text,'html.parser')
                        rIDs = soup.find_all('input',attrs={'name':'requestTokenid'})
                        if len(rIDs) > 0:
                            requestTokenid = rIDs[0]['value']
                        #print('requestTokenid:'+str(requestTokenid))
                        
                        rIDs = soup.find_all('input',attrs={'name':'Areacode'})
                        serviceId = ''
                        if len(rIDs) > 0:
                            Areacode = rIDs[0]['value']
                        #print('Areacode:'+str(Areacode))
                        
                        rIDs = soup.find_all('input',attrs={'name':'days'})
                        if len(rIDs) > 0:
                            days = rIDs[0]['value']
                        #print('days:'+str(days))
                        
                        rIDs = soup.find_all('input',attrs={'name':'initDate'})
                        if len(rIDs) > 0:
                            initDate = rIDs[0]['value']
                        #print('initDate:'+str(initDate))
                        
                        rIDs = soup.find_all('input',attrs={'name':'initTime'})
                        if len(rIDs) > 0:
                            initTime = rIDs[0]['value']
                        #print('initTime:'+str(initTime))
                        
            
                        
                        ReqS_url = 'https://mybank.icbc.com.cn/servlet/ICBCINBSReqServlet'
                        ReqS_header = {
                            'Accept' : 'text/html, application/xhtml+xml, */*',
                            'Accept-Language' : 'zh-CN',
                            'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E;  QIHU 360EE)',
                            'Content-Type' : 'application/x-www-form-urlencoded',
                            'Accept-Encoding' : 'gzip, deflate',
                            'Connection' : 'Keep-Alive',
                            'Cache-Control' : 'no-cache'
                        }
                        beginDate = '2016-05-03'
                        endDate='2017-05-03'
                        ReqS_data = 'dse_sessionId='+self.dse_sessionId+'&requestTokenid='+requestTokenid+'&dse_applicationId=-1&dse_operationName=per_AccountQueryHisdetailOp&dse_pageId=3&cardOwnerMark1=&fromHDM=0&cardNum='+cardNum+'&cardType=007&acctCode=&acctNum=&Begin_pos=-1&acctIndex=0&Tran_flag=0&acctType=&queryType=3&cardAlias=&acctAlias=&acctTypeName=&currTypeName=&init_flag=1&type=browser&showNum=20&incomeSum=&timestmp=&payoutSum=&incomeSum1=&payoutSum1=&Areacode='+Areacode+'&pageflag=0&days='+days+'&flag=&initDate='+initDate+'&initTime='+initTime+'&isupdate=0&data_flag=&ishere=0&qaccf=0&FovaAcctType=0&acctSelList2Temp=&Area=&drcrFlag=0&cardOrAcct=&payCardSnap=&payAcctSnap=&cityFlagSnap=&graylink=0&jiedaiSnap=&ACSTYPE=0&ACAPPNO=&SKflag=0&onoffDJFlag=&onoffJJFlag=2&DRCRF_IN=0&begDate='+beginDate+'&endDate='+endDate+'&ishomecard=0&acctSelList=0&acctSelList2=no&currType=001&YETYPE=0&styFlag=0'
                        #743
                        ReqS_resp = self.session.post(ReqS_url,headers = ReqS_header,data = ReqS_data,verify=False)
                        soup = BeautifulSoup(ReqS_resp.text,'html.parser')
                        tables = soup.find_all('table',attrs={'class':'lst tblWidth'})
                        table = tables[0]
                        trs = table.find_all('tr')
                        unsettledBillDetail = []
                        index = 0
                        for tr in trs:
                            index = index + 1
                            if index == 1:
                                continue
                            idx = 0
                            BillDetail = {}
                            tds = tr.find_all('td')
                            for td in tds:
                                if idx % 7 == 0:
                                    #print('交易日期:'+td.text)
                                    BillDetail['tranDate'] = td.text
                                elif idx % 7 == 1:
                                    #print('摘要:'+td.text)
                                    BillDetail['tranSummary'] = td.text
                                elif idx % 7 == 2:
                                    #print('收入/支出:'+td.text)
                                    txt = td.text
                                    txt = txt.replace('-','')
                                    txt = txt.replace(',','')
                                    txt = txt.replace(' ','')
                                    if txt == '':
                                        txt = '0'
                                    txti = int(abs(float(txt)*100))
                                    BillDetail['tranAmt'] = str(txti)
                                elif idx % 7 == 3:
                                    print('币种:'+td.text)
                                    BillDetail['Type'] = td.text
                                elif idx % 7 == 4:
                                    #print('余额:'+td.text)
                                    txt = td.text
                                    txt = txt.replace('-','')
                                    txt = txt.replace(',','')
                                    txt = txt.replace(' ','')
                                    if txt == '':
                                        txt = '0'
                                    txti = int(abs(float(txt)*100))
                                    BillDetail['Balance'] = str(txti)
                                elif idx % 7 == 5:
                                    #print('对方信息:'+td.text)
                                    BillDetail['OtheActInfo'] = td.text
                                    BillDetail['cardNum'] = ''
                                    unsettledBillDetail.append(BillDetail)
                                idx = idx + 1
                                
                            if index > 20:
                                break
                            #break
                                                
                    except:
                        respText = 'credit except:'+traceback.format_exc()
                        Bank.uploadException(self,self.UserId,'doCapture Code:0XX -->',respText)
                
                self.account_info['translist'] = translist
    #             print(json.dumps(self.account_info))
    
                
                if isSuccess == False:
                    result = {
                        'status':'true',
                        'again':'true',
                        'step':'0',
                        'msg':'操作失败,Code:019',
                        'words':[
                                    {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                    {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                    {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                                ]
                    }
                    return json.dumps(result)


                try:
                    atomSvr_url = 'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/includes/atomService_control.jsp?serviceId=PBL20171802&transData=&dse_sessionId='+self.dse_sessionId+'&requestChannel=302'
                    atomSvr_header = {
                        'Accept': 'text/html, application/xhtml+xml, */*',
                        'Referer': 'https://mybank.icbc.com.cn/servlet/ICBCPERBANKLocationServiceServlet',
                        'Accept-Language': 'zh-CN',
                        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0;  QIHU 360EE)',
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Accept-Encoding': 'gzip, deflate',
                        'Host': 'mybank.icbc.com.cn',
                        'Connection': 'Keep-Alive',
                        'Cache-Control': 'no-cache'
                    }
                    atomSvr_resp = self.session.post(atomSvr_url,headers = atomSvr_header, verify=False)
                    soup = BeautifulSoup(atomSvr_resp.text,'html.parser')
                    rIDs = soup.find_all('table',attrs={'class':'td_L_main'})
                    if len(rIDs) > 0:
                        rID = rIDs[0]
                        trs = rID.find_all('tr')
                        for tr in trs:
                            tds = tr.find_all('td')
                            index = 0
                            if len(tds) > 1:
                                for td in tds:
                                    index = index + 1
                                    if index % 8 == 1:
                                        loanItem['loanTypeName'] = td.get_text()
                                        if '房' in td.get_text():
                                            loanItem['loanType'] = 'H'
                                        else:
                                            loanItem['loanType'] = 'C'
                                        #print('贷款种类:'+td.get_text())
        #                             elif index % 8 == 2:
        #                                 print('合同号:'+td.get_text())
        #                             elif index % 8 == 3:
        #                                 print('借据号:'+td.get_text())
                                    elif index % 8 == 4:
                                        val = td.get_text()
                                        val = val.replace(',','')
                                        loanItem['loanAmt'] = str(int(abs(float(val)*100)))
                                        #print('借据金额:'+td.get_text())
                                    elif index % 8 == 5:
                                        val = td.get_text()
                                        val = val.replace(',','')
                                        loanItem['loanBalance'] = str(int(abs(float(val)*100)))
                                        #print('借据余额:'+td.get_text())
                                    elif index % 8 == 6:
                                        val = td.text
                                        val = val.replace('-','')
                                        val = val.replace(' ','')
                                        loanItem['openDate'] = val
                                        #print('借据发放日:'+td.get_text())
                                    elif index % 8 == 7:
                                        val = td.text
                                        val = val.replace('-','')
                                        val = val.replace(' ','')
                                        loanItem['expiryDate'] = val
                                        #print('借据到期日:'+td.get_text())
                                    elif index % 8 == 0:
                                        loanList.append(loanItem)
                                        #print('管理:'+td.get_text())
                                        break
                    
                    loanItem['loanAct'] = cardNum
                    loanItem['loanDetail'] = loanDetail
                    
                    self.account_info['loanList'] = loanList 
                except Exception:
                    respText = 'Loan except:'+traceback.format_exc()
                    Bank.uploadException(self,self.UserId,'doCapture Loan:0XX -->',respText)
            #信用卡细节
            if cardsInfo:
                for ci in cardsInfo:
                    self.creditCardNum = ci['cardNo']
                    try:
                        loc_serv_url = 'https://mybank.icbc.com.cn/servlet/ICBCPERBANKLocationServiceServlet'
                        loc_serv__post_data ='transData=&serviceId=PBL200779&zoneNo=4000&serviceIdInto=&dse_sessionId='+self.dse_sessionId+'&isflot=0&Language=zh_CN&requestChannel=302'
                        loc_serv_headers={
                            'Accept':'application/json, text/javascript, */*; q=0.01',
                            'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-Requested-With':'XMLHttpRequest',
                            'Referer':'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp',
                            'Accept-Language':'en-US',
                            'Accept-Encoding':'gzip, deflate',
                            'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                            'Host':'mybank.icbc.com.cn',
                            'Content-Length':'155',
                            'DNT':'1',
                            'Connection':'Keep-Alive',
                            'Cache-Control':'no-cache'
                        }
                        self.session.post(loc_serv_url, data = loc_serv__post_data, headers = loc_serv_headers, verify=False)
                        
                        myCardList_url = 'https://mybank.icbc.com.cn/icbc/newperbank/card/card_myCardList.jsp?dse_sessionId='+self.dse_sessionId
                        myCardList_headers= {
                            'Accept':'text/html, application/xhtml+xml, */*',
                            'Referer':loc_serv_url,
                            'Accept-Language':'en-US',
                            'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                            'Accept-Encoding':'gzip, deflate',
                            'Host':'mybank.icbc.com.cn',
                            'DNT':'1',
                            'Connection':'Keep-Alive'         
                        }
                        self.session.get(myCardList_url, headers = myCardList_headers, verify=False)
                        
                        async_data_url = 'https://mybank.icbc.com.cn/servlet/AsynGetDataServlet'
                        async_post_data= 'SessionId='+self.dse_sessionId+'&cardNum='+self.creditCardNum+'&acctNum=&acctType=007&acctCode=&cashSign=0&currType=001&align=0&operatorFlag=0&tranflag=0&skFlag=0&tranCode=A00012'
                        async_data_headers={
                            'Referer':myCardList_url,
                            'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-Requested-With':'XMLHttpRequest',
                            'Accept':'application/json, text/javascript, */*; q=0.01',
                            'Accept-Language':'en-US',
                            'Accept-Encoding':'gzip, deflate',
                            'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                            'Host':'mybank.icbc.com.cn',
                            'Content-Length':'190',
                            'DNT':'1',
                            'Connection':'Keep-Alive',
                            'Cache-Control':'no-cache'
                        }
                        self.session.post(async_data_url, data = async_post_data, headers = async_data_headers, verify=False)
                    
                        loc_serv_post_data ='transData='+self.creditCardNum+'%7C1%7C3%7C1%7C1%7C007%7C0%7C'+self.creditCardNum+'%7C%7C0%7C0%7C0%7C0%7C0000&serviceId=PBL100414&zoneNo=&serviceIdInto=&requestChannel=302&dse_sessionId='+self.dse_sessionId
                        loc_serv_headers={
                            'Accept':'text/html, application/xhtml+xml, */*',
                            'Content-Type':'application/x-www-form-urlencoded',
                            'Referer':loc_serv_url,
                            'Accept-Language':'en-US',
                            'Accept-Encoding':'gzip, deflate',
                            'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                            'Host':'mybank.icbc.com.cn',
                            'Content-Length':'214',
                            'DNT':'1',
                            'Connection':'Keep-Alive',
                            'Cache-Control':'no-cache'
                        }
                        self.session.post(loc_serv_url, data = loc_serv_post_data, headers = loc_serv_headers, verify=False)
                        
                        ICBCINBSReq_url = 'https://mybank.icbc.com.cn/servlet/ICBCINBSReqServlet?dse_operationName=per_CardMyCreditCardOp&CardNum='+self.creditCardNum+'&doFlag=1&currLen=3&vbv=1&cardRegMode=1&cardType=007&cardFlag=0&parsentAcct='+self.creditCardNum+'&isOperNoNet=0&mycardOwnerType=0&crebFlag=0&skFlag=0&cardDescs=0000&dse_sessionId='+self.dse_sessionId
                        ICBCINBSReq_headers= {
                            'Accept':'text/html, application/xhtml+xml, */*',
                            'Referer':loc_serv_url,
                            'Accept-Language':'en-US',
                            'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                            'Accept-Encoding':'gzip, deflate',
                            'Host':'mybank.icbc.com.cn',
                            'DNT':'1',
                            'Connection':'Keep-Alive'         
                        }
                        
                        ICBCINBSReq = self.session.get(ICBCINBSReq_url, headers = ICBCINBSReq_headers, verify=False)
                        soup = BeautifulSoup(ICBCINBSReq.text,'html.parser')
                        forms = soup.find_all('form',attrs={'name':'form1'})
                        
                        if len(forms) > 0:
                            form = forms[0]
                            acts = form.find_all('input',attrs={'name':'acctName'})
                            if len(acts) > 0:
                                creditCardInfo['actName'] = acts[0]['value']
                        
                        table1 = soup.find_all('table',attrs={'class':'normaltbl'})
                        if table1:
                            trs = table1[1].findAll('tr')
                            if trs:
                                creditCardInfo['billDay'] = trs[1].findAll('td')[0].text.strip().replace('账单日 : ','').replace('日','')
                                creditCardInfo['dueDate'] = trs[1].findAll('td')[1].text.strip().replace('还款日 : ','').replace('年','').replace('月','').replace('日','')
                                creditCardInfo['cardType'] = trs[1].findAll('td')[3].text.strip().replace('主副卡标志 : ','')
                                creditCardInfo['currencyName'] = '人民币'
                                                                
                        table2 = soup.find('table',attrs={'class':'lst'})
                        if table2:
                            trs = table2.findAll('tr')
                            if trs:
                                mina = trs[4].findAll('td')[1].text.strip().replace(',','').replace('人民币：','')
                                if mina:
                                    creditCardInfo['availableLimit'] =str(int(float(mina) * 100))
                                a = trs[len(trs)-1].findAll('td')[1].text.strip()
                                if a:
                                    value=re.compile(r'启用日期：(.*?) 联名积分：', re.I).findall(a)
                                    if value and len(value) > 0:
                                        creditCardInfo['openDate'] = value[0].replace('年','').replace('月','').replace('日','')
                    except:
                        respText = 'credit000 except:'+traceback.format_exc()
                        Bank.uploadException(self, self.UserId, 'credit Code:000 -->',respText)
                    
                    try:
                        loc_serv_url = 'https://mybank.icbc.com.cn/servlet/ICBCPERBANKLocationServiceServlet'
                        loc_serv__post_data ='transData=&serviceId=PBL200779&zoneNo=4000&serviceIdInto=&dse_sessionId='+self.dse_sessionId+'&isflot=0&Language=zh_CN&requestChannel=302'
                        loc_serv_headers={
                            'Accept':'application/json, text/javascript, */*; q=0.01',
                            'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-Requested-With':'XMLHttpRequest',
                            'Referer':'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp',
                            'Accept-Language':'en-US',
                            'Accept-Encoding':'gzip, deflate',
                            'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                            'Host':'mybank.icbc.com.cn',
                            'Content-Length':'155',
                            'DNT':'1',
                            'Connection':'Keep-Alive',
                            'Cache-Control':'no-cache'
                        }
                        self.session.post(loc_serv_url, data = loc_serv__post_data, headers = loc_serv_headers, verify=False)
                        
                        myCardList_url = 'https://mybank.icbc.com.cn/icbc/newperbank/card/card_myCardList.jsp?dse_sessionId='+self.dse_sessionId
                        myCardList_headers= {
                            'Accept':'text/html, application/xhtml+xml, */*',
                            'Referer':loc_serv_url,
                            'Accept-Language':'en-US',
                            'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                            'Accept-Encoding':'gzip, deflate',
                            'Host':'mybank.icbc.com.cn',
                            'DNT':'1',
                            'Connection':'Keep-Alive'         
                        }
                        self.session.get(myCardList_url, headers = myCardList_headers, verify=False)
                        
                        async_data_url = 'https://mybank.icbc.com.cn/servlet/AsynGetDataServlet'
                        async_post_data= 'SessionId='+self.dse_sessionId+'&cardNum='+self.creditCardNum+'&acctNum=&acctType=007&acctCode=&cashSign=0&currType=001&align=0&operatorFlag=0&tranflag=0&skFlag=0&tranCode=A00012'
                        async_data_headers={
                            'Referer':myCardList_url,
                            'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-Requested-With':'XMLHttpRequest',
                            'Accept':'application/json, text/javascript, */*; q=0.01',
                            'Accept-Language':'en-US',
                            'Accept-Encoding':'gzip, deflate',
                            'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                            'Host':'mybank.icbc.com.cn',
                            'Content-Length':'190',
                            'DNT':'1',
                            'Connection':'Keep-Alive',
                            'Cache-Control':'no-cache'
                        }
                        self.session.post(async_data_url, data = async_post_data, headers = async_data_headers, verify=False)
                        
                        loc_serv_post_data ='transData=&serviceId=PBL200713&zoneNo=&serviceIdInto=PBL200713%3EPBL20071302&requestChannel=302&dse_sessionId='+self.dse_sessionId
                        loc_serv_headers={
                            'Accept':'text/html, application/xhtml+xml, */*',
                            'Content-Type':'application/x-www-form-urlencoded',
                            'Referer':loc_serv_url,
                            'Accept-Language':'en-US',
                            'Accept-Encoding':'gzip, deflate',
                            'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                            'Host':'mybank.icbc.com.cn',
                            'Content-Length':'150',
                            'DNT':'1',
                            'Connection':'Keep-Alive',
                            'Cache-Control':'no-cache'
                        }
                        self.session.post(loc_serv_url, data = loc_serv_post_data, headers = loc_serv_headers, verify=False)
                        
                        myCardBill_url = 'https://mybank.icbc.com.cn/icbc/newperbank/card/card_myBill_index.jsp?dse_sessionId='+self.dse_sessionId
                        myCardBill_headers= {
                            'Accept':'text/html, application/xhtml+xml, */*',
                            'Referer':loc_serv_url,
                            'Accept-Language':'en-US',
                            'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                            'Accept-Encoding':'gzip, deflate',
                            'Host':'mybank.icbc.com.cn',
                            'DNT':'1',
                            'Connection':'Keep-Alive'         
                        }
                        try:
                            myCardBill = self.session.get(myCardBill_url, headers = myCardBill_headers, verify=False)
                            soup = BeautifulSoup(myCardBill.text,'html.parser')
                            forms = soup.find_all('form',attrs={'name':'form2'})
                            if len(forms) > 0:
                                form = forms[0]
                                rIDs = form.find_all('input',attrs={'name':'requestTokenid'})
                                if len(rIDs) > 0:
                                    self.requestTokenid = rIDs[0]['value']
                                pageIds = form.find_all('input',attrs={'name':'dse_pageId'})
                                if len(pageIds) > 0:
                                    self.dse_pageId = pageIds[0]['value']
                        except:
                            respText = 'myCardBill except:'+traceback.format_exc()
                            Bank.uploadException(self, self.UserId, 'credit Code:myCardBillHIS -->',respText)
                        
                        self.cardHolder  = ''
                        ICBCINBSReq_url = 'https://mybank.icbc.com.cn/servlet/ICBCINBSReqServlet'
                        ICBCINBSReq_post_data='dse_sessionId='+self.dse_sessionId+'&requestTokenid='+self.requestTokenid+'&dse_applicationId=-1&dse_operationName=per_CardMyRepayOp&dse_pageId='+self.dse_pageId+'&CardNum=&cardArea=&doFlag=1'
                        ICBCINBSReq_headers= {
                            'Referer':myCardList_url,
                            'Content-Type':'application/x-www-form-urlencoded',
                            'Accept':'text/html, application/xhtml+xml, */*',
                            'Accept-Language':'en-US',
                            'Accept-Encoding':'gzip, deflate',
                            'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                            'Host':'mybank.icbc.com.cn',
                            'Content-Length':'193',
                            'DNT':'1',
                            'Connection':'Keep-Alive',
                            'Cache-Control':'no-cache'        
                        }
                        try:
                            ICBCINBSReq = self.session.post(ICBCINBSReq_url, data = ICBCINBSReq_post_data, headers = ICBCINBSReq_headers, verify=False)
                            soup = BeautifulSoup(ICBCINBSReq.text,'html.parser')
                            table1 = soup.find_all('table',attrs={'class':'lst'})
                            if table1:
                                trs = table1[0].findAll('tr')
                                if trs:
                                    self.cardHolder = trs[1].findAll('td')[3].text.strip()
                        except:
                            respText = 'ICBCINBSReq except:'+traceback.format_exc()
                            Bank.uploadException(self, self.UserId, 'credit Code:ICBCINBSReqHIS -->',respText)
                        
                        ICBCINBSReqServlet_url = 'https://mybank.icbc.com.cn/servlet/ICBCINBSReqServlet?tranFlag=0&dse_sessionId='+self.dse_sessionId+'&requestTokenid='+self.requestTokenid+'&dse_applicationId=-1&dse_operationName=per_GuessULikeOp&dse_pageId='+self.dse_pageId
                        ICBCINBSReqServlet_headers= {
                            'Accept':'text/html, application/xhtml+xml, */*',
                            'Referer':ICBCINBSReq_url,
                            'Accept-Language':'en-US',
                            'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                            'Accept-Encoding':'gzip, deflate',
                            'Host':'mybank.icbc.com.cn',
                            'DNT':'1',
                            'Connection':'Keep-Alive'        
                        }
                        self.session.get(ICBCINBSReqServlet_url, headers = ICBCINBSReqServlet_headers, verify=False)
                        
                        queryCheckbillList_post_data='dse_sessionId='+self.dse_sessionId+'&requestTokenid='+self.requestTokenid+'&dse_applicationId=-1&dse_operationName=per_AccountQueryCheckbillListOp&dse_pageId='+self.dse_pageId+'&cardNo='+self.creditCardNum+'&cardType=007&currtypeR=001&currtypeF=001&currtypeF1=001&currFlag=1&cardHolder='+ urllib.parse.quote(self.cardHolder,encoding='gbk')
                        queryCheckbillList_headers= {
                            'Referer':ICBCINBSReq_url,
                            'Content-Type':'application/x-www-form-urlencoded',
                            'Accept':'text/html, application/xhtml+xml, */*',
                            'Accept-Language':'en-US',
                            'Accept-Encoding':'gzip, deflate',
                            'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                            'Host':'mybank.icbc.com.cn',
                            'Content-Length':'300',
                            'DNT':'1',
                            'Connection':'Keep-Alive',
                            'Cache-Control':'no-cache'        
                        }
                        try:
                            queryCheckbillList = self.session.post(ICBCINBSReq_url, data = queryCheckbillList_post_data, headers = queryCheckbillList_headers, verify=False)
                            soup = BeautifulSoup(queryCheckbillList.text,'html.parser')
                            forms = soup.find_all('form',attrs={'name':'queryForm'})
                            if len(forms) > 0:
                                form = forms[0]
                                rIDs = form.find_all('input',attrs={'name':'requestTokenid'})
                                if len(rIDs) > 0:
                                    self.requestTokenid = rIDs[0]['value']
                                pageIds = form.find_all('input',attrs={'name':'dse_pageId'})
                                if len(pageIds) > 0:
                                    self.dse_pageId = pageIds[0]['value']
                            
                            lstlink = soup.findAll('a',attrs={'class':'lstlink'})
                            hisQuery = []
                            for l in lstlink:
                                his = l.text
                                hisQuery.append(his)
                        
                            for h in hisQuery:
                                WORKMON_post_data='dse_sessionId='+self.dse_sessionId+'&requestTokenid='+self.requestTokenid+'&dse_applicationId=-1&dse_operationName=per_AccountQueryCheckbillOp&dse_pageId='+self.dse_pageId+'&cardNo='+self.creditCardNum+'&acctIndex=0&Tran_flag=0&Sel_flag=0&newOldFlag=0&queryType=4&cardNum1='+self.creditCardNum+'&interCurrType=&changeFlag=0&WORKMON='+h+'&currtypeR=001&currtypeF=001&cardType=007&dcrFlag=0&currFlag=1'
                                WORKMON_headers= {
                                    'Referer':ICBCINBSReq_url,
                                    'Content-Type':'application/x-www-form-urlencoded',
                                    'Accept':'text/html, application/xhtml+xml, */*',
                                    'Accept-Language':'en-US',
                                    'Accept-Encoding':'gzip, deflate',
                                    'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                                    'Host':'mybank.icbc.com.cn',
                                    'Content-Length':'387',
                                    'DNT':'1',
                                    'Connection':'Keep-Alive',
                                    'Cache-Control':'no-cache'        
                                }
                                try:
                                    WORKMON = self.session.post(ICBCINBSReq_url, data = WORKMON_post_data, headers = WORKMON_headers, verify=False)
                                    soup = BeautifulSoup(WORKMON.text,'html.parser')
                                    table1 = soup.find_all('table',attrs={'class':'normaltbl p3table'})
                                    if table1:
                                        trs = table1[1].findAll('tr')
                                        if trs:
                                            billDate = trs[0].findAll('td')[2].text.strip().replace('年','').replace('月','').replace('日','')
                                            a = trs[1].findAll('td')[2].text.strip().replace(',','')
                                            if a :
                                                totalCost = str(int(float(a) * 100))
                                            b = trs[2].findAll('td')[2].text.strip().replace(',','')
                                            if b :
                                                minPaymentAmt = str(int(float(b) * 100))
                                            
                                            historyBills.append({'billDate':billDate,'totalCost':totalCost,'minPaymentAmt':minPaymentAmt})
                                except:
                                    respText ="data: " + str(WORKMON_post_data) +'WORKMON except:'+traceback.format_exc()
                                    Bank.uploadException(self, self.UserId, 'credit Code:historyBills -->',respText) 
                                #infoIframeSrc = soup.find(id='infoIframe').get('src')
                                
                                infoIframe_url = 'https://mybank.icbc.com.cn/icbc/newperbank/account/account_query_checkbill_loan_detail_index.jsp?dse_sessionId='+self.dse_sessionId+'&requestTokenid='+self.requestTokenid+'&cardNo='+self.creditCardNum
                                infoIframe_headers= {
                                    'Accept':'text/html, application/xhtml+xml, */*',
                                    'Referer':ICBCINBSReq_url,
                                    'Accept-Language':'en-US',
                                    'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                                    'Accept-Encoding':'gzip, deflate',
                                    'Host':'mybank.icbc.com.cn',
                                    'DNT':'1',
                                    'Connection':'Keep-Alive'        
                                }
                                try:
                                    infoIframe = self.session.get(infoIframe_url, headers = infoIframe_headers, verify=False)
                                    soup = BeautifulSoup(infoIframe.text,'html.parser')
                                    forms = soup.find_all('form',attrs={'name':'loanForm'})
                                    if len(forms) > 0:
                                        form = forms[0]
                                        rIDs = form.find_all('input',attrs={'name':'requestTokenid'})
                                        if len(rIDs) > 0:
                                            self.requestTokenid = rIDs[0]['value']
                                        pageIds = form.find_all('input',attrs={'name':'dse_pageId'})
                                        if len(pageIds) > 0:
                                            self.dse_pageId = pageIds[0]['value']
                                except:
                                    respText = 'infoIframe except:'+traceback.format_exc()
                                    Bank.uploadException(self, self.UserId, 'credit Code:infoIframeHIS -->',respText)        
                                
                                ICBCINBSReqServlet_url = 'https://mybank.icbc.com.cn/servlet/ICBCINBSReqServlet?tranFlag=0&dse_sessionId='+self.dse_sessionId+'&requestTokenid='+self.requestTokenid+'&dse_applicationId=-1&dse_operationName=per_GuessULikeOp&dse_pageId='+self.dse_pageId
                                ICBCINBSReqServlet_headers= {
                                    'Accept':'text/html, application/xhtml+xml, */*',
                                    'Referer':ICBCINBSReq_url,
                                    'Accept-Language':'en-US',
                                    'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                                    'Accept-Encoding':'gzip, deflate',
                                    'Host':'mybank.icbc.com.cn',
                                    'DNT':'1',
                                    'Connection':'Keep-Alive'        
                                }
                                self.session.get(ICBCINBSReqServlet_url, headers = ICBCINBSReqServlet_headers, verify=False)
                                
                                ICBCINBSReq_post_data = 'dse_sessionId='+self.dse_sessionId+'&requestTokenid='+self.requestTokenid+'&dse_applicationId=-1&dse_operationName=per_AccountQueryCheckbillOp&dse_pageId='+self.dse_pageId+'&changeFlag=2&page=1&YBpage=1&cardNo='+self.creditCardNum    
                                ICBCINBSReq_headers= {
                                    'Referer':infoIframe_url,
                                    'Content-Type':'application/x-www-form-urlencoded',
                                    'Accept':'text/html, application/xhtml+xml, */*',
                                    'Accept-Language':'en-US',
                                    'Accept-Encoding':'gzip, deflate',
                                    'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                                    'Host':'mybank.icbc.com.cn',
                                    'Content-Length':'225',
                                    'DNT':'1',
                                    'Connection':'Keep-Alive',
                                    'Cache-Control':'no-cache'        
                                }
                                try:
                                    ICBCINBSReq = self.session.post(ICBCINBSReq_url, data = ICBCINBSReq_post_data, headers = ICBCINBSReq_headers, verify=False)
                                    soup = BeautifulSoup(ICBCINBSReq.text,'html.parser')
                                    table1 = soup.find_all('table',attrs={'class':'normaltbl p3table'})
                                    if table1:
                                        trs = table1[0].findAll('tr')
                                        del trs[0]
                                        del trs[0]
                                        del trs[0]
                                        del trs[0]
                                        for tr in trs:
                                            tranDate = tr.findAll('td')[1].text.strip().replace('-','')
                                            bookedDate = tr.findAll('td')[2].text.strip().replace('-','')
                                            tranSummary = tr.findAll('td')[3].text.strip()
                                            tranPlace = tr.findAll('td')[4].text.strip()
                                            a = tr.findAll('td')[6].text.strip().replace(',','').replace('/RMB','')
                                            if a.find('支出')>=0:
                                                a = a.replace('(支出)','')
                                                payMoney = str(int(float(a) * 100))
                                                incomeMoney = ''
                                            elif a.find('存入')>=0:
                                                a = a.replace('(存入)','')
                                                incomeMoney = str(int(float(a) * 100))
                                                payMoney = ''
                                            else:
                                                incomeMoney = ''
                                                payMoney = ''   
                                            historyBillDetail.append({'tranDate':tranDate,'bookedDate':bookedDate,'tranSummary':tranSummary,'tranPlace':tranPlace,'incomeMoney': incomeMoney,'payMoney':payMoney,'bookedDate':''})
                                            
                                except:
                                    respText = 'historyBillDetail except:'+traceback.format_exc()
                                    Bank.uploadException(self, self.UserId, 'credit Code:historyBillDetail -->',respText) 
                        except:
                            respText = 'history except:'+traceback.format_exc()
                            print(respText)
                            Bank.uploadException(self, self.UserId, 'credit Code:HIS -->',respText)
                    except:
                        respText = 'credit001 except:'+traceback.format_exc()
                        print(respText)
                        Bank.uploadException(self, self.UserId, 'credit Code:001 -->',respText)
                    
                    today = datetime.date.today().strftime("%d")
                    if creditCardInfo['billDay'] < today:
                        try:
                            loc_serv_url = 'https://mybank.icbc.com.cn/servlet/ICBCPERBANKLocationServiceServlet'
                            loc_serv__post_data ='transData=&serviceId=PBL201786&zoneNo=4000&serviceIdInto=&dse_sessionId='+self.dse_sessionId+'&isflot=0&Language=zh_CN&requestChannel=302'
                            loc_serv_headers={
                                'Accept':'application/json, text/javascript, */*; q=0.01',
                                'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                                'X-Requested-With':'XMLHttpRequest',
                                'Referer':'https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp',
                                'Accept-Language':'en-US',
                                'Accept-Encoding':'gzip, deflate',
                                'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                                'Host':'mybank.icbc.com.cn',
                                'Content-Length':'155',
                                'DNT':'1',
                                'Connection':'Keep-Alive',
                                'Cache-Control':'no-cache'
                            }
                            self.session.post(loc_serv_url, data = loc_serv__post_data, headers = loc_serv_headers, verify=False)
                            
                            account_list_url = 'https://mybank.icbc.com.cn/icbc/newperbank/account/account_list_regacct.jsp?dse_sessionId='+self.dse_sessionId
                            account_list_headers= {
                                'Accept':'text/html, application/xhtml+xml, */*',
                                'Referer':loc_serv_url,
                                'Accept-Language':'en-US',
                                'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                                'Accept-Encoding':'gzip, deflate',
                                'Host':'mybank.icbc.com.cn',
                                'DNT':'1',
                                'Connection':'Keep-Alive'         
                            }
                            self.session.get(account_list_url, headers = account_list_headers, verify=False)
                            
                            async_data_url = 'https://mybank.icbc.com.cn/servlet/AsynGetDataServlet'
                            async_post_data= 'SessionId='+self.dse_sessionId+'&cardNum='+self.creditCardNum+'&acctNum=&acctType=007&acctCode=&cashSign=0&currType=001&align=0&operatorFlag=0&tranflag=0&skFlag=0&tranCode=A00012'
                            async_data_headers={
                                'Referer':account_list_url,
                                'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                                'X-Requested-With':'XMLHttpRequest',
                                'Accept':'application/json, text/javascript, */*; q=0.01',
                                'Accept-Language':'en-US',
                                'Accept-Encoding':'gzip, deflate',
                                'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                                'Host':'mybank.icbc.com.cn',
                                'Content-Length':'190',
                                'DNT':'1',
                                'Connection':'Keep-Alive',
                                'Cache-Control':'no-cache'
                            }
                            self.session.post(async_data_url, data = async_post_data, headers = async_data_headers, verify=False)
                            
                            loc_serv_post_data ='transData='+self.creditCardNum+'%7C%7Cno%7C000%7C%7Cmyacct%7C&serviceId=PBL200711&zoneNo=&serviceIdInto=&requestChannel=302&dse_sessionId='+self.dse_sessionId
                            loc_serv_headers={
                                'Accept':'text/html, application/xhtml+xml, */*',
                                'Content-Type':'application/x-www-form-urlencoded',
                                'Referer':loc_serv_url,
                                'Accept-Language':'en-US',
                                'Accept-Encoding':'gzip, deflate',
                                'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                                'Host':'mybank.icbc.com.cn',
                                'Content-Length':'172',
                                'DNT':'1',
                                'Connection':'Keep-Alive',
                                'Cache-Control':'no-cache'
                            }
                            self.session.post(loc_serv_url, data = loc_serv_post_data, headers = loc_serv_headers, verify=False)
                            
                            ICBCINBSReq_url = 'https://mybank.icbc.com.cn/servlet/ICBCINBSReqServlet?dse_operationName=per_AccountQueryHisdetailOp&firstInjectFlag=0&card_Num='+self.creditCardNum+'&acct_Type=no&acct_Code=000&from_Mark=myacct&dse_sessionId='+self.dse_sessionId
                            ICBCINBSReq_headers= {
                                'Accept':'text/html, application/xhtml+xml, */*',
                                'Referer':loc_serv_url,
                                'Accept-Language':'en-US',
                                'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                                'Accept-Encoding':'gzip, deflate',
                                'Host':'mybank.icbc.com.cn',
                                'DNT':'1',
                                'Connection':'Keep-Alive'         
                            }
                            try:
                                ICBCINBSReq = self.session.get(ICBCINBSReq_url, headers = ICBCINBSReq_headers, verify=False)
                                soup = BeautifulSoup(ICBCINBSReq.text,'html.parser')
                                forms = soup.find_all('form',attrs={'name':'detailform'})
                                
                                if len(forms) > 0:
                                    form = forms[0]
                                    rIDs = form.find_all('input',attrs={'name':'requestTokenid'})
                                    if len(rIDs) > 0:
                                        self.requestTokenid = rIDs[0]['value']
                                    pageIds = form.find_all('input',attrs={'name':'dse_pageId'})
                                    if len(pageIds) > 0:
                                        self.dse_pageId = pageIds[0]['value']
                            except:
                                respText = 'ICBCINBSReq except:'+traceback.format_exc()
                                Bank.uploadException(self, self.UserId, 'credit Code:ICBCINBSReqUSBD -->',respText)
                            today = datetime.date.today().strftime("%Y-%m")
                            begDate = today +'-'+ creditCardInfo['billDay']
                            endDate = datetime.date.today().strftime("%Y-%m-%d")
                            days = datetime.date.today().strftime("%Y%m%d")
                            initDate = datetime.date.today().strftime("%Y:%m:%d")
                            initTime = datetime.date.today().strftime("%H:%M:%S")
                            
                            ICBCINBSReqServ_url = 'https://mybank.icbc.com.cn/servlet/ICBCINBSReqServlet'
                            ICBCINBSReqServ_post_data = 'dse_sessionId='+self.dse_sessionId+'&requestTokenid='+self.requestTokenid+'&dse_applicationId=-1&dse_operationName=per_AccountQueryHisdetailOp&dse_pageId='+self.dse_pageId+'&cardOwnerMark1=&fromHDM=0&cardNum='+self.creditCardNum+'&cardType=007&acctCode=&acctNum=&Begin_pos=-1&acctIndex=0&Tran_flag=0&acctType=&queryType=3&cardAlias=&acctAlias=&acctTypeName=&currTypeName=&init_flag=1&type=browser&showNum=20&incomeSum=&timestmp=&payoutSum=&incomeSum1=&payoutSum1=&Areacode=4000&pageflag=0&days='+days+'&flag=&initDate='+initDate+'&initTime='+initTime+'&isupdate=0&data_flag=&ishere=0&qaccf=0&FovaAcctType=0&acctSelList2Temp=&Area=&drcrFlag=0&cardOrAcct=&payCardSnap=&payAcctSnap=&cityFlagSnap=&graylink=0&jiedaiSnap=&ACSTYPE=0&ACAPPNO=&SKflag=0&onoffDJFlag=&onoffJJFlag=2&DRCRF_IN=0&begDate='+begDate+'&endDate='+endDate+'&ishomecard=0&acctSelList=0&acctSelList2=no&currType=001&YETYPE=0&styFlag=0'
                            ICBCINBSReqServ__headers= {
                                'Accept':'text/html, application/xhtml+xml, */*',
                                'Referer':ICBCINBSReq_url,
                                'Accept-Language':'en-US',
                                'User-Agent':'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                                'Content-Type':'application/x-www-form-urlencoded',
                                'Accept-Encoding':'gzip, deflate',
                                'Host':'mybank.icbc.com.cn',
                                'Content-Length':'890',
                                'DNT':'1',
                                'Connection':'Keep-Alive',
                                'Cache-Control':'no-cache'
                            }
                            try:
                                ICBCINBSReqServ = self.session.post(ICBCINBSReqServ_url, data = ICBCINBSReqServ_post_data, headers = ICBCINBSReqServ__headers, verify=False) 
                                soup = BeautifulSoup(ICBCINBSReqServ.text,'html.parser')
                                tables = soup.find_all('table',attrs={'class':'lst tblWidth'})
                                if len(tables) > 0:
                                    table = tables[0]
                                    trs = table.find_all('tr')
                                    for tr in trs:
                                        tds = tr.find_all('td',attrs={'align':'center'})
                                        if len(tds) == 0:
                                            continue
                                        unsettledBillDetail_info = {}
                                        
                                        links = tr.find_all('a',attrs={'class':'link'})
                                        if len(links) == 0:
                                            continue
                                        
                                        href = links[0]['href']
                                        details = re.compile('javascript:showDetail\((.*?)\)', re.S | re.M | re.I).findall(href)
                                        if len(details) > 0:
                                            detail = details[0]
                                            detail = detail.replace('\t','')
                                            detail = detail.replace('\n','')
                                            detail = detail.replace(' ','')
                                            detail = detail.split('\',\'')
                                            detail[0] = detail[0].replace('\'','')
                                            detail[len(detail)-1] = detail[len(detail)-1].replace('\'','')
                                            unsettledBillDetail_info['bookedDate'] = ''
                                            unsettledBillDetail_info['tranPlace'] = ''
                                            unsettledBillDetail_info['tranDate'] = detail[2].replace('-','')
                                            unsettledBillDetail_info['tranSummary'] = detail[5]
                                            unsettledBillDetail_info['cardNum'] = detail[0]
                                            tranAmt = str(int(float(detail[13].replace(',',''))*100))
                                            if tranAmt:
                                                if tranAmt.find('-')>=0:
                                                    unsettledBillDetail_info['incomeMoney'] = ''
                                                    unsettledBillDetail_info['payMoney'] = tranAmt
                                                else:
                                                    unsettledBillDetail_info['incomeMoney'] = tranAmt
                                                    unsettledBillDetail_info['payMoney'] = ''
                                            else:
                                                unsettledBillDetail_info['incomeMoney'] =''
                                                unsettledBillDetail_info['payMoney'] =''
                                        unsettledBillDetail.append(unsettledBillDetail_info)
                                
                            except:
                                respText = 'unsettledBillDetail except:'+traceback.format_exc()
                                Bank.uploadException(self, self.UserId, 'credit Code:USBD -->',respText)
                    
                        except Exception:
                            respText = 'credit002 except:'+traceback.format_exc()
                            Bank.uploadException(self, self.UserId, 'credit Code:002 -->',respText)
                
                    creditCardInfo['cardsInfo'] = cardsInfo
                    creditCardInfo['historyBills'] = historyBills
                    creditCardInfo['historyBillDetail'] = historyBillDetail
                    creditCardInfo['unsettledBillDetail'] = unsettledBillDetail
                    creditCardInfos.append(creditCardInfo)
                self.account_info['creditCardInfos'] = creditCardInfos
            
            isSuccess = Bank.uploadData(self, self.account_info)
            
            if isSuccess:
                result = {
                    'status':'true',
                    'again':'false',
                    'msg':'操作成功'
                }
                print("Upload Data Success...")
                Bank.uploadException(self,self.UserId,'Upload Data','Upload Data Success nCount:'+str(nCount))
            else:
                result = {
                    'status':'false',
                    'again':'false',
                    'step':'0',
                    'msg':'系统繁忙,请稍后重试(ICBC_UDS)',
                    'words':[
                                {'ID':'UserId','index': 0,'needUserInput':'true', 'label':'用户名或卡号', 'type': 'text'},
                                {'ID':'password','index': 1,'needUserInput':'true', 'label':'登录密码', 'type': 'password'},
                                {'ID':'MobilePhone','index': 2,'needUserInput':'true', 'label':'绑定手机号码', 'type': 'text'},
                            ]
                }
                Bank.uploadException(self,self.UserId,'Upload Data','Upload Data fail nCount:'+str(nCount)+'  | '+json.dumps(self.account_info, ensure_ascii=False))

            return json.dumps(result)

    def uploadData(self, data):
        #上传数据到服务器
        headers = {
            'Accept':'*/*',
            'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent':'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.87 Safari/537.36'
        }
        try:
            postData = {
                'heade':{'code':'uploadPersonalBankData','token':'','timestamp':''},
                'body':{
                    'attach':'',
                    'content':data
                }
            }
            resp = requests.post(self.crawlerServiceUrl, headers = headers, data = {'content':json.dumps(postData, ensure_ascii=False)})
            respObj = json.loads(str(resp.text).strip(), encoding = 'utf-8')
            if 'resCode' in respObj.keys() and '0' == str(respObj['resCode']):
                return True
            else:
                Bank.uploadException(self, username=self.UserId, step='uploadData fail', errmsg=resp.text)
                return False
        except Exception:
            respText = 'resp:'+resp.text+'   |'+traceback.format_exc()
            Bank.uploadException(self, username=self.UserId, step='uploadData fail', errmsg=respText)
            return False

    '''def jiamiData1(self,randomId,login_account,login_password,verifyCode,clientIp,serviceId,zoneNo):
        #密码加密
        jiamiUrl = ''#self.jiamiUrl
        jiamiUrl_headers = {
            'Accept':'*/*',
            'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent':'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.87 Safari/537.36'
        }
        #{"bankCode":"ICBC","password":"123456","imgCode":"456z","clientIP":"127.0.0.1","randomId":"rdm123","serviceId":"0500","requestChannelzoneNo":"112233"}
        jiamiUrl_params = {
            'bankCode':'ICBC',
            'step':'1',
            'account':login_account,
            'password':login_password,
            'imgCode':verifyCode,
            'clientIP':clientIp,
            'randomId':randomId,
            'serviceId':serviceId,
            'requestChannelzoneNo':zoneNo
        }
        op = False
        try:
            jiamiData = {'content':json.dumps(jiamiUrl_params, ensure_ascii=False)}
            resp = requests.post(jiamiUrl, headers = jiamiUrl_headers, data = jiamiData)
            self.jmresp1 = resp.text
            self.URI = ''
            obj = ''
            self.URI = ''
            objs = re.compile(r'obj(.*?)}', re.S | re.M | re.I).findall(resp.text)
            if len(objs) > 0:
                obj = objs[0]+'}'
                objs = re.compile(r'obj(.*?)}', re.S | re.M | re.I).findall(obj)
                if len(objs) > 0:
                    obj = objs[0]+'}'
                    objs = re.compile(r'obj(.*?)}', re.S | re.M | re.I).findall(obj)
                    if len(objs) > 0:
                        URI = objs[0]
                        URI = URI[3:len(URI)]
                        self.URI = URI.replace('\"','')
                        self.URI = self.URI.replace('\\','')
                        op = True
            if op==False:
                if 'Inside error' in resp.text:
                    op = False
                else:
                    retJson = json.loads(resp.text)
                    sobj = json.loads(retJson['obj'])
                    ssobj = sobj['obj']
                    sssobj = json.loads(ssobj)
                    self.URI = sssobj['obj']
                    #self.URI = self.URI[1:]
                    op = True
        except:
            respText = 'jiamiData1 except:'+traceback.format_exc()
            Bank.uploadException(self,self.UserId,'jiamiData1',respText)
 
            op = False
        return op'''
       
    def jiamiData1(self, randomId,login_account,login_password,verifyCode,clientIp,serviceId,zoneNo,setChangeRule,setRules,setRandom):
        #密码加密
        #jiamiUrl = 'http://127.0.0.1:8888/bankEncrypt'
        jiamiUrl_headers = {
            'Accept':'*/*',
            'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent':'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.87 Safari/537.36'
        }
        #{"bankCode":"ICBC","password":"123456","imgCode":"456z","clientIP":"127.0.0.1","randomId":"rdm123","serviceId":"0500","requestChannelzoneNo":"112233"}
        jiamiUrl_params = {
            'bankCode':'ICBC1',
            'step':'1',
            'account':login_account,
            'password':login_password,
            'imgCode':verifyCode,
            'clientIP':clientIp,
            'randomId':randomId,
            'serviceId':serviceId,
            'setChangeRule':setChangeRule,
            'setRules':setRules,
            'setRandom':setRandom,
            'requestChannelzoneNo':zoneNo
        }
        jiamiData = {'content':json.dumps(jiamiUrl_params, ensure_ascii=False)}
        url_str = json.dumps(jiamiUrl_params, ensure_ascii=False)
        #jiamiUrl = 'http://10.10.10.74:8888/bankEncrypt/?content='+url_str
        jiamiUrl = self.jiamiUrl + '?content=' + url_str
#         print(jiamiUrl)
        #URI = ''
        op = False
        try:
            #print('url_str'+url_str)
            resp = requests.get(jiamiUrl, headers = jiamiUrl_headers)
            print("jiami 1: "+resp.text)
            if len(resp.text) <= 20:
                op = False
            else:
                self.URI = resp.text
                print(self.URI)
                op = True
    
        except:
            respText = 'jiamiData1 except:'+traceback.format_exc()
            #Bank.uploadException(self,self.UserId,'jiamiData1',respText)
            print(respText)
            op = False
        return op
    
    def jiamiData2(self, verifyCode,clientIp,dse_sessionId):
        #密码加密
        jiamiUrl_headers = {
            'Accept':'*/*',
            'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent':'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.87 Safari/537.36'
        }
        jiamiUrl_params = {
            'bankCode':'ICBC2',
            'step':'2',
            'imgCode':verifyCode,
            'clientIP':clientIp,
            'dse_sessionId':dse_sessionId,
        }
        op = False
        url_str = json.dumps(jiamiUrl_params, ensure_ascii=False)
        #jiamiUrl = 'http://10.10.10.74:8888/bankEncrypt/?content='+url_str
        jiamiUrl = self.jiamiUrl + '?content=' + url_str
        print(jiamiUrl)
        #URI = ''
        op = False
        try:
            #print('url_str'+url_str)
            resp = requests.get(jiamiUrl, headers = jiamiUrl_headers)
            print(resp.text)
            if len(resp.text) <= 20:
                op = False
            else:
                self.encripCode = resp.text
                op = True
            print(resp.text)
        except:
            respText = 'jiamiData1 except:'+traceback.format_exc()
            #Bank.uploadException(self,self.UserId,'jiamiData1',respText)
            print(respText)
            op = False
        return op

    '''def jiamiData2(self,verifyCode,clientIp,dse_sessionId):
        #密码加密
        jiamiUrl = self.jiamiUrl
        jiamiUrl_headers = {
            'Accept':'*/*',
            'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent':'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.87 Safari/537.36'
        }
        jiamiUrl_params = {
            'bankCode':'ICBC',
            'step':'2',
            'imgCode':verifyCode,
            'clientIP':clientIp,
            'dse_sessionId':dse_sessionId,
        }
        op = False
        try:
            jiamiData = {'content':json.dumps(jiamiUrl_params, ensure_ascii=False)}
            resp = requests.post(jiamiUrl, headers = jiamiUrl_headers, data = jiamiData)
            self.jmresp2 = resp.text
            obj = ''
            self.encripCode = ''
            objs = re.compile(r'obj(.*?)}', re.S | re.M | re.I).findall(resp.text)
            if len(objs) > 0:
                obj = objs[0]+'}'
                objs = re.compile(r'obj(.*?)}', re.S | re.M | re.I).findall(obj)
                if len(objs) > 0:
                    obj = objs[0]+'}'
                    objs = re.compile(r'obj(.*?)}', re.S | re.M | re.I).findall(obj)
                    if len(objs) > 0:
                        URI = objs[0]
                        URI = URI[3:len(URI)]
                        URI = URI.replace('\"','')
                        self.encripCode = URI.replace('\\','')
                        op = True
            if op == False:
                if 'Inside error' in resp.text:
                    op = False
                else:
                    retJson = json.loads(resp.text)
                    sobj = json.loads(retJson['obj'])
                    ssobj = sobj['obj']
                    sssobj = json.loads(ssobj)
                    self.encripCode = sssobj['obj']
                    #self.encripCode = self.encripCode[1:]
                    op = True
        except:
            respText = 'jiamiData2 except:'+traceback.format_exc() + '   |  '+resp.text
            Bank.uploadException(self,self.UserId,'jiamiData2',respText)
            op = False
        return op'''

    def uploadException(self, username = '', step = '', errmsg = ''):
        #上传异常信息
        headers = {
            'Accept':'*/*',
            'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent':'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.87 Safari/537.36'
        }
        data = {'error_info': errmsg,'error_step':step,'error_type':'icbc','login_account':username}
        try:
            requests.post(self.uploadExceptionUrl, headers = headers, data = {'content':json.dumps(data, ensure_ascii=False)})
        except:
            print('uploadException-->[post] icbc exception error')

    def get_pre_date(self,daycount):
        d = datetime.datetime.now()
        dayscount = datetime.timedelta(days=0)
        print(dayscount)
        dayto = d - dayscount
        sixdays = datetime.timedelta(days=daycount)
        dayfrom = dayto - sixdays
        
        BeginDate = str(dayfrom.year)+'-'+str(dayfrom.month)+'-'+str(dayfrom.day)
        EndDate = str(dayto.year)+'-'+str(dayto.month)+'-'+str(dayto.day)
        return BeginDate,EndDate

def header_map(headerstr):
    headers = {}
    hd = map(lambda x:x.split(':'),headerstr.split('\n'))
    hdlist = list(hd)
    hdlist
    for item in  hdlist:
        valuestr = ''
        for i in list(range(1,len(item))):
            valuestr = valuestr+item[i]
        headers[item[0]]= valuestr.strip(' ')
    return headers

def cookie_map(cookiestr):
    cookie = {}
    cookiedict = map(lambda x:x.split('='),cookiestr.split(';'))
    cookiedict = list(cookiedict)
    for item in  cookiedict:
        cookie[item[0].strip(' ')]= item[1]
    return cookie

def postdata_map(postdatastr):
    post_data = {}
    pd = map(lambda x:x.split('='),postdatastr.split('&'))
    pdlist = list(pd)
    if postdatastr[-1]=='&':
        pdlist.pop()
    for item in  pdlist:
        post_data[item[0]]= item[1]
    return post_data


