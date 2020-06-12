# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/26
"""
import requests
from cfg import WX_API, RPC
from utils import constant
import json


def get_openid(code):
    point = WX_API["point"]
    appid = WX_API['appid']
    appsecret = WX_API['appsecret']
    grant_type = "authorization_code"
    openid_api = "{point}/sns/jscode2session?appid={appid}&secret={secret}&js_code={code}&grant_type={gtype}".format(
        point=point, appid=appid, secret=appsecret, code=code, gtype=grant_type)
    res = requests.get(openid_api, verify=False)
    rsjson = res.json()
    return rsjson


def rpc_shared(fs_id):
    host = RPC['hosts']
    params = {'fs_id': fs_id}
    res = requests.get("{}{}".format(host, "/rpc/shared"), params=params, verify=False)
    if res.status_code:
        return res.json()
    else:
        return {
            'state': -1, 'err': constant.SHARED_NOT_EXISTS_ERR
        }
