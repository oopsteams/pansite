# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/30
"""
from controller.action import BaseHandler
from controller.book.book_service import book_service
from utils import decrypt_id, constant
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
        elif "se" == cmd:
            kw = params.get("kw", None)
            mtag = params.get("mtag", None)
            tag = params.get("tag", None)
            # tag = url_decode(tag)
            page = params.get("page", "0")
            size = params.get("size", "20")
            # print("kw:", kw)
            # print("source:", source)
            rs = book_service.search(mtag, tag, kw, page, int(size))
        elif "pinyin" == cmd:
            code = params.get("code", "0")
            chapter = params.get("c", "")
            if self.user_id and self.token and self.user_id != self.guest.id:
                rs = book_service.parse_py_epub(self.context, code, chapter)
            else:
                rs = {'state': -1, 'err': 'user state wrong!'}
        elif "shelf" == cmd:
            page = int(params.get("page", "0"))
            size = int(params.get("size", "10"))
            offset = page * size
            fuzzy_wx_id = params.get('uid', None)
            if not fuzzy_wx_id:
                wx_id = 0
            else:
                wx_id = decrypt_id(fuzzy_wx_id)
            if wx_id:
                rs["datas"] = book_service.shelf_book_list(wx_id, offset, size)
                rs["maxcount"] = constant.SHELF["COUNT"]
                rs["hasnext"] = len(rs["datas"]) == size
        elif "shelfsync" == cmd:
            datas = params.get("datas", [])
            fuzzy_wx_id = params.get('uid', None)
            if not fuzzy_wx_id:
                wx_id = 0
            else:
                wx_id = decrypt_id(fuzzy_wx_id)
            if wx_id:
                rs_val = book_service.sync_shelf_book_list(wx_id, datas)
                rs["value"] = rs_val
        elif "shelfremove" == cmd:
            book_shelf_code = params.get("code", None)
            fuzzy_wx_id = params.get('uid', None)
            if not fuzzy_wx_id:
                wx_id = 0
            else:
                wx_id = decrypt_id(fuzzy_wx_id)

            if wx_id and book_shelf_code:
                rs["value"] = book_service.remove_shelf_book(wx_id, book_shelf_code)

        elif "recoverbkes" == cmd:
            if self.token:
                from controller.open_service import open_service
                rs = open_service.recover_bk_es()

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
