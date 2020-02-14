# -*- coding: utf-8 -*-
"""
Created by susy at 2020/1/28
"""
from controller.action import BaseHandler
from controller.auth_service import auth_service
from tornado.web import authenticated
from utils.constant import USER_TYPE
import json


class UserHandler(BaseHandler):

    def post(self):
        self.get()

    def get_current_user(self):
        rs = super().get_current_user()
        if rs:
            if self.user_type != USER_TYPE['ALL']:
                print("user type:", self.user_type)
                return False
        return rs

    @authenticated
    def get(self):
        path = self.request.path
        if path.endswith("/user_list"):
            pin = self.get_argument("pin", None)
            _type = self.get_argument("type", None)
            page = int(self.get_argument("page", "0"))
            rs, has_next = auth_service.user_list(pin, _type, page)
            self.to_write_json({"data": rs, "has_next": has_next, "has_prev": page > 0})
        elif path.endswith("/org_list"):
            page = int(self.get_argument("page", "0"))
            rs, has_next = auth_service.org_list(int(page))
            self.to_write_json({"data": rs, "has_next": has_next, "has_prev": page > 0})
        elif path.endswith("/fun_list"):
            page = int(self.get_argument("page", "0"))
            rs, has_next = auth_service.fun_list(int(page))
            self.to_write_json({"data": rs, "has_next": has_next, "has_prev": page > 0})
        elif path.endswith("/role_list"):
            page = int(self.get_argument("page", "0"))
            rs, has_next = auth_service.role_list(int(page))
            fun_list, _ = auth_service.fun_list(0)
            self.to_write_json({"data": rs, "fun_list": fun_list, "has_next": has_next, "has_prev": page > 0})
        elif path.endswith("/role_detail"):
            _id = int(self.get_argument("id"))
            rs = auth_service.role_detail(_id)
            self.to_write_json({"data": rs})
        elif path.endswith("/user_detail"):
            fuzz_id = self.get_argument("id", None)
            rs = {}
            if fuzz_id:
                rs = auth_service.get_auth_user_by_id(fuzz_id)
                # print("user_detail rs:", rs)
            self.to_write_json(rs)
        elif path.endswith("/user_role_detail"):
            fuzz_id = self.get_argument("id", None)
            rs = {}
            if fuzz_id:
                rs = auth_service.get_auth_user_role_by_id(fuzz_id)
            self.to_write_json(rs)
        elif path.endswith("/user_org_detail"):
            fuzz_id = self.get_argument("id", None)
            rs = {}
            if fuzz_id:
                rs = auth_service.get_auth_user_org_by_id(fuzz_id)
            self.to_write_json(rs)
        elif path.endswith("/new_role"):
            rs = {}
            params = json.loads(self.request.body)
            print('body params:', params)
            auth_service.update_role(params)
            self.to_write_json(rs)
        elif path.endswith("/new_org"):
            rs = {}
            params = json.loads(self.request.body)
            print('body params:', params)
            auth_service.update_org(params)
            self.to_write_json(rs)
        elif path.endswith("/new_user"):
            params = json.loads(self.request.body)
            print('body params:', params)
            isok = auth_service.update_user(params)
            self.to_write_json({'ok': isok})
        else:
            self.to_write_json({})



