# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/29
"""
from peewee import *
from dao.base import db, BaseModel, BASE_FIELDS, db_create_field_sql
from utils import object_to_dict


class Category(BaseModel):
    cid = AutoField()
    name = CharField(null=True, max_length=64)
    pin = SmallIntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["cid", "name", "pin"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class CateCate(Model):
    cid = IntegerField(null=False, default=0)
    pcid = IntegerField(null=False, default=0)
    lvl = SmallIntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return ["cid", "pcid", "lvl"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())

    class Meta:
        database = db
        primary_key = CompositeKey('cid', 'pcid')


class SPUStruct(BaseModel):
    structid = AutoField()
    name = CharField(null=True, max_length=64)
    desc = CharField(null=True, max_length=64)
    field = CharField(null=True, max_length=32)
    startid = IntegerField(null=False, default=0)
    cid = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["structid", "name", "desc", "field", "startid", "cid"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class SPUModel(Model):

    class Meta:
        database = db

    id = AutoField()
    created_at = DateTimeField(index=True, constraints=db_create_field_sql())
    name = CharField(null=True, max_length=64)
    weight = FloatField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return ["id", "created_at", "name", "weight"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class Brand(SPUModel):
    pass


class NetWeight(SPUModel):
    min = IntegerField(null=False, default=0)
    mmax = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return SPUModel.field_names() + ["min", "mmax"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class SweetNess(SPUModel):
    min = FloatField(null=False, default=0)
    mmax = FloatField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return SPUModel.field_names() + ["min", "mmax"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class Subjects(SPUModel):
    pass


class Pack(SPUModel):
    pass


class CourseProduct(BaseModel):
    pid = AutoField()
    name = CharField(null=True, max_length=64)
    netweight = FloatField(null=False, default=0)
    cid = IntegerField(null=False, default=0)
    tpcid = IntegerField(null=False, default=0)
    desc = CharField(null=True, max_length=256)
    ref_id = IntegerField(null=False, default=0)
    pin = SmallIntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["name", "pid", "netweight", "cid", "tpcid", "desc", "ref_id", "pin"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class ProductSpu(Model):
    pid = IntegerField(null=False, default=0)
    spuid = IntegerField(null=False, default=0)
    structid = IntegerField(null=False, default=0)
    ref_id = IntegerField(null=False, default=0)
    pin = SmallIntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return ["pid", "spuid", "structid", "ref_id", "pin"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)

    class Meta:
        database = db
        primary_key = CompositeKey('pid', 'spuid')


class ProductImg(Model):
    pid = IntegerField(null=False, default=0)
    imgurl = CharField(null=True, max_length=128)
    simgurl = CharField(null=True, max_length=128)
    idx = IntegerField(null=False, default=0)
    ref_id = IntegerField(null=False, default=0)
    pin = SmallIntegerField(null=False, default=0)

    class Meta:
        database = db
        primary_key = CompositeKey('pid', 'imgurl')

    @classmethod
    def field_names(cls):
        return ["pid", "imgurl", "simgurl", "ref_id", "pin", "idx"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class Goods(BaseModel):
    gid = AutoField()
    pid = IntegerField(null=False, default=0)  # 商品
    price = IntegerField(null=False, default=0)  # 价格/评分，分
    undertime = DateTimeField(null=False)
    spu = CharField(null=True, max_length=256)
    sku = CharField(null=True, max_length=256)
    ref_id = IntegerField(null=False, default=0)
    pin = SmallIntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["gid", "pid", "price", "undertime", "spu", "sku", "ref_id", "pin"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)
