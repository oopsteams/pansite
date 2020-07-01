# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/30
"""
from controller.action import BaseHandler
from controller.book.book_service import book_service
import json


class BookHandler(BaseHandler):

    def parseCMD(self, params):
        cmd = u'' + params.get("cmd", "")
        rs = {"status": 0}
        # print("header", header)
        if "list" == cmd:
            page = params.get("page", "0")
            size = int(params.get('size', '6'))
            offset = int(page) * size
            bl = book_service.list(self.guest, offset, size)
            rs["hasnext"] = len(bl) == size
            rs["list"] = bl
        elif "pinyin" == cmd:
            code = params.get("code", "0")
            chapter = params.get("c", "")
            if self.user_id and self.token and self.user_id != self.guest.id:
                rs = book_service.parse_py_epub(self.context, code, chapter)
            else:
                rs = {'state': -1, 'err': 'user state wrong!'}
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
