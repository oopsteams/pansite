# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/26
"""
from dao.models import db, query_wrap_db, Accounts, AccountExt, AccountWxExt, StudyProps, AppCfg, KfMsg, Kf, PlanTime, PlanSubject
from dao.mdao import DataDao
from peewee import ModelSelect
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
        return dict()

    @classmethod
    @query_wrap_db
    def query_pan_headers(cls, wx_id) -> list:
        ms: ModelSelect = PlanTime.select().where(PlanTime.wx_id == wx_id)
        rs = []
        if ms:
            for pt in ms:
                rs.append(dict(txt=[pt.info, pt.val], id=pt.code))
        return rs

    @classmethod
    @query_wrap_db
    def query_pan_cells(cls, wx_id) -> list:
        ms: ModelSelect = PlanSubject.select().where(PlanSubject.wx_id == wx_id)
        rs = []
        if ms:
            for ps in ms:
                val = ''
                if ps.val:
                    val = ps.val
                rs.append(dict(txt=[ps.info], id=ps.code, val=val))
        return rs

    @classmethod
    @query_wrap_db
    def query_one_kf(cls, fr) -> Kf:
        kf: Kf = Kf.select().where(Kf.last_fr == fr).first()
        if not kf:
            kf = Kf.select().limit(1).first()
        return kf

    @classmethod
    @query_wrap_db
    def query_kf_list(cls, cnt=50) -> list:
        return Kf.select().offset(0).limit(cnt)

    @classmethod
    @query_wrap_db
    def query_kf_msg_list(cls, pin, offset=0, cnt=50) -> list:
        return KfMsg.select().where(KfMsg.pin == pin).offset(offset).limit(cnt)

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

    @classmethod
    def update_kf_msg_pin(cls, msg_id, pin):
        with db:
            KfMsg.update(pin=pin).where(KfMsg.msg_id == msg_id).execute()

    @classmethod
    def update_kf_msg(cls, msg_id, to, fr, msg_ct, msg_type, content):
        with db:
            kfmsg: KfMsg = KfMsg.select().where(KfMsg.msg_id == str(msg_id)).first()
            if not kfmsg:
                kfmsg = KfMsg(msg_id=str(msg_id), to=to, fr=fr, msg_ct=msg_ct, msg_type=msg_type, content=content, pin=0)
                kfmsg.save(force_insert=True)
            return kfmsg

    @classmethod
    def update_kf_cnt(cls, kf_id, last_fr, incr):
        with db:
            Kf.update(cnt=Kf.cnt+incr, last_fr=last_fr).where(Kf.kf_id == kf_id).execute()

    @classmethod
    def update_kf(cls, kf_id, kf_params):
        with db:

            kf: Kf = Kf.select().where(Kf.kf_id == kf_id).first()
            if not kf:
                kf = Kf(**kf_params)
                kf.pin = 0
                kf.cnt = 0
                kf.save(force_insert=True)
            else:
                _params = {p: kf_params[p] for p in kf_params if p in Kf.field_names()}
                Kf.update(**_params).where(Kf.kf_id == kf_id).execute()

    @classmethod
    def update_plan_time(cls, wx_id, code, info, time_val):
        with db:
            pt: PlanTime = PlanTime.select().where(PlanTime.code == code, PlanTime.wx_id == wx_id).first()
            if not pt:
                pt = PlanTime(info=info, val=time_val, wx_id=wx_id)
                pt.save(force_insert=True)
            else:
                PlanTime.update(info=info, val=time_val).where(PlanTime.code == code, PlanTime.wx_id == wx_id).execute()

    @classmethod
    def update_plan_sub(cls, wx_id, code, info, product_code=None):
        with db:
            ps: PlanSubject = PlanSubject.select().where(PlanSubject.code == code, PlanSubject.wx_id == wx_id).first()
            if not ps:
                ps = PlanSubject(info=info, wx_id=wx_id)
                if product_code:
                    ps.val = product_code
                ps.save(force_insert=True)
            else:
                params = {"info": info}
                if product_code:
                    params["val"] = product_code
                PlanSubject.update(**params).where(PlanSubject.code == code, PlanSubject.wx_id == wx_id).execute()
