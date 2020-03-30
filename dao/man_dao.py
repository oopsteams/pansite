# -*- coding: utf-8 -*-
"""
Created by susy at 2020/3/30
"""
from dao.models import db, query_wrap_db, ClientDataItem, UserRootCfg
from utils.constant import TOP_DIR_FILE_NAME
from cfg import PAN_ROOT_DIR


class ManDao(object):

    # Query
    @classmethod
    @query_wrap_db
    def check_root_cfg_fetch(cls, fs_id):
        return UserRootCfg.select().where(UserRootCfg.fs_id == fs_id).first()

    # Update
    @classmethod
    def update_root_cfg_by_id(cls, pk_id, params):
        _params = {p: params[p] for p in params if p in UserRootCfg.field_names()}
        with db:
            UserRootCfg.update(**_params).where(UserRootCfg.id == pk_id).execute()

    # New
    @classmethod
    def new_root_cfg(cls, fs_id, filename, user_id, pan_id, desc, source='local', pin=0):
        #  "fs_id", "filename", "account_id", "pin", "panacc", "source", "desc"
        urc = UserRootCfg(fs_id=fs_id,
                          filename=filename,
                          account_id=user_id,
                          panacc=pan_id,
                          desc=desc,
                          source=source,
                          pin=pin
                          )
        with db:
            urc.save(force_insert=True)
            return urc.id
