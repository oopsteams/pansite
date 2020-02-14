# -*- coding: utf-8 -*-
"""
Created by susy at 2019/11/8
"""
from dao.dao import DataDao
import pytz
from dao.models import PanAccounts
from cfg import PAN_SERVICE, MASTER_ACCOUNT_ID


class BaseService:

    def __init__(self):
        self.default_tz = pytz.timezone('Asia/Chongqing')
        # self.pan_acc: PanAccounts = DataDao.pan_account_list(MASTER_ACCOUNT_ID, False)
