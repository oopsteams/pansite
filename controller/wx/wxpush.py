# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/21
"""
from controller.action import BaseHandler
from cfg import WX_API
import hashlib
from controller.wx.wx_service import wx_service
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
        arr = [WX_API['token'], tt, nonce]
        arr.sort()
        astr = ''.join(arr)
        sha1str = hashlib.sha1(astr.encode("utf8")).hexdigest()
        print("sha1str:", sha1str, ",sign:", sign)
        if sign == sha1str:
            return True
        else:
            return False

    def parse_msg(self, params):
        if self.checksign():
            ToUserName = params.get("ToUserName", None)
            FromUserName = params.get("FromUserName", None)
            CreateTime = params.get("CreateTime", 0)
            MsgType = params.get("MsgType", "text")
            Content = params.get("Content", "")
            MsgId = params.get("MsgId", 0)
            print("ToUserName:", ToUserName, ",FromUserName:", FromUserName, ",CreateTime:", CreateTime, ",MsgType:", MsgType, ",MsgId:", MsgId, ",Content:", Content)
            wx_service.put_kf_msg(MsgId, ToUserName, FromUserName, CreateTime, MsgType, Content)
            self.write("success")
        else:
            self.write(0)

    def get(self):
        self.parse_msg({})

    def post(self):
        bd = self.request.body
        _params = {}
        if bd:
            try:
                _params = json.loads(bd)
            except Exception:
                pass
        self.parse_msg(_params)
