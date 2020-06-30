# -*- coding: utf-8 -*-
"""
Created by susy at 2020/3/16
"""
from controller.base_service import BaseService
from utils.caches import cache_service, get_from_cache
from utils import singleton, get_now_ts, log as logger
from typing import Callable, Tuple
from threading import Thread
from dao.models import try_release_conn

THREAD_LIMIT_PARAMS = {
    "max": 100,
    "actived": 0
}


@singleton
class AsyncService(BaseService):

    def __init__(self):
        super().__init__()

    def __build_thread(self, __run: Callable):
        if THREAD_LIMIT_PARAMS['actived'] < THREAD_LIMIT_PARAMS['max']:
            THREAD_LIMIT_PARAMS['actived'] = THREAD_LIMIT_PARAMS['actived'] + 1
            return Thread(target=__run)

    def release_thread(self):
        if THREAD_LIMIT_PARAMS['actived'] > 0:
            THREAD_LIMIT_PARAMS['actived'] = THREAD_LIMIT_PARAMS['actived'] - 1

    def async_checkout_thread_todo(self, prefix, suffix, action: Callable[..., dict]=None, final_call: Callable=None):
        ctx = self
        key = "async:%s:%s" % (prefix, suffix)
        rs_key = "async:%s:rs:%s:" % (prefix, suffix)

        def __run():
            logger.info("thread to run in.")
            # cache_service.rm(rs_key)
            rs = {}
            if action:
                try:
                    rs = action(key, rs_key)
                except Exception:
                    logger.error("exe action failed.", exc_info=True)
                    pass
            self.__thread = None
            cache_service.rm(key)
            rs['end'] = 1
            # cache_service.put(rs_key, rs)
            self.update_state(prefix, suffix, rs)
            if final_call:
                try:
                    final_call()
                except Exception:
                    pass
            try_release_conn()

            ctx.release_thread()
            pass
        __thread = self.__build_thread(__run)
        if __thread:
            not_exists = cache_service.put_on_not_exists(key, get_now_ts())
            if not_exists:
                __thread.start()
            else:
                return {"state": "block"}
        else:
            return {"state": "block"}
        return {"state": "run"}

    def init_state(self, prefix, suffix, val):
        rs_key = "async:%s:rs:%s:" % (prefix, suffix)
        # print('async update state:', val)
        cache_service.replace(rs_key, val)

    def update_state(self, prefix, suffix, val):
        rs_key = "async:%s:rs:%s:" % (prefix, suffix)
        # print('async update state:', val)
        cache_service.put(rs_key, val)

    def checkout_key_state(self, prefix, suffix):
        rs_key = "async:%s:rs:%s:" % (prefix, suffix)
        val = cache_service.get(rs_key)
        # if 'end' in val and val['end'] == 1:
        #     cache_service.rm(rs_key)
        return val


async_service = AsyncService()
