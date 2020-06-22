# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/22
"""
from controller.action import BaseHandler
from controller.wx.wx_service import wx_service
from utils import wxapi
import json


class WXAppKf(BaseHandler):

    def parseCMD(self, params):
        cmd = u'' + params.get("cmd", "")
        rs = {"status": 0}
        # print("header", header)
        at_dict = wx_service.get_valid_access_token()
        if "getkflist" == cmd:
            if at_dict:
                kflist = wxapi.getkflist(at_dict["access_token"])
                print("kflist:", kflist)
            pass
        return rs

    def get(self):
        # self.check_header("wx get")
        # rs = {"status": 0}
        cmd = self.get_argument("cmd", "")
        name = self.get_argument("name", "")
        params = {"cmd": cmd, "name": name}

        arguments = self.request.query_arguments
        if arguments:
            for k in arguments:
                d = arguments[k]
                if isinstance(d, list):
                    if len(d) == 1:
                        params[k] = d[0].decode()
                    else:
                        params[k] = d
        print("params:", params)
        rs = self.parseCMD(params)
        print("rs:", rs)
        self.to_write_json(rs)

    def post(self):
        rs = {"status": 0}
        cmd = self.get_argument("cmd", "")
        bd = self.request.body
        _params = json.loads(bd)
        if cmd:
            _params['cmd'] = cmd
        if _params:
            # rs = yield gen.Task(self.parseCMD,**_params)
            # print "yield rs:",rs
            rs = self.parseCMD(_params)
        print("rs:", rs)
        self.to_write_json(rs)
