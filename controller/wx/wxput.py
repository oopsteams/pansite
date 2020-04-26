# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/26
"""
from controller.action import BaseHandler
from controller.auth_service import auth_service
from utils.constant import USER_TYPE
import json


class WXAppPut(BaseHandler):

    def parsePutCMD(self, **params):
        cmd = u'' + params.get("cmd", "")
        print("cmd:", cmd)
        rs = {"status": 0}

        return rs

    def get(self):

        cmd = self.get_argument("cmd", "")
        name = self.get_argument("name", "")
        params = {"cmd": cmd, "name": name}
        if "openid" == cmd:
            params["code"] = self.get_argument("code", "")
        rs = self.parsePutCMD(**params)

        self.to_write_json(rs)

    def post(self):
        # self.get()
        rs = {"status": 0}
        cmd = self.get_argument("cmd", "")
        bd = self.request.body
        _params = json.loads(bd)
        if cmd:
            _params['cmd'] = cmd
        if _params:
            rs = self.parsePutCMD(**_params)
        self.to_write_json(rs)
