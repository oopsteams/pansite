# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/26
"""
from dao.models import db, query_wrap_db, Accounts, AccountExt, AccountWxExt, StudyProps, AppCfg
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
    @query_wrap_db
    def query_access_token(cls) -> dict:
        ac: AppCfg = AppCfg.select().where(AppCfg.key == "access_token").first()
        if ac:
            return dict(access_token=ac.val, expires_in=int(ac.type))
        return None

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
    def new_wx_account_ext(cls, openid, session_key, guest, source, wx_user_dict):
        with db:
            wxacc: AccountWxExt = AccountWxExt(openid=openid, session_key=session_key, account_id=guest.id, source=source)
            if "avatarUrl" in wx_user_dict:
                wxacc.avatar = wx_user_dict["avatarUrl"]
            if "city" in wx_user_dict:
                wxacc.city = wx_user_dict["city"]
            if "country" in wx_user_dict:
                wxacc.country = wx_user_dict["country"]
            if "gender" in wx_user_dict:
                wxacc.gender = wx_user_dict["gender"]
            if "language" in wx_user_dict:
                wxacc.language = wx_user_dict["language"]
            if "nickName" in wx_user_dict:
                wxacc.nickname = wx_user_dict["nickName"]
            if "province" in wx_user_dict:
                wxacc.province = wx_user_dict["province"]

            wxacc.save(force_insert=True)
            return wxacc

    @classmethod
    def new_study_props(cls, wx_id, code, val, idx):
        with db:
            sp: StudyProps = StudyProps(wx_id=wx_id, code=code, val=val, idx=idx)
            sp.save(force_insert=True)
            return sp

    @classmethod
    def update_access_token(cls, access_token, expires_in) -> AppCfg:
        with db:
            ac: AppCfg = AppCfg.select().where(AppCfg.key == "access_token").first()
            if not ac:
                ac = AppCfg(key="access_token", name="access_token", val=access_token, pin=1, type=str(expires_in))
                ac.save(force_insert=True)
            else:
                ac.val = access_token
                ac.type = str(expires_in)
                AppCfg.update(val=ac.val, type=ac.type).where(AppCfg.key == "access_token").execute()
            return ac
