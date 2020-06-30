# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/30
"""
from controller.base_service import BaseService
from controller.auth_service import auth_service
from dao.models import PaymentAccount, CreditRecord, AccountWxExt
from dao.study_dao import StudyDao
from dao.wx_dao import WxDao
from utils import scale_size, compare_dt, decrypt_id, singleton, get_today_zero_datetime, get_now_datetime, constant, get_now_ts
from utils.caches import cache_data, clear_cache
PAY_SIGNED_CACHE_TIMEOUT = 24 * 60 * 60


def clear_signed_state_cache(ref_id):
    key = "pay_signed_{}".format(ref_id)
    print("clear_signed_state_cache key:", key)
    clear_cache(key)


def clear_balance_cache(account_id):
    key = "pay_balance_{}".format(account_id)
    print("clear_balance_cache key:", key)
    clear_cache(key)


@singleton
class BookService(BaseService):

    def clear_cache(self, account_id, ref_id):
        clear_balance_cache(account_id)
        clear_signed_state_cache(ref_id)

    def list(self, guest, offset, size):
        return StudyDao.query_study_book_list(1, offset, size)

    def get_book(self, code):
        return StudyDao.check_out_study_book(code)


book_service = BookService()

