# -*- coding: utf-8 -*-
"""
Created by susy at 2019/10/17
"""
import logging
import os
import sys
env = os.getenv('env', None)
if not env and len(sys.argv) > 1:
    env = sys.argv[-1]
if not env:
    env = 'PROD'
TAG = env
print("TAG:", TAG)
redis_config = {
    # "host":"172.31.140.253",
    "host": "127.0.0.1",
    "port": 6379
}

mysql_worker_config = {
    # "host":"172.31.140.255",
    "host": "127.0.0.1",
    "port": 3306,
    "user": "worker",
    "password": "worker",
    "db": "panproxy"
}
if TAG == "dev":
    mysql_worker_config["host"] = "152.136.21.249"
service = {
    # "port": 443,
    "port": 8080,
}
JWT_SECRET_KEY = '\x0f\n\x88}4\xbf\xbb)2\xd9\xdd\x96"\x06t\xea\x8aG\x14S\xe1W\x85\xac\xfd,\x91\\ZmCe'
JWT_TOKEN_EXPIRATION_DAYS = 7
# Password generation
PASSWORD_SALT = 'soho0506'
PASSWORD_ALGORITHM = 'pbkdf2_sha256'

HASH_ID_MIN_LENGTH = 10
HASH_ID_SALT = 'hello, panclient'

MASTER_ACCOUNT_ID = 1

DEFAULT_CONTACT_QR_URI = '/static/img/contact/contact.jpeg'

WX_API = dict(appid='wx86242b978be4eb84',
              appsecret='687e701c47b40c027dac1de39af8fcba',
              token='20200622',
              aeskey='1JR32YSTAFShT1xs6ZqCKmWCZjQ7e3piDjsux1muzAD',
              point='https://api.weixin.qq.com'
              )

PAN_SERVICE = {
    "protocol": "https",
    "domain": "pan.baidu.com/rest/2.0/xpan",
    "agent": "pan.baidu.com",
    # "client_id": "aEsuEphvzdHYrcxtKnCgUXMl",
    "client_id": "wMAbjme3mQuGk1dtggTZvPPu",
    # "client_secret": "mf0GdhafvYWMS8PdUdBPGo7ENPdObUWI",
    "client_secret": "k0yydQlmLkKorwwhzqrmYGkL09za6Oyk",
    "access_token": "22.5903885244c6dae9b856d52a1d6bd374.315360000.1886082029.2717926781-9850001",
    "auth_domain": "openapi.baidu.com/oauth/2.0/",
    "auth_dns_domain": "openapi.baidu.com"
}
PAN_ROOT_DIR = {
    "name": "_SHAREDSYS",
    "alias": "分享盘"
}
CDN = dict(
    hosts=["http://static.oopsteam.site"]
)
RPC = dict(
    hosts=["http://api.oopsteam.site"]
)
ES = {
    "hosts": [{"host": "111.229.193.232", "port": 9200}],

    "share": {
        "index_name": "share",
        "doctype": "dataitem"
    },
    "local": {
        "index_name": "local",
        "doctype": "dataitem"
    },
    "test": {
        "index_name": "test",
        "doctype": "dataitem"
    }
}
if TAG == "dev":
    ES["hosts"] = [{"host": "127.0.0.1"}]

NEW_USER_DEFAULT = dict(org_id=5, role_id=1)

EPUB = dict(
    dir="/home/app/www/epub/"
)


def bd_auth_path(redirect_uri='oob', display='pad', skip_login=False):
    client_id = PAN_SERVICE['client_id']
    force_login = 1
    if skip_login:
        pan_auth = "authorize?response_type=code&client_id={}&redirect_uri={}&scope=basic,netdisk&display={}&" \
                   "qrcode=0".format(client_id, redirect_uri, display)
    else:
        pan_auth = "authorize?response_type=code&client_id={}&redirect_uri={}&scope=basic,netdisk&display={}&" \
                   "qrcode=0&force_login={}".format(client_id, redirect_uri, display, force_login)
    return pan_auth


def get_bd_auth_uri(redirect_uri='oob', display='pad'):
    auth_point = "{}://{}".format(PAN_SERVICE['protocol'], PAN_SERVICE['auth_domain'])
    pan_auth = "{}{}".format(auth_point, bd_auth_path(redirect_uri, display))
    return pan_auth
