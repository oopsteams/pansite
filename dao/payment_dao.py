# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/3
"""
from dao.models import db, query_wrap_db, PaymentAccount, Org, AuthUser, CreditRecord
from utils import obfuscate_id, get_today_zero_datetime, constant
from peewee import fn, ModelSelect, SQL
import json


class PaymentDao(object):

    @classmethod
    @query_wrap_db
    def query_payment_account_by_account_id(cls, account_id):
        return PaymentAccount.select().where(PaymentAccount.account_id == account_id).first()

    @classmethod
    @query_wrap_db
    def query_today_signed_record(cls, ref_id):
        return CreditRecord.select().where(CreditRecord.ref_id == ref_id,
                                           CreditRecord.source == constant.CREDIT_SOURCE["LOGIN"]).first()

    @classmethod
    @query_wrap_db
    def query_signed_extra_reward_record(cls, ref_id):
        return CreditRecord.select().where(CreditRecord.ref_id == ref_id,
                                           CreditRecord.source == constant.CREDIT_SOURCE["LOGIN_EXTRA"]).first()

    ###############################
    # UPDATE TO DB
    ###############################
    @classmethod
    def update_credit_record(cls, cr_id, params):
        _params = {p: params[p] for p in params if p in CreditRecord.field_names()}
        with db:
            CreditRecord.update(**_params).where(CreditRecord.cr_id == cr_id).execute()

    @classmethod
    def update_payment_account(cls, pay_id, params):
        _params = {p: params[p] for p in params if p in PaymentAccount.field_names()}
        with db:
            PaymentAccount.update(**_params).where(PaymentAccount.pay_id == pay_id).execute()

    @classmethod
    def un_freeze_credit_by_id(cls, pay_id, frozen_amount):
        with db:
            # db.execute_sql(
            #     "update paymentaccount set frozen_amount = frozen_amount - {} where pay_id={}".format(frozen_amount, pay_id))
            PaymentAccount.update(frozen_amount=PaymentAccount.frozen_amount - frozen_amount).where(PaymentAccount.pay_id == pay_id).execute()

    @classmethod
    def active_payment_frozen(cls, account_id):
        with db:
            # db.execute_sql("update paymentaccount set balance = balance - frozen_amount where account_id={}".format(account_id))
            PaymentAccount.update(balance=PaymentAccount.balance - PaymentAccount.frozen_amount).where(PaymentAccount.account_id == account_id).execute()
            PaymentAccount.update(frozen_amount=0).where(PaymentAccount.account_id == account_id).execute()

    ###############################
    # SAVE TO DB
    ###############################

    @classmethod
    def signed_credit_record(cls, account_id, ref_id, params):
        cr = CreditRecord(account_id=account_id,
                          ref_id=ref_id,
                          amount=params['amount'],
                          start_at=params['start_at'],
                          source=params['source'],
                          balance=params['balance'],
                          counter=params['counter']
                          )
        if "end_at" in params:
            cr.end_at = params['end_at']
        if "nounce" in params:
            cr.nounce = params['nounce']
        with db:
            cr.save(force_insert=True)
            return cr

    @classmethod
    def new_payment_account(cls, account_id, ref_id, params):
        pa = PaymentAccount(account_id=account_id,
                            ref_id=ref_id,
                            account_type=0,
                            start_at=params['start_at'],
                            source=params['source'],
                            balance=params['balance'],
                            amount=params['amount'],
                            frozen_amount=params['frozen_amount'],
                            )

        if "end_at" in params:
            pa.end_at = params['end_at']
        if "nounce" in params:
            pa.nounce = params['nounce']


        if "end_at" in params:
            pa.end_at = params['end_at']
        if "nounce" in params:
            pa.nounce = params['nounce']
        with db:
            pa.save(force_insert=True)
            return pa
