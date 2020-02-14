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

    def put(self, key, val):
        if key in self.SYNC_PAN_DIR_CACHES:
            return False
        else:
            self.SYNC_PAN_DIR_CACHES[key] = val
            return True

    def rm(self, key):
        if key in self.SYNC_PAN_DIR_CACHES:
            return self.SYNC_PAN_DIR_CACHES.pop(key)
        return None


cache_service = CacheService()

LAST_CLEAR_CACHE_CONST = dict(tm=get_now_ts(), timeout=3600)
DATA_CACHES = {}


def _clear_cache():
    if get_now_ts() - LAST_CLEAR_CACHE_CONST['tm'] > LAST_CLEAR_CACHE_CONST['timeout']:
        all_keys = [k for k in DATA_CACHES]
        for key in all_keys:
            _get_from_cache(key)

        LAST_CLEAR_CACHE_CONST['tm'] = get_now_ts()


def _get_from_cache(key):
    data_obj = DATA_CACHES.get(key, None)
    if not data_obj:
        return None
    tm = data_obj.get('tm', 0)
    time_out = data_obj.get('to', 0)
    if time_out and get_now_ts() - tm > time_out:
        DATA_CACHES.pop(key)
        return None
    else:
        return data_obj.get('data', None)


def _put_to_cache(key, val, timeout_seconds=0):
    data_obj = {'data': val, 'tm': get_now_ts(), 'to': timeout_seconds}
    DATA_CACHES[key] = data_obj
    _clear_cache()


def cache_data(cache_key, timeout_seconds=0, verify_dict_key=None, verify_object_attr=None):
    def cache_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if isinstance(cache_key, str):
                key = cache_key % locals()
            elif callable(cache_key):
                key = cache_key(*args, **kwargs)
            else:
                key = cache_key

            data = _get_from_cache(key)
            if data:
                if not verify_dict_key and not verify_object_attr:
                    return data
                if verify_dict_key and verify_dict_key in data:
                    return data
                if verify_object_attr and hasattr(data, verify_object_attr):
                    return data

            result = func(*args, **kwargs)
            if not result:
                return result
            _put_to_cache(key, result, timeout_seconds)
            return result
        return wrapper
    return cache_decorator
