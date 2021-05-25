# -*- coding: utf-8 -*-
"""
Created by susy at 2021/5/25
"""
import requests
from utils import constant
from cfg import ALI_REDIRECT


def ali_rpc_cb(params):
    uri = ALI_REDIRECT["hosts"][0]

    res = requests.get("{}".format(uri), params=params, verify=False)
    if res.status_code == 200:
        return res.json()
    else:
        return {
            'state': -1, 'err': constant.SHARED_NOT_EXISTS_ERR
        }