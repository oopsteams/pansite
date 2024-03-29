# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/26
"""
import requests
from cfg import WX_API
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
