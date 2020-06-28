# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/3
"""
from peewee import *
from dao.base import db, BaseModel, BASE_FIELDS, db_create_field_sql
from utils import object_to_dict


class PaymentAccount(BaseModel):
    pay_id = AutoField()
    account_type = SmallIntegerField(default=0)
    amount = IntegerField(default=0)
    frozen_amount = IntegerField(default=0)
    balance = IntegerField(default=0)  # 余额
    currency = CharField(max_length=10, default="credit")
    start_at = DateTimeField(null=True, index=True)
    expire_at = DateTimeField(null=True, index=True)
    source = CharField(max_length=64, default="", index=True)
    account_id = IntegerField(null=False, index=True)
    ref_id = IntegerField(null=False, index=True)
    nounce = BigIntegerField(default=0)  # 同步时间戳(credit records)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["pay_id", "account_type", "amount", "frozen_amount", "balance", "currency", "start_at", "expire_at", "source",
                              "account_id", "ref_id", "nounce"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class CreditRecord(BaseModel):  # state:2 发放,3:已用过
    cr_id = AutoField()
    account_id = IntegerField(null=False, index=True)
    ref_id = IntegerField(null=False, index=True)
    amount = IntegerField(default=0)
    period = IntegerField(default=-1)
    period_unit = CharField(max_length=64, default='')
    start_at = DateTimeField(null=True, index=True)
    end_at = DateTimeField(null=True, index=True)
    source = CharField(max_length=64, default='', null=True, index=True)
    balance = IntegerField(default=0)  # 余额
    counter = IntegerField(default=0)  # 计数器
    tz = CharField(max_length=64, default='')  # 时区 defaut:America/Chicago
    expired = SmallIntegerField(default=0, index=True)  # 过期标识
    nounce = BigIntegerField(default=0)  # 时间戳

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["cr_id", "amount", "period", "period_unit", "start_at", "end_at", "source", "balance",
                              "tz", "expired", "account_id", "ref_id", "nounce", "counter"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)

#  [{'kf_account': 'kf2001@gh_642856204ea2', 'kf_headimgurl': 'http://wx.qlogo.cn/mmhead/Q3auHgzwzM56MJWGvpm67yjkHZIpUIhibNSg7BbVMSY4B8cR88J6LqA/0', 'kf_id': 2001, 'kf_nick': '少余', 'kf_wx': 'RicherSu'}]
class Kf(BaseModel):
    id = AutoField()
    kf_id = IntegerField(default=0, unique=True)
    kf_account = CharField(max_length=64, default='', index=True)
    kf_headimgurl = CharField(max_length=1024)
    kf_nick = CharField(max_length=32)
    kf_wx = CharField(max_length=32)
    last_fr = CharField(max_length=64)
    pin = IntegerField(default=0)
    cnt = IntegerField(default=0, index=True)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "kf_id", "kf_account", "kf_headimgurl", "kf_nick", "kf_wx", "last_fr", "pin", "cnt"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)

# gh_642856204ea2 ,FromUserName: oyfEQ0R0KGe3mVEN8y0gN0Ydg9cQ ,CreateTime: 1592753194 ,MsgType: text ,MsgId: 22802741778032274 ,Content: 在吗？
class KfMsg(BaseModel):
    id = AutoField()
    msg_id = CharField(max_length=64, unique=True)
    to = CharField(max_length=64)
    fr = CharField(max_length=64)
    msg_ct = IntegerField(default=0, index=True)
    msg_type = CharField(max_length=16)
    content = CharField(max_length=1024)
    pin = IntegerField(default=0, index=True)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "msg_id", "to", "fr", "msg_ct", "msg_type", "content", "pin"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)

