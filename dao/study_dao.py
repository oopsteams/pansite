# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/28
"""
from dao.models import db, query_wrap_db, StudyBook
from peewee import fn


class StudyDao(object):

    # query data
    @classmethod
    @query_wrap_db
    def query_study_book_list(cls, pin, offset=0, cnt=50) -> list:
        rs = []
        ms = StudyBook.select().where(StudyBook.pin == pin).order_by(StudyBook.idx.asc()).offset(offset).limit(cnt)
        for sb in ms:
            rs.append(StudyBook.to_dict(sb, ['id']))
        return rs

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
            print("batch_update_books_by_codes params:", _params, ",codes:", codes)
            StudyBook.update(**_params).where(StudyBook.code.in_(codes)).execute()

    @classmethod
    def update_books_by_id(cls, params, pk_id):
        _params = {p: params[p] for p in params if p in StudyBook.field_names()}
        with db:
            print("update_books_by_id params:", _params, ",pk_id:", pk_id)
            StudyBook.update(**_params).where(StudyBook.id == pk_id).execute()

    # insert datas
    @classmethod
    def batch_insert_books(cls, book_list):
        with db:
            StudyBook.insert_many(book_list).execute()



