# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/30
"""
from controller.base_service import BaseService
from dao.study_dao import StudyDao
from utils import singleton, CJsonEncoder, decrypt_id, constant, log
from utils.caches import cache_data, clear_cache
from controller.book.html_book_parser import HTMLBookParser
from cfg import EPUB
import json
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

    def translate_epub(self, chapter_path, py_chapter_path):
        if os.path.exists(chapter_path):
            parser = HTMLBookParser()
            with open(chapter_path, "r") as f:
                parser.feed(f.read())
            parser.close()
            if parser.data:
                if os.path.exists(py_chapter_path):
                    os.remove(py_chapter_path)
                with open(py_chapter_path, "w") as f:
                    f.write(json.dumps(parser.data, cls=CJsonEncoder))

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
        if not os.path.exists(py_dir):
            os.makedirs(py_dir)
        py_chapter_path = os.path.join(py_dir, chapter_file_name)
        if not os.path.exists(py_chapter_path):
            self.translate_epub(chapter_path, py_chapter_path)
        if os.path.exists(py_chapter_path):
            rs["p"] = os.path.join("py", chapter_file_name)

        return rs

    def shelf_book_list(self, wx_id, offset, size):
        return StudyDao.query_shelf_book_list(wx_id, offset, size)

    def sync_shelf_book_list(self, wx_id, book_list):
        rs = 0
        news_items = []
        update_items = []
        for bk in book_list:
            if "id" in bk:
                _id = decrypt_id(bk["id"])
                if not _id:
                    continue
            else:
                c = bk["code"]
                shel_book = StudyDao.query_shelf_book_by_code(wx_id, c)
                if shel_book:
                    update_items.append(bk)
                else:
                    news_items.append(bk)
        if update_items:
            StudyDao.update_shelf_books(update_items, wx_id)
        if news_items:
            cnt = StudyDao.query_shelf_book_count(wx_id)
            if cnt >= constant.SHELF["COUNT"]:
                return -1
            for nbk in news_items:
                nbk["wx_id"] = wx_id
                # log.debug("new shelf book:{}".format(nbk))
                StudyDao.new_book_shelf(nbk)

        return rs

    def remove_shelf_book(self, wx_id, book_shelf_code):
        StudyDao.del_shelf_books(wx_id, book_shelf_code)
        return 0


book_service = BookService()
