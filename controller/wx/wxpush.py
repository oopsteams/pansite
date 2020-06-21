# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/21
"""
from controller.action import BaseHandler
from cfg import WX_PUSH
import hashlib
from controller.auth_service import auth_service
from controller.wx.goods_service import goods_service
from dao.models import CourseProduct
from utils import obfuscate_id, decrypt_id
import json


class WXAppPush(BaseHandler):

    def checksign(self):
        sign = self.get_argument("signature", "")
        tt = self.get_argument("timestamp", '0')
        nonce = self.get_argument("nonce", '0')
        arr = [WX_PUSH['token'], tt, nonce]
        arr.sort()
        astr = ''.join(arr)
        sha1str = hashlib.sha1(astr).hexdigest()
        print("sha1str:", sha1str, ",sign:", sign)
        if sign == sha1str:
            return True
        else:
            return False

    def get(self):
        # sign = self.get_argument("signature","")
        # tt = self.get_argument("timestamp",0)
        # nonce=self.get_argument("nonce",0)
        echostr = self.get_argument("echostr", "")
        # rs={"status":0}
        # arr = [TOKEN,tt,nonce]
        # print "arr:",arr
        # arr.sort()
        # print "sorted arr:",arr
        # str = ''.join(arr)
        # sha1str = hashlib.sha1(str).hexdigest()
        # print "str:%s,sha1str:%s,sign:%s"%(str,sha1str,sign)
        print("echostr:", echostr)
        if self.checksign():
            self.write(echostr)
        else:
            self.write(0)

    def post(self):
        self.get()
