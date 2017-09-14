# -*- coding: utf-8 -*-
'''
Created on 2016年12月4日

@author: cary.zhu
'''

import json
import importlib
import traceback
import time
import importlib.util

def fuckTest():
    print('this is fuck test')

class SpiderRouter(object):
    '''
    params:{
        type:类型（bank、e-commers、telecommunications）
        name:例如：abc
        class:例如：Bank
    }
    '''

    def init(self, jsonParams):
        res = None
        print (str(jsonParams))
        print('fuck')
        for a in range(10):
            print(a)
            time.sleep(1)

        try:
        
            print('start paras data')
            values = json.loads(jsonParams)
            m1 = importlib.import_module(values.get('type') + '.' + values.get('name'))
            self.aclass = getattr(m1, values.get('class'))
            function = values.get('method')
            res = self.aclass.init(self.aclass);
            status = 'true'
            print('end paras data')
        except KeyError:
            print('error')
            status = 'false'
            res = None
            traceback.print_exc()
        return json.dumps({
            'status': status,
            'result': res
        })
    
    '''
    jsonParams:json格式参数
    '''
    def execute(self, jsonParams):
        print('execute ')
        try:

            res = self.aclass.doCapture(self.aclass, jsonParams);
            status = 'true'
        except KeyError:
            status = 'false'
            res = None
            
        return json.dumps({
            'status': status,
            'result': res,
        })

    def test(self,jsonParams):
        print('this function is test')
