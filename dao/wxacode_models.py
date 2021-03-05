# -*- coding: utf-8 -*-
"""
Created by susy at 2021/3/5
"""
from peewee import *
from dao.base import db, BaseModel
from utils import object_to_dict


class WxaGenCode(BaseModel):
    id = AutoField()
    occupied_at = IntegerField(null=False, default=0)
    pin = SmallIntegerField(null=False, default=0, index=True)  # 0:init,1:gen_code,2:occupied,3:used

    @classmethod
    def field_names(cls):
        return ["id", "pin"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class WxaAccessToken(BaseModel):
    id = AutoField()
    appid = CharField(max_length=32, null=False)
    expires_in = IntegerField(null=False, default=0)
    expires_at = IntegerField(null=False, default=0)
    access_token = CharField(max_length=128, null=False)
    pin = SmallIntegerField(null=False, default=0)  # 0:init,1:gen_code,2:occupied,3:used

    @classmethod
    def field_names(cls):
        return ["id", "appid", "expires_in", "access_token", "pin"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)

