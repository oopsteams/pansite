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
    code = CharField(max_length=128, null=False, index=True)
    cover = CharField(max_length=64)
    opf = CharField(max_length=64)
    ncx = CharField(max_length=64)
    unziped = IntegerField(null=False, default=0)
    ftype = IntegerField(null=False, default=0)  # 绘本:2
    lh = CharField(max_length=32, default='')  # 默认行高
    ftsize = IntegerField(null=False, default=0)  # 默认字号
    authors = CharField(max_length=128, null=True)  # 作者等信息
    rating = IntegerField(null=False, default=0)  # 默认平分
    series = CharField(max_length=128, null=True)  # 丛书等信息
    publisher = CharField(max_length=128, null=True)  # 出版等信息
    pubdate = DateTimeField(index=True, null=True)  # 出版日期 可能为空值
    idx = IntegerField(null=False, default=0, index=True)
    pin = IntegerField(null=False, default=0, index=True)
    is_pack = IntegerField(null=False, default=0)  # 默认非打包处理
    pack_id = IntegerField(null=False, default=0)  # 打包Book ID

    @classmethod
    def field_names(cls):
        return ["id", "code", "account_id", "ref_id", "price", "name", "unziped", "idx", "cover", "pin", "opf", "ncx",
                "ftype", "lh", "ftsize", "authors", "rating", "series", "publisher", "pubdate", "is_pack", "pack_id"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class BookShelf(Model):
    id = AutoField()
    wx_id = IntegerField(null=False, default=0)
    code = CharField(max_length=128, null=False, index=True)
    lastopen = IntegerField(null=False, default=0)
    top = IntegerField(null=False, default=0)

    class Meta:
        database = db

    @classmethod
    def field_names(cls):
        return ["id", "wx_id", "lastopen", "code", "top"]

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


class StudyEssay(BaseModel):
    id = AutoField()
    title = CharField(max_length=16, null=False)
    authors = CharField(max_length=32, null=False)
    info = CharField(max_length=32, null=False)
    tag = CharField(max_length=32, null=False)
    description = CharField(max_length=256, null=False)
    hanzi = IntegerField(null=False, index=True)
    idx = IntegerField(null=False, default=0, index=True)
    pin = IntegerField(null=False, default=0, index=True)

    @classmethod
    def field_names(cls):
        return ["id", "title", "authors", "info", "hanzi", "idx", "pin", "tag", "description"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class StudyHanzi(BaseModel):
    id = AutoField()
    txt = CharField(max_length=2, null=False)
    py = CharField(max_length=10, null=False)
    cap = CharField(max_length=1, null=False)
    bs = CharField(max_length=1, null=False)
    sds = CharField(max_length=4, null=False)
    num = IntegerField(null=False, index=True)
    struct = CharField(max_length=4, null=False)
    demo = CharField(max_length=16, null=False)
    worder = CharField(max_length=64, null=False)
    zc = CharField(max_length=16, null=False)
    zy = CharField(max_length=64, null=False)
    txt_gif = CharField(max_length=128, null=True)

    @classmethod
    def field_names(cls):
        return ["id", "txt", "py", "cap", "bs", "sds", "num", "struct", "demo", "worder", "zc", "zy", "txt_gif"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class EssayHanzi(Model):
    essay = IntegerField(null=False, default=0)
    hz = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return ["essay", "hz"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())

    class Meta:
        database = db
        primary_key = CompositeKey('essay', 'hz')


