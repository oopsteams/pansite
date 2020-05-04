# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/26
"""
from controller.base_service import BaseService
from controller.auth_service import auth_service
from dao.wx_dao import WxDao
from dao.models import AccountWxExt, Accounts
import base64
from Crypto.Cipher import AES
from utils import singleton, obfuscate_id
from cfg import WX_API
import arrow
import json


@singleton
class WxService(BaseService):

    def __init__(self):
        super().__init__()
        self.appId = WX_API['appid']

    def profile(self, wx_user_id, guest):
        rs = {}
        # wx_acc: AccountWxExt = self.fetch_wx_account(wx_user_id)
        wx_acc: AccountWxExt = AccountWxExt(openid="oGZUI0egBJY1zhBYw2KhdUfwVJJE",
                                            nickname="Band",
                                            id=0,
                                            account_id=guest.id)
        acc: Accounts = self.get_acc_by_wx_acc(wx_acc, guest)
        rs['user'] = self.build_user_result(acc, wx_acc)
        if wx_acc:
            # {'uid': uid, 'sync': 0, 'pin': ub.pin, 'ri': ub.setting.rinclude, 're': rexclude,
            #               'name': ub.user.rname}
            rs['openid'] = wx_acc.openid

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

    def get_acc_by_wx_acc(self, wx_acc: AccountWxExt, guest: Accounts):
        if wx_acc:
            acc_id = wx_acc.account_id
            if guest and guest.id == acc_id:
                acc = guest
            else:
                acc = WxDao.account_by_id(acc_id)
            return acc
        else:
            return guest

    def wx_sync_login(self, openid, session_key, guest):
        if openid:
            wx_acc = WxDao.wx_account(openid)
            acc = self.get_acc_by_wx_acc(wx_acc, guest)
            if not wx_acc:
                wx_acc = WxDao.new_wx_account_ext(openid, session_key, guest)
            # rs = auth_service.login_check_user(acc, False, 'WX')
            rs = dict()
            rs['user'] = self.build_user_result(acc, wx_acc)
            rs['uid'] = obfuscate_id(wx_acc.id)
            rs['openid'] = wx_acc.openid
            rs['name'] = wx_acc.nickname
            return rs
        return {}

    def fetch_wx_account(self, wx_id) -> AccountWxExt:
        return WxDao.wx_account_by_id(wx_id)

    def fetch_user_by_id(self, user_id):
        return WxDao.account_by_id(user_id)

    def update_wx_account(self, info, wx_id):
        params = dict(
            nickname=info.get('nickName', ''),
            avatar=info.get('avatarUrl', ''),
            gender=info.get('gender', 0),
            language=info.get('language', 'zh_CN'),
            country=info.get('country', ''),
            province=info.get('province', ''),
            city=info.get('city', '')
        )
        if 'unionId' in info:
            params['unionid'] = info['unionId']

        WxDao.update_wx_account(params, wx_id)

    def extractUserInfo(self, sk, encryptedData, iv):
        aeskey = base64.b64decode(sk)
        decodeData = base64.b64decode(encryptedData)
        iv = base64.b64decode(iv)
        cipher = AES.new(aeskey, AES.MODE_CBC, iv)
        codes = cipher.decrypt(encryptedData)
        _codes = self._unpad(codes)
        decrypted = json.loads(_codes)
        if decrypted['watermark']['appid'] != self.appId:
            raise Exception('Invalid Buffer')

        return decrypted

    def _unpad(self, s):
        return s[:-ord(s[len(s) - 1:])]


wx_service = WxService()
