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
    def query_study_books_count_by_pin(cls, pin):
        model_rs = StudyBook.select(fn.count(StudyBook.id)).where(StudyBook.pin == pin).alias('count')
        if model_rs:
            model_dict = model_rs.dicts()
            if model_dict:
                v = model_dict[0].get('count')
                if v:
                    return v
        return 0

    # inert datas
    @classmethod
    def batch_insert_books(cls, book_list):
        with db:
            StudyBook.insert_many(book_list).execute()

    @classmethod
    @query_wrap_db
    def check_expired_pan_account(cls, pin, size=10, callback=None):
        total = cls.query_study_books_count_by_pin(pin)
        if total:
            page = 0
            offset = page * size
            while offset < total:
                book_list = StudyBook.select().where(StudyBook.pin == 0).offset(offset).limit(size)
                if callback:
                    callback(book_list)
                page = page + 1
                offset = page * size

