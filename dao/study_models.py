# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/18
"""
from peewee import *
from dao.base import db, BaseModel
from utils import object_to_dict


class StudyBook(BaseModel):
    id = AutoField()
    account_id = IntegerField(null=False, index=True)
    ref_id = IntegerField(null=False, index=True)
    price = IntegerField(null=False, default=0)  # 价格/评分，分
    name = CharField(max_length=128, null=False)
    code = CharField(max_length=64, null=False, index=True)
    cover = CharField(max_length=64)
    unziped = IntegerField(null=False, default=0)
    idx = IntegerField(null=False, default=0, index=True)
    pin = IntegerField(null=False, default=0, index=True)

    @classmethod
    def field_names(cls):
        return ["id", "code", "account_id", "ref_id", "price", "name", "unziped", "idx", "cover", "pin"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class StudyProps(Model):
    wx_id = IntegerField(null=False, default=0)
    code = CharField(max_length=16, null=False, index=True)
    val = IntegerField(null=False, default=0)
    idx = IntegerField(null=False, default=0)

    class Meta:
        database = db
        primary_key = CompositeKey('wx_id', 'code')

    @classmethod
    def field_names(cls):
        return ["wx_id", "code", "val", "idx"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class PlanSubject(Model):
    wx_id = IntegerField(null=False, default=0, index=True)
    code = CharField(max_length=16, null=False, index=True)
    info = CharField(max_length=64, null=False)
    val = CharField(max_length=64)
    idx = IntegerField(null=False, default=0)

    class Meta:
        database = db
        primary_key = CompositeKey('wx_id', 'code')

    @classmethod
    def field_names(cls):
        return ["wx_id", "code", "info", "val", "idx"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class PlanTime(Model):
    wx_id = IntegerField(null=False, default=0, index=True)
    code = CharField(max_length=16, null=False, index=True)
    info = CharField(max_length=64, null=False)
    val = CharField(max_length=64, null=False)
    idx = IntegerField(null=False, default=0)

    class Meta:
        database = db
        primary_key = CompositeKey('wx_id', 'code')

    @classmethod
    def field_names(cls):
        return ["wx_id", "code", "info", "val", "idx"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


