# -*- coding: utf-8 -*-
"""
Created by susy at 2021/3/5
"""
from dao.models import db, query_wrap_db, WxaGenCode, WxaAccessToken
from peewee import ModelSelect, fn
from utils import obfuscate_id, get_now_ts


class WxaDao(object):

    @classmethod
    @query_wrap_db
    def query_unused_list(cls) -> list:
        rs = []
        ms: ModelSelect = WxaGenCode.select().where(WxaGenCode.pin == 0).limit(1000)
        if ms:
            for o in ms:
                rs.append(dict(id=obfuscate_id(o.id)))
        return rs

    @classmethod
    @query_wrap_db
    def query_wxa_code(cls, _id) -> WxaGenCode:
        return WxaGenCode.select().where(WxaGenCode.id == _id).first()

    @classmethod
    @query_wrap_db
    def fetch_one_access_token(cls, appid) -> WxaAccessToken:
        ms = WxaAccessToken.select().where(WxaAccessToken.appid == appid).limit(1)
        if ms:
            return ms[0]
        return None

    @classmethod
    @query_wrap_db
    def fetch_one_wxa_code(cls, pin) -> WxaGenCode:
        return WxaGenCode.select().where(WxaGenCode.pin == pin).order_by(WxaGenCode.id.asc()).limit(1)

    @classmethod
    @query_wrap_db
    def query_wxa_count(cls, pin):
        model_rs: ModelSelect = WxaGenCode.select(fn.count(WxaGenCode.id).alias('count'))
        if pin is not None:
            model_rs = model_rs.where(WxaGenCode.pin == pin)

        if model_rs:
            model_dict = model_rs.dicts()
            if model_dict:
                v = model_dict[0].get('count')
                if v:
                    return v
        return 0

    # update
    @classmethod
    def update_pin(cls, pin, _id, o_pin):

        with db:
            if pin == 2:
                rs = WxaGenCode.update(pin=pin, occupied_at=get_now_ts()).where(WxaGenCode.id == _id, WxaGenCode.pin == o_pin).execute()
            else:
                rs = WxaGenCode.update(pin=pin).where(WxaGenCode.id == _id, WxaGenCode.pin == o_pin).execute()
        return rs

    @classmethod
    def del_gen_code(cls, _id):

        with db:
            WxaGenCode.delete_by_id(_id)

    @classmethod
    def update_access_token(cls, access_token, expires_in, expires_at, _id):

        with db:
            rs = WxaAccessToken.update(access_token=access_token, expires_in=expires_in, expires_at=expires_at
                                       ).where(WxaAccessToken.id == _id).execute()
        return rs

    @classmethod
    def new_wxa_record(cls):
        wgc: WxaGenCode = WxaGenCode(pin=0)
        with db:
            wgc.save(force_insert=True)
            return wgc.id

    @classmethod
    def new_wxa_access_token(cls, appid, access_token, expires_in, expires_at):
        wat: WxaAccessToken = WxaAccessToken(appid=appid, access_token=access_token, expires_in=expires_in, expires_at=expires_at, pin=0)
        with db:
            wat.save(force_insert=True)
            return wat


