# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/30
"""
from controller.base_service import BaseService
from controller.auth_service import auth_service
from dao.models import PaymentAccount, CreditRecord, AccountWxExt
from dao.study_dao import StudyDao
from dao.wx_dao import WxDao
from utils import scale_size, compare_dt, decrypt_id, singleton, get_today_zero_datetime, get_now_datetime, constant, \
    get_now_ts
from utils.caches import cache_data, clear_cache
from controller.book.my_html_parser import MyHTMLParser
from cfg import EPUB
import os

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

    def translate_epub(self, chapter_path):
        if os.path.exists(chapter_path):
            parser = MyHTMLParser()
            with open(chapter_path, "r") as f:
                parser.feed(f.read())
            parser.close()
            print("parser.data", parser.data)
            print("parser.links", parser.links)

    def parse_py_epub(self, ctx, code, chapter):
        rs = {"state": 0}
        chapter_file_name = chapter
        idx = chapter.rfind("/")
        if len(chapter) > idx >= 0:
            chapter_file_name = chapter[idx+1:]
        base_dir = ctx["basepath"]
        if base_dir:
            dest_dir = os.path.join(base_dir, EPUB["dest"])
        else:
            dest_dir = EPUB["dest"]
        current_dest_dir = os.path.join(dest_dir, code)
        chapter_path = os.path.join(current_dest_dir, chapter)
        print("chapter_path: ", chapter_path)
        py_dir = os.path.join(current_dest_dir, "py")
        py_chapter_path = os.path.join(py_dir, chapter_file_name)
        if os.path.exists(py_chapter_path):
            rs["p"] = os.path.join("py", chapter_file_name)
        else:
            self.translate_epub(chapter_path)

        def final_do():
            pass

        return rs


book_service = BookService()
