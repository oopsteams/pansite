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
        return BASE_FIELDS + ["pay_id", "account_type", "balance", "currency", "start_at", "expire_at", "source",
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
