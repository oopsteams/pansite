# -*- coding: utf-8 -*-
"""
Created by susy at 2020/2/5
"""
from controller.action import BaseHandler
from controller.auth_service import auth_service
import json


class ProductHandler(BaseHandler):

    def post(self):
        self.get()

    def get(self):
        path = self.request.path
        if path.endswith("/pro_list"):
            pass
