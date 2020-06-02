# -*- coding: utf-8 -*-
"""
Created by susy at 2019/10/18
"""
import os
import json
import arrow
import pytz
import logging
import logging.config
from datetime import datetime, date
from hashids import Hashids
import jwt
import random
from urllib.parse import quote, unquote
from cfg import HASH_ID_MIN_LENGTH, HASH_ID_SALT, JWT_SECRET_KEY

default_tz = pytz.timezone('Asia/Chongqing')


def scale_size(get_size):
    if not get_size:
        return ""
    rs = "{}B".format(get_size)

    _size = float(get_size)
    if _size > 1024:
        _size = _size / 1024
    else:
        rs = "{:.0f}B".format(_size)
        return rs

    if _size > 1024:
        _size = _size / 1024
    else:
        rs = "{:.2f}K".format(_size)
        return rs

    if _size > 1024:
        _size = _size / 1024
    else:
        rs = "{:.2f}M".format(_size)
        return rs

    if _size > 1024:
        _size = _size / 1024
    else:
        rs = "{:.2f}G".format(_size)
        return rs

    if _size > 1024:
        _size = _size / 1024
    else:
        rs = "{:.2f}T".format(_size)

    return rs


def url_encode(s):
    return quote(s)


def url_decode(s):
    return unquote(s)


def object_to_dict(instance, fields=[], excludes=[]):
    info = {}

    if not instance:
        return info

    for fn in fields:
        if excludes and fn in excludes:
            continue
        if hasattr(instance, fn):
            info[fn] = getattr(instance, fn)

    return info


def split_filename(filename):
    if not filename:
        return '', ''
    name = filename
    suffix = ''
    __idx = filename.rfind(".")
    if __idx > 0:
        name = filename[0:__idx]
        suffix = filename[__idx+1:]

    return name, suffix

def compare_dt(dt1, dt2) -> int:
    arrow_dt1 = arrow.get(dt1).replace(tzinfo=default_tz)
    arrow_dt2 = arrow.get(dt2).replace(tzinfo=default_tz)
    return (arrow_dt1 - arrow_dt2).total_seconds()


def compare_dt_by_now(dt1) -> int:
    return compare_dt(dt1, datetime.now(default_tz))


def make_token(acc_id):

    login_token = jwt.encode(dict(id=acc_id, tm=get_now_ts()), JWT_SECRET_KEY).decode("utf-8")
    return login_token


def make_account_token(payload: dict):
    if 'tm' not in payload:
        payload['tm'] = get_now_ts()
    login_token = jwt.encode(payload, JWT_SECRET_KEY, json_encoder=CJsonEncoder).decode("utf-8")
    return login_token


def get_payload_from_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY)
        return payload
    except ValueError as e:
        raise e


def get_now_ts():
    timestamp = arrow.utcnow().timestamp
    return timestamp


def get_now_datetime(offset=0):
    arrow_now = arrow.now(default_tz)
    if offset:
        arrow_now = arrow_now.shift(seconds=offset)
    return arrow_now.datetime


def get_now_datetime_format(fmt="YYYY-MM-DD HH:mm:ssZZ"):
    return arrow.now(default_tz).format(fmt=fmt)


def singleton(cls, *args, **kw):
    instances = {}

    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]
    return _singleton


hashider = Hashids(min_length=HASH_ID_MIN_LENGTH, salt=HASH_ID_SALT)


def obfuscate_id(raw_id):
    return hashider.encrypt(raw_id)


def decrypt_id(fuzzy_id, is_raise_error=True):
    val = hashider.decrypt(fuzzy_id)
    if val and len(val) > 0:
        return val[0]
    else:
        if is_raise_error:
            raise TypeError("fuzzy id is incorrect!")
        return ''


def decrypt_user_id(fuzzy_user_id, is_raise_error=True):
    return decrypt_id(fuzzy_user_id, is_raise_error)


def random_password(bit_count=4):
    dig = list('0123456789')
    alp = list('abcdefghijklmnopqrstuvwxyz')
    k = int(random.random() * (bit_count-1)) + 1
    pre = random.choices(dig, k=k)
    j = bit_count - k
    suf = random.choices(alp, k=j)
    v_list = pre + suf
    password_list = random.sample(v_list, k=bit_count)
    # print("password_list:", password_list)
    return "".join(password_list)


__DOC_EXT_NAMES = ['.pdf', '.as', '.c', '.htm', '.html', '.xml', '.cpp', '.cs', '.sql', '.xls', '.h', '.php', '.text',
                   '.txt', '.md', '.log', '.htaccess', '.js', '.css']
__IMAGE_EXT_NAMES = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
__VIDEO_EXT_NAMES = ['.mp4', '.flv', '.ts', '.avi', '.mkv', '.mov']
__EXT_NAMES = ['.pdf', '.as', '.c', '.iso', '.htm', '.html', '.xml', '.xsl', '.cf', '.cpp', '.cs', '.sql', '.xls',
               'xlsx', '.h', '.crt', '.pem', '.cer', '.php', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ppt', '.pptx',
               '.rb', '.text', '.txt', '.md', '.log', '.htaccess', '.doc', '.docx', '.zip', '.gz', '.tar', '.rar',
               '.js', '.css', '.fla', '.mp3', '.srt', '.dmg', '.apk', '.swf'] + __VIDEO_EXT_NAMES


def is_plain_media(file_name):
    _file_name = file_name.lower()
    for suffix in __DOC_EXT_NAMES:
        if _file_name.endswith(suffix):
            return True
    return False


def is_video_media(file_name):
    _file_name = file_name.lower()
    for suffix in __VIDEO_EXT_NAMES:
        if _file_name.endswith(suffix):
            return True
    return False


def is_image_media(file_name):
    _file_name = file_name.lower()
    for suffix in __IMAGE_EXT_NAMES:
        if _file_name.endswith(suffix):
            return True
    return False


def guess_file_type(file_name):
    _file_name = file_name.lower()
    for suffix in __EXT_NAMES:
        if _file_name.endswith(suffix):
            return suffix[1:]
    return ''


class CJsonEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        else:
            return json.JSONEncoder.default(self, obj)


standard_format = '%(asctime)s %(levelname)s [%(threadName)s:%(thread)d][%(filename)s:%(lineno)d]' \
                  '----> %(message)s'


def __log_cfg(log_file_name):
    if not os.path.exists("./logs"):
        os.mkdir("./logs")
    return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'json': {
                    'format': '%(asctime)s %(message)s',
                },
                'text': {
                    'format': standard_format,
                }
            },
            'handlers': {
                'json': {
                    'class': 'logging.handlers.TimedRotatingFileHandler',
                    'formatter': 'json',
                    'filename': "./logs/%s.json" % log_file_name,
                    'backupCount': 7,
                    'when': 'midnight'
                },
                'text': {
                    'level': logging.INFO,
                    'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件
                    'formatter': 'text',  # 标准
                    'filename': "./logs/%s.log" % log_file_name,  # 日志文件
                    'maxBytes': 10000000,  # 日志大小 10M
                    'backupCount': 5,  # 轮转文件数
                    'encoding': 'utf-8',  # 日志文件的编码，再也不用担心中文log乱码了
                }
            },
            'loggers': {
                'pan': {
                    'handlers': ['text'],
                    'level': logging.DEBUG
                },

            }
        }


__log_dict_cfg = __log_cfg("pansite")
logging.config.dictConfig(__log_dict_cfg)
log = logging.getLogger("pan")
