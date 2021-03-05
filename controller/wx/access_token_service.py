# -*- coding: utf-8 -*-
"""
Created by susy at 2021/3/5
"""
from controller.base_service import BaseService
from dao.wxacode_dao import WxaDao, WxaAccessToken
from utils import singleton, obfuscate_id, caches, constant, wxapi, get_now_ts
from cfg import WX_API, RPC


@singleton
class AccessTokenService(BaseService):

    def fetch_cfg(self, platform):
        cfg = None
        if "wxa" == platform:
            cfg = WX_API
        return cfg

    def refresh_access_token(self, params=None):
        platform = "wxa"
        if params:
            platform = params.get("p", "wxa")
        wat_dict = None
        if "wxa" == platform:
            cfg = self.fetch_cfg(platform)
            _appid = cfg['appid']
            # lock_key = "lock:refresh:access:{}:token:{}".format(_appid, "wx")
            key = "wxa:access_token:{}".format(_appid)
            wat_dict = caches.get_from_cache(key)
            if not wat_dict:
                wat = WxaDao.fetch_one_access_token(_appid)
                wat_dict = WxaAccessToken.to_dict(wat)
                print("fetch_one_access_token wat_dict:", wat_dict)
            if not wat_dict:
                try:
                    return None
                    jsonrs = wxapi.get_access_token(cfg)
                    if "access_token" in jsonrs:
                        access_token = jsonrs["access_token"]
                        expires_in = jsonrs["expires_in"]
                        expires_at = expires_in - 60 + get_now_ts()
                        wat = WxaDao.new_wxa_access_token(_appid, access_token, expires_in, expires_at)
                        wat_dict = WxaAccessToken.to_dict(wat)
                        caches._put_to_cache(key, wat_dict)
                except Exception:
                    pass
            else:
                now_tm = get_now_ts()
                expires_at = wat_dict['expires_at']
                if expires_at < now_tm:
                    try:
                        jsonrs = wxapi.get_access_token(cfg)
                        if "access_token" in jsonrs:
                            access_token = jsonrs["access_token"]
                            expires_in = jsonrs["expires_in"]
                            expires_at = expires_in - 60 + get_now_ts()
                            wat_dict['expires_in'] = expires_in
                            wat_dict['expires_at'] = expires_at
                            wat_dict['access_token'] = access_token
                            WxaDao.update_access_token(access_token, expires_in, expires_at, wat_dict['id'])
                    except Exception:
                        pass

        return wat_dict


access_token_service = AccessTokenService()
