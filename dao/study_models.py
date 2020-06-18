# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/18
"""
from peewee import *
from dao.base import db
from utils import object_to_dict


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


