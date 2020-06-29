# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/28
"""
from dao.models import db, query_wrap_db, StudyBook


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
    def batch_insert_books(cls, book_list):
        with db:
            StudyBook.insert_many(book_list).execute()
