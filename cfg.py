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

PAN_SERVICE = {
    "protocol": "https",
    "domain": "pan.baidu.com/rest/2.0/xpan",
    "agent": "pan.baidu.com",
    # "client_id": "aEsuEphvzdHYrcxtKnCgUXMl",
    "client_id": "wMAbjme3mQuGk1dtggTZvPPu",
    # "client_secret": "mf0GdhafvYWMS8PdUdBPGo7ENPdObUWI",
    "client_secret": "k0yydQlmLkKorwwhzqrmYGkL09za6Oyk",
    "access_token": "22.5903885244c6dae9b856d52a1d6bd374.315360000.1886082029.2717926781-9850001",
    "auth_domain": "openapi.baidu.com/oauth/2.0/"
}

ES = {
    "hosts": [{"host": "127.0.0.1"}],

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


def get_bd_auth_uri(redirect_uri='oob'):
    auth_point = "{}://{}".format(PAN_SERVICE['protocol'], PAN_SERVICE['auth_domain'])
    client_id = PAN_SERVICE['client_id']
    force_login = 1
    pan_auth = "{}authorize?response_type=code&client_id={}&redirect_uri={}&scope=basic,netdisk&display=tv&" \
               "qrcode=0&force_login={}".format(auth_point, client_id, redirect_uri, force_login)
    return pan_auth
