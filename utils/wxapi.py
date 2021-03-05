# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/26
"""
import requests
from cfg import WX_API, RPC
from utils import constant, url_encode, do_post_request
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
    host = RPC['hosts'][0]
    params = {'fs_id': fs_id}
    res = requests.get("{}{}".format(host, "/rpc/shared"), params=params, verify=False)
    if res.status_code == 200:
        return res.json()
    else:
        return {
            'state': -1, 'err': constant.SHARED_NOT_EXISTS_ERR
        }


def get_access_token(cfg):
    point = cfg["point"]
    fresh_access_token_api = "{point}/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}".format(
        point=point, appid=cfg["appid"], secret=cfg["appsecret"])
    res = requests.get(fresh_access_token_api, verify=False)

    rsjson = res.json()
    return rsjson


def getkflist(access_token):
    point = WX_API["point"]
    getkflist_api = "{point}/cgi-bin/customservice/getkflist?access_token={token}".format(point=point,
                                                                                          token=access_token)
    res = requests.get(getkflist_api, verify=False)
    rsjson = res.json()
    return rsjson


def gen_mini_qrcode(access_token, page_path, fuzzy_id, width=280):
    params = dict(
        page=page_path,
        scene="tag={}".format(fuzzy_id),
        width=width
    )
    headers = {"Content-Type": ""}
    print("gen_mini_qrcode params:{}".format(params))
    point = WX_API["point"]
    send_api = "{point}/wxa/getwxacodeunlimit?access_token={token}".format(point=point, token=access_token)
    print("send_api:{}".format(send_api))
    # res = requests.post(send_api, data=json.dumps(params), verify=False)
    # res = requests.post(send_api, json=params, headers=headers, verify=False)
    res = do_post_request(send_api, data=json.dumps(params), headers=headers)
    try:
        rs = res.json()
        print("gen_mini_qrcode failed:{}".format(rs))
    except Exception:
        return res.content
    return None

def wrap_qrcode_url(qrcode):
    return "https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket={}".format(qrcode)


def gen_qrcode(access_token, action_name, fuzzy_id, expire_seconds=2592000):
    params = dict(
        action_name=action_name,
        action_info={}
    )
    if action_name in ['QR_SCENE', 'QR_STR_SCENE']:
        params['expire_seconds'] = expire_seconds
    if action_name in ['QR_LIMIT_STR_SCENE', 'QR_STR_SCENE']:
        params['action_info']['scene'] = dict(scene_str=fuzzy_id)
    else:
        params['action_info']['scene'] = dict(scene_id=fuzzy_id)

    point = WX_API["point"]
    send_api = "{point}/cgi-bin/qrcode/create?access_token={token}".format(point=point, token=access_token)
    res = requests.post(send_api, json=params)
    rsjson = res.json()
    ticket = rsjson.get("ticket", None)
    if ticket:
        return dict(ticket=ticket, expire_seconds=rsjson.get('expire_seconds', expire_seconds))
    return {}
