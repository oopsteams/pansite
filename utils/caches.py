# -*- coding: utf-8 -*-
"""
Created by susy at 2020/1/7
"""
from utils import singleton, log, get_now_ts
from functools import wraps


@singleton
class CacheService:
    SYNC_PAN_DIR_CACHES = {}

    def __init__(self):
        pass

    def put_on_not_exists(self, key, val):
        if key in self.SYNC_PAN_DIR_CACHES:
            return False
        else:
            self.SYNC_PAN_DIR_CACHES[key] = val
            return True

    def put(self, key, val):
        if key in self.SYNC_PAN_DIR_CACHES:
            _val = self.SYNC_PAN_DIR_CACHES[key]
            if type(val) is dict and type(_val) is dict:
                for k in val:
                    _val[k] = val[k]
            return False
        else:
            self.SYNC_PAN_DIR_CACHES[key] = val
            return True

    def replace(self, key, val):
        self.SYNC_PAN_DIR_CACHES[key] = val

    def rm(self, key):
        if key in self.SYNC_PAN_DIR_CACHES:
            return self.SYNC_PAN_DIR_CACHES.pop(key)
        return None

    def get(self, key):
        if key in self.SYNC_PAN_DIR_CACHES:
            return self.SYNC_PAN_DIR_CACHES[key]
        return None


cache_service = CacheService()
DATA_CACHES_TIMEOUT_KEYS_INDEX = []
LAST_CLEAR_CACHE_CONST = dict(tm=get_now_ts(), timeout=3600)
DATA_CACHES = {}


def _clear_cache():
    if get_now_ts() - LAST_CLEAR_CACHE_CONST['tm'] > LAST_CLEAR_CACHE_CONST['timeout']:
        _l = len(DATA_CACHES_TIMEOUT_KEYS_INDEX)
        idx = 0
        find_target = False
        for idx in range(_l, 0, -1):
            data_obj = DATA_CACHES_TIMEOUT_KEYS_INDEX[idx-1]
            tm = data_obj.get('tm', 0)
            time_out = data_obj.get('to', 0)
            if time_out and get_now_ts() - tm > time_out:
                log.warn("find timeout idx:{}".format(idx))
                find_target = True
                break
        if find_target and idx > 0:
            log.warn("clear cache by idx:{}".format(idx))
            for i in range(idx, 0, -1):
                d = DATA_CACHES_TIMEOUT_KEYS_INDEX.pop(i-1)
                k = d['key']
                _get_from_cache(k)

        LAST_CLEAR_CACHE_CONST['tm'] = get_now_ts()


def clear_cache(key):
    idx = 0
    _l = len(DATA_CACHES_TIMEOUT_KEYS_INDEX)
    find_target = False
    for idx in range(_l, 0, -1):
        data_obj = DATA_CACHES_TIMEOUT_KEYS_INDEX[idx - 1]
        _key = data_obj.get('key', None)
        if _key and _key == key:
            log.debug("clear_cache find target keys_index:{}, index:{}".format(data_obj, idx-1))
            find_target = True
            break
    if find_target and idx > 0:
        log.warn("clear cache by find [{}][index:{}], will remove it!".format(key, idx-1))
        keys_index = DATA_CACHES_TIMEOUT_KEYS_INDEX.pop(idx - 1)
        log.debug("keys_index:{}".format(keys_index))
        DATA_CACHES.pop(key)
    if not find_target:
        if key in DATA_CACHES:
            log.warn("clear cache, timeout is 0, [{}][index:{}], will remove it!".format(key, idx - 1))
            DATA_CACHES.pop(key)


def _get_from_cache(key):
    data_obj = DATA_CACHES.get(key, None)
    if not data_obj:
        return None
    tm = data_obj.get('tm', 0)
    time_out = data_obj.get('to', 0)
    if time_out and get_now_ts() - tm > time_out:
        # DATA_CACHES.pop(key)
        clear_cache(key)
        return None
    else:
        log.info("_get_from_cache hit ok! [{}]".format(key))
        return data_obj.get('data', None)


def get_from_cache(key):
    return _get_from_cache(key)


def _put_to_cache(key, val, timeout_seconds=0):

    data_obj = {'data': val, 'tm': get_now_ts(), 'to': timeout_seconds, 'key': key}
    print("_put_to_cache key:", key)
    DATA_CACHES[key] = data_obj
    if timeout_seconds > 0:
        DATA_CACHES_TIMEOUT_KEYS_INDEX.append(data_obj)
        DATA_CACHES_TIMEOUT_KEYS_INDEX.sort(key=lambda el: el['tm'] + el['to'])

    _clear_cache()


def cache_data(cache_key, timeout_seconds=None, verify_key=None):

    def cache_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if isinstance(cache_key, str):
                key = cache_key.format(*args)
            elif callable(cache_key):
                key = cache_key(*args, **kwargs)
            else:
                key = cache_key

            data = _get_from_cache(key)
            if data:
                if verify_key:
                    if type(data) is dict and verify_key in data:
                        return data
                    elif type(data) is object and hasattr(data, verify_key):
                        return data
                else:
                    return data

            result = func(*args, **kwargs)
            if not result:
                return result
            if callable(timeout_seconds):
                to = timeout_seconds(*args, result)
            elif isinstance(timeout_seconds, str):
                to = int(timeout_seconds)
            elif timeout_seconds:
                to = timeout_seconds
            else:
                to = 0
            _put_to_cache(key, result, to)
            return result
        return wrapper
    return cache_decorator
