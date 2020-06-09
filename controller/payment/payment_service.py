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
    clear_cache("pay_signed_{}".format(ref_id))


def clear_balance_cache(account_id):
    clear_cache("pay_balance_{}".format(account_id))

@singleton
class PaymentService(BaseService):

    @cache_data("pay_balance_{1}")
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
            rs = {"signed": compare_dt(cr.start_at, get_today_zero_datetime()) > 0,
                  "to": (get_today_zero_datetime(+1) - get_now_datetime()).total_seconds(),
                  "cr_id": cr.cr_id,
                  "amount": cr.amount
                  }
            new_counter = 1
            if rs["signed"]:
                extra_cr: CreditRecord = PaymentDao.query_signed_extra_reward_record(ref_id)
                if extra_cr:
                    if compare_dt(extra_cr.start_at, get_today_zero_datetime()) > 0:
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
            clear_cache("pay_balance_{}".format(account_id))

    def reward_credit_by_signed(self, account_id, ref_id):
        # 查询今天是否已经signed
        nounce = get_now_ts()
        rs = {"signed": 0}
        signed = self.check_signed(ref_id)
        if signed:
            if not signed["signed"]:
                extra_cr: CreditRecord = PaymentDao.query_signed_extra_reward_record(ref_id)
                new_counter = 1
                extra_amount = 0
                if extra_cr:
                    if compare_dt(extra_cr.start_at, get_today_zero_datetime()) >= 0:
                        new_counter = extra_cr.counter + 1
                        if constant.CREDIT_SIGNED_LEVEL:
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
                    pass
                    # update extra_cr start_at -> tomorrow && counter
                cr_params = dict(
                    start_at=get_today_zero_datetime(1),
                    amount=extra_amount + constant.CREDIT_SIGNED_REWARD
                )
                PaymentDao.update_credit_record(signed["cr_id"], cr_params)
                self.update_payment_account(account_id, ref_id, cr_params["amount"], nounce)
                clear_signed_state_cache(ref_id)
                clear_balance_cache(account_id)
                rs["signed"] = 1
        else:
            params = dict(
                amount=constant.CREDIT_SIGNED_REWARD,
                start_at=get_now_datetime(),
                source=constant.CREDIT_SOURCE["LOGIN"],
                balance=constant.CREDIT_SIGNED_REWARD,
                counter=0
            )
            PaymentDao.signed_credit_record(account_id, ref_id, params)
            self.update_payment_account(account_id, ref_id, params["amount"], nounce)
            clear_balance_cache(account_id)
            rs["signed"] = 1
        return rs

    def reward_credit_by_invite(self):
        pass

    def active_credit(self, params):
        pass


payment_service = PaymentService()
