# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/30
"""
from controller.base_service import BaseService
from dao.study_dao import StudyDao
from dao.es_dao import es_dao_book
from utils import singleton, CJsonEncoder, decrypt_id, constant, log as logger, constant
from utils.utils_es import SearchParams, build_query_item_es_body, build_es_book_json_body
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

    def __to_sarch(self, offset, size, es_body):
        es_dao_fun = es_dao_book
        es_result = es_dao_fun().es_search_exec(es_body)
        total = 0
        # datas = [_s["_source"] for _s in hits_rs["hits"]]
        datas = []
        if es_result:
            # logger.info("book es_result:{}".format(es_result))
            hits_rs = es_result["hits"]
            total = hits_rs["total"]["value"]
            for _s in hits_rs["hits"]:
                highlight = {}
                if "highlight" in _s:
                    highlight = _s["highlight"]
                raw = _s["_source"]
                raw["highlight"] = highlight
                raw["code"] = raw["id"]
                item = raw
                item.pop("tags")
                item.pop("@ts")
                item.pop("@is_removed")
                item.pop("ref_id")
                datas.append(item)
        print('__to_sarch es_result:', es_result)
        has_next = offset + size < total
        rs = {"data": datas, "has_next": has_next, "total": total, "pagesize": size}
        return rs

    def search_in_pack(self, pack_id, page, size=50):
        offset = int(page) * size
        if offset > constant.MAX_RESULT_WINDOW - size:
            offset = constant.MAX_RESULT_WINDOW - size
        sp: SearchParams = SearchParams.build_params(offset, size)
        sp.add_must(False, field="pack_id", value=pack_id)
        sp.add_must(False, field="pin", value=1)
        _sort_fields = [{"idx": {"order": "asc"}}]
        es_body = build_query_item_es_body(sp, sort_fields=_sort_fields)
        logger.info("es_body:{}".format(es_body).replace("'", '"'))

        rs = self.__to_sarch(offset, size, es_body)

        return rs

    def essay(self, mtag, page, size=20):
        kw = None

        offset = int(page) * size
        datas = StudyDao.query_study_essay_list(mtag, 1, offset, size)
        total = StudyDao.query_study_essay_count(mtag, 1)
        has_next = offset + len(datas) < total
        rs = {"data": datas, "has_next": has_next, "total": total, "pagesize": size}
        return rs

    def search_hz(self, kw):
        datas = []
        if kw:
            datas = StudyDao.query_study_essay_by_hz(kw)
        rs = {"data": datas, "has_next": False, "total": 1, "pagesize": 20}
        return rs

    def essayclazz(self, fuzzy_id, page, size=20, total=0):
        kw = None
        essay_id = decrypt_id(fuzzy_id)
        offset = int(page) * size
        essay_dict = StudyDao.query_study_essay(essay_id)
        hz_list = StudyDao.query_study_essay_hz_list(essay_id, offset, size)
        if not total:
            total = StudyDao.query_study_essay_hz_count(essay_id)
        has_next = offset + len(hz_list) < total
        rs = {"data": hz_list, "essay": essay_dict, "has_next": has_next, "total": total, "pagesize": size}
        return rs

    def essayinfo(self, fuzzy_id):
        essay_id = decrypt_id(fuzzy_id)
        essay_dict = StudyDao.query_study_essay(essay_id)
        total = StudyDao.query_study_essay_hz_count(essay_id)
        rs = {"essay": essay_dict, "total": total}
        return rs

    def search(self, mtag, tag, keyword, page, size=50):
        kw = None
        if keyword:
            l_kw = keyword.lower()
            pos = 0
            idx = l_kw.find("or", pos)
            _kw_secs = []
            while idx >= pos:
                s = keyword[pos:idx]
                _s = s.strip()
                _s_arr = _s.split(' ')
                _arr = [a for a in _s_arr if len(a) > 0]
                _s = " AND ".join(_arr)
                _kw_secs.append(_s)
                pos = idx + 2
                idx = l_kw.find("or", pos)
            if pos < len(l_kw):
                s = keyword[pos:]
                _s = s.strip()
                _s_arr = _s.split(' ')
                _arr = [a for a in _s_arr if len(a) > 0]
                _s = " AND ".join(_arr)
                _kw_secs.append(_s)
            # print("_kw_secs:", _kw_secs)
            if _kw_secs:
                new_keyword = " OR ".join(_kw_secs)
            else:
                new_keyword = keyword
            kw = new_keyword
        # print("kw:", kw)
        # size = 50
        offset = int(page) * size
        if offset > constant.MAX_RESULT_WINDOW - size:
            offset = constant.MAX_RESULT_WINDOW - size
        sp: SearchParams = SearchParams.build_params(offset, size)
        es_dao_fun = es_dao_book
        if kw:
            # sp.add_must(value=kw)
            # sp.add_must(False, field='query_string', value="\"%s\"" % kw)
            _kw_val = "%s" % kw
            sp.add_should(True, field='name', value=_kw_val)
            sp.add_should(True, field='authors', value=_kw_val)
            sp.add_should(True, field='publisher', value=_kw_val)
        if mtag:
            idx = mtag.rfind(",")
            if idx > 0:
                tag_query = mtag.replace(",", " OR ")
                sp.add_must(False, field='tags', value=tag_query, is_query=True)
            else:
                sp.add_must(True, field='tags', value="%s" % mtag)
        if tag:
            idx = tag.rfind(",")
            if idx > 0:
                tag_query = tag.replace(",", " OR ")
                sp.add_must(False, field='tags', value=tag_query, is_query=True)
            else:
                sp.add_must(True, field='tags', value="%s" % tag)
        sp.add_must(False, field="pack_id", value=0)
        sp.add_must(False, field="pin", value=1)
            # tags = tag.split(",")
            # for t in tags:
            # sp.add_must(False, field='query_string', value="\"%s\"" % tag)
            #     sp.add_must(True, field='tags', value="%s" % t, is_query=True)
        _sort_fields = None
        if not kw:
            _sort_fields = [{"created_at": {"order": "desc"}}]

        if kw:
            es_body = build_query_item_es_body(sp)
            # es_body["highlight"] = {
            #     "pre_tags": "<text class='key'>",
            #     "post_tags": "</text>",
            #     "fields": {"name": {}, "authors": {}, "publisher": {}}
            # }
            es_body["highlight"] = {
                "fields": {"name": {}, "authors": {}, "publisher": {}}
            }
        else:
            es_body = build_query_item_es_body(sp, sort_fields=_sort_fields)

        logger.info("es_body:{}".format(es_body).replace("'", '"'))

        rs = self.__to_sarch(offset, size, es_body)

        return rs

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
            chapter_file_name = chapter[idx + 1:]
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

    def put_off_book(self, book_shelf_code):
        rs = {"status": 0}
        updated = []
        from dao.models import StudyBook
        idx = book_shelf_code.find("|")
        if idx > 0:
            code_list = book_shelf_code.split("|")
            if code_list:
                sb_list = StudyDao.check_out_study_books(code_list)
                for sb in sb_list:
                    sb.pin = 0
                    StudyDao.update_books_by_id({"pin": sb.pin}, sb.id)
                    sb_dict = StudyBook.to_dict(sb, ["id"])
                    es_up_params = es_dao_book().filter_update_params(sb_dict)
                    if es_up_params:
                        logger.info("will update book es item es_up_params:{}".format(es_up_params))
                        es_dao_book().update_fields(sb.code, **es_up_params)
                    updated.append(sb_dict)
        else:
            sb: StudyBook = StudyDao.check_out_study_book(book_shelf_code)
            if sb:
                sb.pin = 0
                StudyDao.update_books_by_id({"pin": sb.pin}, sb.id)
                sb_dict = StudyBook.to_dict(sb, ["id"])
                es_up_params = es_dao_book().filter_update_params(sb_dict)
                if es_up_params:
                    logger.info("will update book es item es_up_params:{}".format(es_up_params))
                    es_dao_book().update_fields(sb.code, **es_up_params)
                updated.append(sb_dict)
                # return sb_dict
        if updated:
            rs['updated'] = updated
        return rs

    def put_on_book(self, book_shelf_code):
        rs = {"status": 0}
        updated = []
        from dao.models import StudyBook
        idx = book_shelf_code.find("|")
        if idx > 0:
            code_list = book_shelf_code.split("|")
            if code_list:
                sb_list = StudyDao.check_out_study_books(code_list)
                for sb in sb_list:
                    sb.pin = 1
                    StudyDao.update_books_by_id({"pin": sb.pin}, sb.id)
                    if not sb.pack_id:
                        sb.pack_id = 0
                    sb_dict = StudyBook.to_dict(sb, ["id"])
                    es_up_params = es_dao_book().filter_update_params(sb_dict)
                    if es_up_params:
                        logger.info("will update book es item es_up_params:{}".format(es_up_params))
                        es_dao_book().update_fields(sb.code, **es_up_params)
                    updated.append(sb_dict)
        else:
            sb: StudyBook = StudyDao.check_out_study_book(book_shelf_code)
            if sb:
                sb.pin = 1
                if not sb.pack_id:
                    sb.pack_id = 0
                StudyDao.update_books_by_id({"pin": sb.pin}, sb.id)
                sb_dict = StudyBook.to_dict(sb, ["id"])
                es_up_params = es_dao_book().filter_update_params(sb_dict)
                if es_up_params:
                    logger.info("will update book es item es_up_params:{}".format(es_up_params))
                    es_dao_book().update_fields(sb.code, **es_up_params)
                updated.append(sb_dict)
                # return sb_dict
        if updated:
            rs['updated'] = updated
        return rs


book_service = BookService()
