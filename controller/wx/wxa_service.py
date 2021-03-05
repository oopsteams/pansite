# -*- coding: utf-8 -*-
"""
Created by susy at 2021/3/5
"""
from controller.base_service import BaseService
from controller.async_service import async_service
from controller.wx.access_token_service import access_token_service
from dao.wxacode_dao import WxaDao, WxaGenCode
from utils import singleton, obfuscate_id, caches, constant, wxapi, get_now_ts, decrypt_id
import time
import traceback

INIT_QR_CODE_COUNT = 4
DEFAULT_WXA_PAGE_PATH = "pages/hello/hello"


@singleton
class WxaService(BaseService):

    def gen_min_qrcode(self):
        pass

    def checkin(self, fuzzy_id, tk):
        wgc_id = decrypt_id(fuzzy_id)
        WxaDao.update_pin(3, wgc_id, 2)
        caches._put_to_cache(fuzzy_id, tk, 300)

    def checkout(self, fuzzy_id):
        wgc_id = decrypt_id(fuzzy_id)
        tk = caches.get_from_cache(fuzzy_id)
        caches.clear_cache(fuzzy_id)
        return tk

    def fetch_unused_qrcode(self, ctx):
        wgc: WxaGenCode = WxaDao.fetch_one_wxa_code(1)
        if wgc:
            rs = WxaDao.update_pin(2, wgc.id, 1)
            print("fetch ok? rs:", rs)
            return obfuscate_id(wgc.id)
        else:
            async_rs = self.async_gen_qrcode(ctx)
            print("async_gen_qrcode state:", async_rs)
        return None

    def async_gen_qrcode(self, ctx):

        def final_do():
            pass

        def to_do(key, result_key):
            _result = {'state': 0, 'done': 0}
            n = WxaDao.query_wxa_count(1)  # qrcode unused count
            if n > INIT_QR_CODE_COUNT / 2:
                return _result
            need_gen_count = INIT_QR_CODE_COUNT - n
            rs = access_token_service.refresh_access_token()
            if not rs:
                return _result
            access_token = rs['access_token']
            for i in range(0, need_gen_count):
                try:
                    new_id = WxaDao.new_wxa_record()
                    fuzzy_id = obfuscate_id(new_id)
                    print("to gen code,fuzzy_id:{}".format(fuzzy_id))
                    bf = wxapi.gen_mini_qrcode(access_token, DEFAULT_WXA_PAGE_PATH, fuzzy_id)

                    if bf:

                        import os
                        base_dir = ctx["basepath"]
                        dest_dir = os.path.join(base_dir, "static/mqr/")
                        dest_file = os.path.join(dest_dir, "{}.png".format(fuzzy_id))
                        print("to gen code success,will write to file:{}".format(dest_file))
                        with open(dest_file, 'wb') as up:
                            up.write(bf)
                        WxaDao.update_pin(1, new_id, 0)
                    else:
                        # del wgc
                        return _result
                        pass
                except Exception:
                    traceback.print_exc()
                    # log.error("gen code err.", exc_info=True)
                    pass
                time.sleep(0.5)

            return _result
        key_prefix = "wxa:ready:"
        suffix = "qrcode"
        async_service.init_state(key_prefix, suffix, {"state": 0, "pos": 0})
        async_rs = async_service.async_checkout_thread_todo(key_prefix, suffix, to_do, final_do)
        return async_rs


wxa_service = WxaService()
