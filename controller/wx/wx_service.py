# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/26
"""
from controller.base_service import BaseService
from controller.auth_service import auth_service
from controller.payment.payment_service import payment_service
from dao.wx_dao import WxDao
from dao.models import AccountWxExt, Accounts, BASE_FIELDS, StudyProps
import base64
from Crypto.Cipher import AES
from utils import singleton, obfuscate_id, caches, constant, wxapi, get_now_ts
from cfg import WX_API
import arrow
import json


def clear_wx_acc_cache(openid):
    key = "wx_acc_{}".format(openid)
    caches.clear_cache(key)


def wx_acc_to_simple_dict(wx_acc: AccountWxExt):
    if wx_acc:
        return AccountWxExt.to_dict(wx_acc, BASE_FIELDS + ["avatar", "birthday", "marriage", "gender",
                                                           "language", "country", "province", "city", "job",
                                                           "is_realname"])
    return None

@singleton
class WxService(BaseService):

    def __init__(self):
        super().__init__()
        self.appId = WX_API['appid']

    @caches.cache_data("study_props_{1}")
    def queryprop(self, wx_user_id):
        props = WxDao.wx_props_by_wx_id(wx_user_id)
        rs = []
        if props:
            for sp in props:
                rs.append(StudyProps.to_dict(sp, ['wx_id', 'idx']))
        return rs

    def sync_props(self, wx_user_id, props):
        _props = self.queryprop(wx_user_id)
        if _props:
            for p in props:
                WxDao.update_study_prop(wx_user_id, p["c"], {'val': p["v"]})
        else:
            props_map = {i['c']: i['v'] for i in props}
            codes = constant.STUDY["CODES"]
            for idx in range(0, len(codes)):
                c = codes[idx]
                if c in props_map:
                    WxDao.new_study_props(wx_user_id, c, props_map[c], idx)
        caches.clear_cache("study_props_{}".format(wx_user_id))

    def simple_profile(self, account_id, ref_id, wx_user_id, token):
        rs = dict()
        rs['user'] = self.build_simple_user_result(account_id, wx_user_id, token)
        rs['user']['sync'] = 0
        rs["state"] = {
            "signed": False,
            "counter": 0
        }
        balance_rs = payment_service.query_credit_balance(account_id)
        rs["balance"] = balance_rs
        # au = auth_service.get_auth_user_by_account_id(account_id)
        # if au:
        if ref_id:
            signed_rs = payment_service.check_signed(ref_id)
            if signed_rs:
                rs["state"] = signed_rs
        return rs

    def profile(self, wx_user_id, guest):
        rs = {}
        wx_acc: AccountWxExt = None
        if wx_user_id:
            wx_acc = self.fetch_wx_account(wx_user_id)
        # wx_acc: AccountWxExt = AccountWxExt(openid="oGZUI0egBJY1zhBYw2KhdUfwVJJE",
        #                                     nickname="Band",
        #                                     id=0,
        #                                     account_id=guest.id)
        acc: Accounts = self.get_acc_by_wx_acc(wx_acc_to_simple_dict(wx_acc), guest)
        rs['user'] = self.build_user_result(acc, wx_acc)
        rs['user']['sync'] = 1
        rs["state"] = {
            "signed": False,
            "counter": -1
        }
        if wx_acc:
            # {'uid': uid, 'sync': 0, 'pin': ub.pin, 'ri': ub.setting.rinclude, 're': rexclude,
            #               'name': ub.user.rname}
            rs['openid'] = wx_acc.openid
            if guest.id != wx_acc.account_id:
                rs["state"]["counter"] = 0;
                balance_rs = payment_service.query_credit_balance(wx_acc.account_id)
                rs["balance"] = balance_rs
                au = auth_service.get_auth_user_by_account_id(wx_acc.account_id)
                if au:
                    rs['user']['sync'] = 0
                    signed_rs = payment_service.check_signed(au.ref_id)
                    if signed_rs:
                        rs["state"] = signed_rs

        return rs

    def build_user_result(self, acc: Accounts, wx_acc: AccountWxExt):
        lud = arrow.now(self.default_tz)
        if acc.login_updated_at:
            lud = arrow.get(acc.login_updated_at).replace(tzinfo=self.default_tz)
        result = dict(
            token=acc.login_token,
            login_at=int(arrow.get(lud).timestamp * 1000),
            id=acc.fuzzy_id
                      )
        result['id'] = acc.fuzzy_id

        if wx_acc:
            result['portrait'] = wx_acc.avatar
            result['uid'] = obfuscate_id(wx_acc.id)
            result['pin'] = 0
            result['sync'] = 0
            result['ri'] = []
            result['re'] = []
            result['name'] = wx_acc.nickname

        return result

    def build_simple_user_result(self, account_id, wx_id, login_token):
        lud = arrow.now(self.default_tz)
        result = dict(
            token=login_token,
            login_at=int(arrow.get(lud).timestamp * 1000),
        )
        sync = 0
        if not wx_id:
            sync = 1
        result['id'] = obfuscate_id(account_id)
        result['uid'] = obfuscate_id(wx_id)
        result['pin'] = 0
        result['sync'] = sync
        result['ri'] = []
        result['re'] = []

        return result

    def get_acc_by_wx_acc(self, wx_acc_dict: dict, guest: Accounts):
        if wx_acc_dict:
            acc_id = wx_acc_dict['account_id']
            if guest and guest.id == acc_id:
                acc = guest
            else:
                acc = WxDao.account_by_id(acc_id)
            return acc
        else:
            return guest

    def guest_profile(self, guest):
        rs = dict()
        rs['user'] = dict(
            uid=obfuscate_id(guest.id),
            pin=0,
            sync=1,
            ri=[],
            re=[]
        )
        rs["state"] = {
            "signed": False,
            "counter": -1
        }
        return rs

    def wx_sync_login(self, openid, session_key, guest, wx_user_dict, source=0):
        if openid:
            # wx_acc_dict = self.checkout_wx_acc_by_openid(openid)
            wx_acc: AccountWxExt = WxDao.wx_account(openid)
            acc = self.get_acc_by_wx_acc(wx_acc_to_simple_dict(wx_acc), guest)
            sync = 1
            rs = dict()
            if not wx_acc:
                wx_acc = WxDao.new_wx_account_ext(openid, session_key, guest, source, wx_user_dict)
                print("reg source:", source)
                if wx_acc and source:
                    payment_service.reward_credit_by_invite(source, wx_acc.id)
                result = auth_service.wx_sync_login(wx_acc)
                tk = result['token']
                acc.login_token = tk
                login_at = result['login_at']
                if wx_acc.account_id != guest.id:
                    ref_id = auth_service.query_ref_id_by_account_id(wx_acc.account_id)
                    if ref_id:
                        rs = self.simple_profile(wx_acc.account_id, ref_id, wx_acc.id, tk)
                        if login_at:
                            rs['user']['login_at'] = login_at

            else:
                WxDao.update_wx_account({"session_key": session_key}, wx_acc.id)
                if wx_acc.account_id != guest.id:
                    sync = 0
                    ref_id = auth_service.query_ref_id_by_account_id(wx_acc.account_id)
                    if ref_id:
                        result = auth_service.login_check_user(acc, source="wx")
                        # tk = result['token']
                        # result = auth_service.wx_sync_login(wx_acc)
                        tk = result['token']
                        login_at = result['login_at']
                        acc.login_token = tk
                        rs = self.simple_profile(wx_acc.account_id, ref_id, wx_acc.id, tk)
                        if login_at:
                            rs['user']['login_at'] = login_at

            _user = self.build_user_result(acc, wx_acc)
            if _user and 'user' in rs:
                for k in _user:
                    if k == 'login_at':
                        continue
                    rs['user'][k] = _user[k]
            else:
                rs['user'] = _user
            # rs['uid'] = obfuscate_id(wx_acc.id)
            rs['openid'] = wx_acc.openid
            rs['name'] = wx_acc.nickname
            rs['user']['sync'] = sync
            return rs
        return {}

    def fetch_wx_account(self, wx_id) -> AccountWxExt:
        return WxDao.wx_account_by_id(wx_id)

    def fetch_user_by_id(self, user_id):
        return WxDao.account_by_id(user_id)

    def update_wx_account(self, info, wx_acc: AccountWxExt):
        wx_id = wx_acc.id
        params = dict(
            nickname=info.get('nickName', ''),
            avatar=info.get('avatarUrl', ''),
            gender=info.get('gender', 0),
            language=info.get('language', 'zh_CN'),
            country=info.get('country', ''),
            province=info.get('province', ''),
            city=info.get('city', '')
        )
        wx_acc.nickname = params['nickname']
        wx_acc.gender = params['gender']
        wx_acc.country = params['country']
        wx_acc.province = params['province']
        wx_acc.city = params['city']
        if 'unionId' in info:
            params['unionid'] = info['unionId']

        WxDao.update_wx_account(params, wx_id)

    def extractUserInfo(self, sk, encryptedData, iv):
        aeskey = base64.b64decode(sk)
        decodeData = base64.b64decode(encryptedData)
        iv = base64.b64decode(iv)
        cipher = AES.new(aeskey, AES.MODE_CBC, iv)
        codes = cipher.decrypt(decodeData)
        _codes = self._unpad(codes)
        print("extractUserInfo sk:", sk)
        print("extractUserInfo _codes:", _codes)
        decrypted = json.loads(_codes)
        if decrypted['watermark']['appid'] != self.appId:
            raise Exception('Invalid Buffer')

        return decrypted

    def _unpad(self, s):
        return s[:-ord(s[len(s) - 1:])]

    def refresh_access_token(self):
        jsonrs = wxapi.get_access_token()
        if "access_token" in jsonrs:
            access_token = jsonrs["access_token"]
            expires_in = jsonrs["expires_in"]
            ac = WxDao.update_access_token(access_token, expires_in + get_now_ts())
            return dict(access_token=ac.val, expires_in=int(ac.type))
        return None

    @caches.cache_data("access_token", timeout_seconds=lambda s, rs: rs["to"])
    def get_valid_access_token(self):
        rs = WxDao.query_access_token()
        if not rs or rs["expires_in"] <= get_now_ts():
            new_rs = self.refresh_access_token()
            if new_rs:
                new_rs["to"] = new_rs["expires_in"] - get_now_ts() - 1
            return new_rs
        if rs:
            rs["to"] = rs["expires_in"] - get_now_ts() - 1
        return rs


wx_service = WxService()
