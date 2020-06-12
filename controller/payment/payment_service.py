# -*- coding: utf-8 -*-
"""
Created by susy at 2020/6/3
"""
from controller.base_service import BaseService
from dao.models import PaymentAccount, CreditRecord
from dao.payment_dao import PaymentDao
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
class PaymentService(BaseService):

    def clear_cache(self, account_id, ref_id):
        clear_balance_cache(account_id)
        clear_signed_state_cache(ref_id)

    @cache_data("pay_balance_{1}", timeout_seconds=lambda s, account_id, rs: PAY_SIGNED_CACHE_TIMEOUT)
    def query_credit_balance(self, account_id):
        rs = {
                "balance": 0,
                "amount": 0,
                "frozen_amount": 0
            }
        pa: PaymentAccount = PaymentDao.query_payment_account_by_account_id(account_id=account_id)
        if pa:
            rs = {
                "balance": pa.balance,
                "amount": pa.amount,
                "frozen_amount": pa.frozen_amount
            }
        # cache
        return rs

    @cache_data("pay_signed_{1}", timeout_seconds=lambda s, ref_id, rs: rs["to"])
    def check_signed(self, ref_id):
        rs = None
        cr: CreditRecord = PaymentDao.query_today_signed_record(ref_id)
        if cr:
            diff = compare_dt(cr.start_at, get_today_zero_datetime())
            print("login cr start_at - today diff:", diff)
            rs = {"signed": diff > 0,
                  "to": int((get_today_zero_datetime(+1) - get_now_datetime()).total_seconds()) + 1,
                  "cr_id": cr.cr_id,
                  "amount": cr.amount
                  }
            new_counter = 1
            if rs["signed"]:
                extra_cr: CreditRecord = PaymentDao.query_signed_extra_reward_record(ref_id)
                if extra_cr:
                    diff = compare_dt(extra_cr.start_at, get_today_zero_datetime())
                    print("extra cr start_at - today diff:", diff)
                    if diff >= 0:
                        new_counter = extra_cr.counter

            rs["counter"] = new_counter

            # rs["to"] = (get_today_zero_datetime(+1) - get_now_datetime()).total_seconds()
        return rs

    def update_payment_account(self, account_id, ref_id, amount, nounce=0):
        pa: PaymentAccount = PaymentDao.query_payment_account_by_account_id(account_id=account_id)
        if not pa:
            params = dict(
                start_at=get_now_datetime(),
                source=constant.PAYMENT_ACC_SOURCE["CREDIT"],
                balance=amount,
                amount=amount,
                frozen_amount=0,
                nounce=nounce
            )
            PaymentDao.new_payment_account(account_id=account_id, ref_id=ref_id, params=params)
        else:
            params = dict(
                balance=pa.balance+amount,
                amount=pa.amount+amount,
                frozen_amount=0,
                nounce=nounce
            )

            PaymentDao.update_payment_account(pa.pay_id, params)
            # clear_cache("pay_balance_{}".format(account_id))

    def reward_credit_by_signed(self, account_id, ref_id):
        # 查询今天是否已经signed
        nounce = get_now_ts()
        rs = signed = self.check_signed(ref_id)
        if signed:
            if not signed["signed"]:
                extra_cr: CreditRecord = PaymentDao.query_signed_extra_reward_record(ref_id)
                new_counter = 1
                extra_amount = 0
                if extra_cr:
                    diff_val = compare_dt(extra_cr.start_at, get_today_zero_datetime())
                    if diff_val >= 0:
                        if diff_val == 0:
                            new_counter = extra_cr.counter + 1
                        else:
                            new_counter = extra_cr.counter
                        if diff_val == 0 and constant.CREDIT_SIGNED_LEVEL:
                            for item in constant.CREDIT_SIGNED_LEVEL:
                                cnt = item[0]
                                _amount = item[1]
                                if extra_cr.counter < cnt:
                                    if _amount < 0:
                                        item_l = len(item)
                                        renew_counter = 1
                                        if item_l > 2:
                                            renew_counter = item[2]
                                        new_counter = renew_counter
                                        if item_l > 3:
                                            extra_amount = item[3]
                                    else:
                                        extra_amount = _amount
                                    break

                    params = dict(
                        start_at=get_today_zero_datetime(1),
                        counter=new_counter
                    )
                    PaymentDao.update_credit_record(extra_cr.cr_id, params)

                else:
                    params = dict(
                        amount=constant.CREDIT_SIGNED_REWARD,
                        start_at=get_today_zero_datetime(1),
                        source=constant.CREDIT_SOURCE["LOGIN_EXTRA"],
                        balance=constant.CREDIT_SIGNED_REWARD,
                        counter=new_counter
                    )
                    PaymentDao.signed_credit_record(account_id, ref_id, params)

                    # update extra_cr start_at -> tomorrow && counter
                cr_params = dict(
                    start_at=get_today_zero_datetime(1),
                    amount=extra_amount + constant.CREDIT_SIGNED_REWARD
                )
                print("will update cr params:", cr_params, ",cr_id:", signed["cr_id"])
                PaymentDao.update_credit_record(signed["cr_id"], cr_params)
                self.update_payment_account(account_id, ref_id, cr_params["amount"], nounce)
                clear_signed_state_cache(ref_id)
                clear_balance_cache(account_id)
                rs = self.check_signed(ref_id)
        else:
            params = dict(
                amount=constant.CREDIT_SIGNED_REWARD,
                start_at=get_today_zero_datetime(1),
                source=constant.CREDIT_SOURCE["LOGIN"],
                balance=constant.CREDIT_SIGNED_REWARD,
                counter=0
            )
            PaymentDao.signed_credit_record(account_id, ref_id, params)
            self.update_payment_account(account_id, ref_id, params["amount"], nounce)
            clear_signed_state_cache(ref_id)
            clear_balance_cache(account_id)
            rs = self.check_signed(ref_id)
        return rs

    def reward_credit_by_invite(self):
        pass

    def active_credit(self, params):
        pass

    def freeze_credit(self, account_id, amount):
        pa: PaymentAccount = PaymentDao.query_payment_account_by_account_id(account_id=account_id)
        nounce = get_now_ts()
        params = dict(
            frozen_amount=pa.frozen_amount + amount,
            nounce=nounce
        )
        PaymentDao.update_payment_account(pa.pay_id, params)
        return pa.pay_id

    def un_freeze_credit_by_id(self, pay_id, amount):
        PaymentDao.un_freeze_credit_by_id(pay_id, amount)

    def active_frozen_credit(self, account_id):
        PaymentDao.active_payment_frozen(account_id)


payment_service = PaymentService()
