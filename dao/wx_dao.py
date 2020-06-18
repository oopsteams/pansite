# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/26
"""
from dao.models import db, query_wrap_db, Accounts, AccountExt, AccountWxExt, StudyProps
from dao.mdao import DataDao
from utils import utils_es, get_now_datetime, obfuscate_id


class WxDao(object):

    # query data
    @classmethod
    @query_wrap_db
    def wx_account(cls, open_id) -> AccountWxExt:
        return AccountWxExt.select().where(AccountWxExt.openid == open_id).first()

    @classmethod
    @query_wrap_db
    def wx_account_by_id(cls, wx_id) -> AccountWxExt:
        return AccountWxExt.select().where(AccountWxExt.id == wx_id).first()

    @classmethod
    @query_wrap_db
    def wx_props_by_wx_id(cls, wx_id) -> StudyProps:
        return StudyProps.select().where(StudyProps.wx_id == wx_id).order_by(StudyProps.idx.asc())

    @classmethod
    def account_by_id(cls, account_id) -> Accounts:
        return DataDao.account_by_id(account_id)

    # update data
    @classmethod
    def update_wx_account(cls, params, wx_id):
        _params = {p: params[p] for p in params if p in AccountWxExt.field_names()}
        with db:
            AccountWxExt.update(**_params).where(AccountWxExt.id == wx_id).execute()

    @classmethod
    def update_study_prop(cls, wx_id, code, params):
        _params = {p: params[p] for p in params if p in StudyProps.field_names()}
        with db:
            StudyProps.update(**_params).where(StudyProps.wx_id == wx_id, StudyProps.code == code).execute()

    # new data
    @classmethod
    def new_wx_account_ext(cls, openid, session_key, guest, source):
        with db:
            user_token = None
            wxacc: AccountWxExt = AccountWxExt(openid=openid, session_key=session_key, account_id=guest.id, source=source)
            wxacc.save(force_insert=True)
            return wxacc

    @classmethod
    def new_study_props(cls, wx_id, code, val, idx):
        with db:
            sp: StudyProps = StudyProps(wx_id=wx_id, code=code, val=val, idx=idx)
            sp.save(force_insert=True)
            return sp
