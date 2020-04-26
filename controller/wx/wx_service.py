# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/26
"""
from controller.base_service import BaseService
from controller.auth_service import auth_service
from dao.wx_dao import WxDao
from dao.models import AccountWxExt
import base64
from Crypto.Cipher import AES
from utils import singleton
from cfg import WX_API
import json


@singleton
class WxService(BaseService):

    def __init__(self):
        self.appId = WX_API['appid']

    def wx_sync_login(self, openid, session_key, guest):
        if openid:
            wx_acc = WxDao.wx_account(openid)
            if wx_acc:
                acc_id = wx_acc.account_id
                if self.guest and self.guest.id != acc_id:
                    acc = self.guest
                else:
                    acc = WxDao.account_by_id(acc_id)
            else:
                acc = self.guest
                wxacc = WxDao.new_wx_account_ext(openid, session_key, guest)
            rs = auth_service.login_check_user(acc, False, 'WX')
            rs['uid'] = wxacc.id
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
