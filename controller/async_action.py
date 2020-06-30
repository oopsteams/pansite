# -*- coding: utf-8 -*-
"""
Created by susy at 2020/3/16
"""
from controller.action import BaseHandler
from tornado.web import authenticated
from controller.async_service import async_service


class AsyncHandler(BaseHandler):

    def post(self):
        self.get()

    @authenticated
    def get(self):
        self.release_db = False
        path = self.request.path
        if path.endswith("/checkstate"):
            key_prefix = "client:ready:"
            rs = async_service.checkout_key_state(key_prefix, self.user_id)
            if rs:
                self.to_write_json(rs)
            else:
                self.to_write_json({'state': 0})

        elif path.endswith("/scanepudstate"):
            key_prefix = "epud:ready:"
            rs = async_service.checkout_key_state(key_prefix, self.guest.id)
            if rs:
                self.to_write_json(rs)
            else:
                self.to_write_json({'state': 0})