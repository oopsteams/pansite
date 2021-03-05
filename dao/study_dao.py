# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/28
"""
from dao.models import db, query_wrap_db, StudyBook, BookShelf, StudyEssay, StudyHanzi, EssayHanzi
from peewee import fn, ModelSelect
from utils import obfuscate_id


class StudyDao(object):

    # query data
    @classmethod
    @query_wrap_db
    def query_study_book_list(cls, pin, offset=0, cnt=50) -> list:
        rs = []
        ms = StudyBook.select().where(StudyBook.pin == pin).order_by(StudyBook.idx.desc()).offset(offset).limit(cnt)
        for sb in ms:
            sb_dict = StudyBook.to_dict(sb, ['id'])
            idx = sb.name.rfind(".")
            if idx > 0:
                sb_dict["name"] = sb.name[:idx]
            rs.append(sb_dict)
        return rs

    @classmethod
    @query_wrap_db
    def query_study_essay(cls, essay_id):
        essay = StudyEssay.select().where(StudyEssay.id == essay_id).first()
        sb_dict = StudyEssay.to_dict(essay, ['id'])
        sb_dict["id"] = obfuscate_id(essay.id)
        return sb_dict

    @classmethod
    @query_wrap_db
    def query_study_essay_by_title(cls, title):
        essay = StudyEssay.select().where(StudyEssay.title == title).first()
        sb_dict = {}
        if essay:
            sb_dict = StudyEssay.to_dict(essay)
        # sb_dict["id"] = obfuscate_id(essay.id)
        return sb_dict

    @classmethod
    @query_wrap_db
    def query_study_essay_list(cls, tag, pin, offset=0, cnt=50) -> list:
        rs = []
        ms: ModelSelect = StudyEssay.select(StudyEssay, StudyHanzi).join(StudyHanzi, on=(StudyEssay.hanzi == StudyHanzi.id), attr="hz")
        if tag:
            ms = ms.where(StudyEssay.pin == pin, StudyEssay.tag == tag)
        else:
            ms = ms.where(StudyEssay.pin == pin)
        ms = ms.order_by(StudyEssay.tag.asc(), StudyEssay.term.asc(), StudyEssay.idx.asc()).offset(offset).limit(cnt)
        for sb in ms:
            sb_dict = StudyEssay.to_dict(sb, ['id', 'description'])
            sb_dict["id"] = obfuscate_id(sb.id)
            sb_dict["hz"] = StudyHanzi.to_dict(sb.hz, ["id"])
            rs.append(sb_dict)
        return rs

    @classmethod
    @query_wrap_db
    def query_study_essay_count(cls, tag, pin):
        model_rs: ModelSelect = StudyEssay.select(fn.count(StudyEssay.id).alias('count'))
        if tag:
            model_rs = model_rs.where(StudyEssay.pin == pin, StudyEssay.tag == tag)
        else:
            model_rs = model_rs.where(StudyEssay.pin == pin)

        if model_rs:
            model_dict = model_rs.dicts()
            if model_dict:
                v = model_dict[0].get('count')
                if v:
                    return v
        return 0

    @classmethod
    @query_wrap_db
    def query_study_essay_by_hz(cls, txt):
        rs = []

        ms = StudyHanzi.select(StudyHanzi, EssayHanzi, StudyEssay).join(EssayHanzi, on=(EssayHanzi.hz == StudyHanzi.id),
                                                            attr="eh").join(StudyEssay,
                                                                            on=(EssayHanzi.essay == StudyEssay.id),
                                                                            attr="e").where(StudyHanzi.txt == txt)
        # print("query_study_essay_by_hz ms:{}".format(ms))
        for o in ms:
            sh_dict = StudyHanzi.to_dict(o, ["id"])
            essay = StudyEssay.to_dict(o.eh.e, ["id"])
            essay["id"] = obfuscate_id(o.eh.e.id)
            essay["hz"] = sh_dict
            rs.append(essay)
        return rs

    @classmethod
    @query_wrap_db
    def query_study_essay_hz_list(cls, essay_id, offset=0, cnt=50):
        rs = []
        ms = EssayHanzi.select(EssayHanzi, StudyHanzi).join(StudyHanzi, on=(EssayHanzi.hz == StudyHanzi.id),
                                                            attr="hanzi").where(EssayHanzi.essay == essay_id).order_by(
            StudyHanzi.idx.asc()).offset(offset).limit(cnt)
        for eh in ms:
            sb_dict = StudyHanzi.to_dict(eh.hanzi, ["id"])
            rs.append(sb_dict)
        return rs

    @classmethod
    @query_wrap_db
    def query_study_essay_hz_count(cls, essay_id):
        model_rs: ModelSelect = EssayHanzi.select(fn.count(EssayHanzi.hz).alias('count')).where(EssayHanzi.essay == essay_id)

        if model_rs:
            model_dict = model_rs.dicts()
            if model_dict:
                v = model_dict[0].get('count')
                if v:
                    return v
        return 0

    @classmethod
    @query_wrap_db
    def query_shelf_book_list(cls, wx_id, offset=0, cnt=50) -> list:
        rs = []
        ms = BookShelf.select(BookShelf, StudyBook).join(StudyBook, on=(StudyBook.code == BookShelf.code), attr="book").where(BookShelf.wx_id == wx_id).order_by(BookShelf.lastopen.desc()).offset(offset).limit(cnt)
        for bs in ms:
            sb_dict = BookShelf.to_dict(bs, ['id', 'wx_id'])
            sb_dict["id"] = obfuscate_id(bs.id)
            sb_dict["bk"] = StudyBook.to_dict(bs.book, ["id", "account_id", "ref_id"])
            rs.append(sb_dict)
        return rs

    @classmethod
    @query_wrap_db
    def query_shelf_book_by_code(cls, wx_id, code) -> BookShelf:
        ms = BookShelf.select(BookShelf).where(BookShelf.wx_id == wx_id, BookShelf.code == code).limit(1)
        if ms:
            return ms[0]
        return None

    @classmethod
    @query_wrap_db
    def query_shelf_book_count(cls, wx_id):
        model_rs: ModelSelect = BookShelf.select(fn.count(BookShelf.id).alias('count')).where(BookShelf.wx_id == wx_id)

        if model_rs:
            model_dict = model_rs.dicts()
            if model_dict:
                v = model_dict[0].get('count')
                if v:
                    return v
        return 0

    @classmethod
    @query_wrap_db
    def check_out_study_book(cls, code):
        return StudyBook.select().where(StudyBook.code == code).first()

    @classmethod
    @query_wrap_db
    def check_out_study_books(cls, codes):
        return StudyBook.select().where(StudyBook.code.in_(codes))

    @classmethod
    @query_wrap_db
    def query_study_books_count_by_pin(cls, pin, unziped):
        model_rs = StudyBook.select(fn.count(StudyBook.id).alias('count')).where(StudyBook.pin == pin, StudyBook.unziped == unziped)
        if model_rs:
            print("query_study_books_count_by_pin:", model_rs)
            model_dict = model_rs.dicts()

            if model_dict:
                print("model_dict item:", model_dict[0])
                v = model_dict[0].get('count')
                if v:
                    return v
        return 0

    @classmethod
    @query_wrap_db
    def check_ziped_books(cls, pin, unziped, size=10, callback=None):
        total = cls.query_study_books_count_by_pin(pin, unziped)
        print("total:", total)
        if total:
            page = 0
            offset = page * size
            while offset < total:
                book_list = StudyBook.select().where(StudyBook.pin == pin, StudyBook.unziped == unziped).offset(
                    offset).limit(size)
                if callback:
                    callback(book_list)
                    _total = cls.query_study_books_count_by_pin(pin, unziped)
                    if _total != total:
                        page = 0
                        total = _total
                    else:
                        page = page + 1
                    offset = page * size
                else:
                    page = page + 1
                    offset = page * size

    # update
    @classmethod
    def batch_update_books_by_codes(cls, params, codes):
        _params = {p: params[p] for p in params if p in StudyBook.field_names()}
        with db:
            # print("batch_update_books_by_codes params:", _params, ",codes:", codes)
            StudyBook.update(**_params).where(StudyBook.code.in_(codes)).execute()

    @classmethod
    def update_books_by_id(cls, params, pk_id):
        _params = {p: params[p] for p in params if p in StudyBook.field_names()}
        with db:
            # print("update_books_by_id params:", _params, ",pk_id:", pk_id)
            StudyBook.update(**_params).where(StudyBook.id == pk_id).execute()

    @classmethod
    def update_shelf_books(cls, params_list, wx_id):

        with db:
            for params in params_list:
                code = params.pop("code")
                _params = {p: params[p] for p in params if p in BookShelf.field_names()}
                BookShelf.update(**_params).where(BookShelf.wx_id == wx_id, BookShelf.code == code).execute()

    # insert datas
    @classmethod
    def batch_insert_books(cls, book_list):
        with db:
            StudyBook.insert_many(book_list).execute()

    @classmethod
    def new_study_book(cls, book_params):
        _params = {p: book_params[p] for p in book_params if p in StudyBook.field_names()}
        sb: StudyBook = StudyBook(**_params)
        with db:
            sb.save(force_insert=True)
            return sb

    @classmethod
    def new_book_shelf(cls, params):
        _params = {p: params[p] for p in params if p in BookShelf.field_names()}
        bs: BookShelf = BookShelf(**_params)
        with db:
            bs.save(force_insert=True)
            return bs

    @classmethod
    def new_study_essay(cls, essay_params):
        _params = {p: essay_params[p] for p in essay_params if p in StudyEssay.field_names()}
        sb: StudyEssay = StudyEssay(**_params)
        with db:
            sb.save(force_insert=True)
            return sb

    @classmethod
    def new_study_hanzi(cls, hz_params):
        _params = {p: hz_params[p] for p in hz_params if p in StudyHanzi.field_names()}
        sb: StudyHanzi = StudyHanzi(**_params)
        with db:
            sb.save(force_insert=True)
            return sb

    @classmethod
    def new_essay_hanzi(cls, essay_id, hz_id):
        sb: EssayHanzi = EssayHanzi(essay=essay_id, hz=hz_id)
        with db:
            sb.save(force_insert=True)
            return sb

    # Del
    @classmethod
    def del_shelf_books(cls, wx_id, bookshelf_code):
        with db:
            BookShelf.delete().where(BookShelf.code == bookshelf_code, BookShelf.wx_id == wx_id).execute()



