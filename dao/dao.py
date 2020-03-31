# -*- coding: utf-8 -*-
"""
Created by susy at 2019/10/17
"""

from dao.models import db, Accounts, DataItem, DataItemExt, PanAccounts, ShareLogs, TransferLogs, AccountExt, UserRootCfg, \
    query_wrap_db
from utils import utils_es, get_now_datetime, log as logger
from dao.es_dao import es_dao_local
from typing import Callable, Tuple
from peewee import fn, ModelSelect
from utils.constant import TOP_DIR_FILE_NAME
import traceback


class DataDao(object):

    @classmethod
    @query_wrap_db
    def account_by_passwd(cls, name, passwd):
        account_list = Accounts.select().where((Accounts.name == name) | (Accounts.mobile_no == name), Accounts.password == passwd)
        print("account_list:", account_list)
        for acc in account_list:
            print("acc id:", acc.id)
            # return object_to_dict(acc)
            return acc
        return None

    @classmethod
    @query_wrap_db
    def account_by_name(cls, name):
        account_list = Accounts.select().where((Accounts.name == name) | (Accounts.mobile_no == name))
        for acc in account_list:
            return acc
        return None

    @classmethod
    @query_wrap_db
    def account_by_id(cls, id):
        try:
            return Accounts.get(id=id)
        except Exception:
            pass
        return None

    @classmethod
    @query_wrap_db
    def query_pan_acc_count_by_acc_id(cls, acc_id):
        model_rs: ModelSelect = PanAccounts.select(fn.count(PanAccounts.id).where(
            PanAccounts.user_id == acc_id).alias('count'))
        if model_rs:
            model_dict = model_rs.dicts()
            if model_dict:
                v = model_dict[0].get('count')
                if v:
                    return v
        return 0

    @classmethod
    @query_wrap_db
    def pan_account_by_id(cls, id):
        try:
            return PanAccounts.get(id=id)
        except Exception:
            traceback.print_exc()
            pass
        return None

    @classmethod
    @query_wrap_db
    def pan_account_list(cls, account_id=None, cnt=5) -> list:
        if account_id:
            _pan_account_list = PanAccounts.select().where(PanAccounts.user_id == account_id).order_by(PanAccounts.pin.desc()).order_by(PanAccounts.use_count).offset(0).limit(cnt)
        else:
            _pan_account_list = PanAccounts.select().order_by(PanAccounts.pin.desc()).order_by(PanAccounts.use_count).offset(0).limit(cnt)
        logger.info("pan_account_list:", _pan_account_list)
        # for acc in _pan_account_list:
        #     if transfer_to_dict:
        #         pan_acc_list.append(PanAccounts.to_dict(acc))
        #     else:
        #         pan_acc_list.append(acc)
        # if account_id:
        #     return pan_acc_list[0] if pan_acc_list else None
        return _pan_account_list

    @classmethod
    @query_wrap_db
    def pan_account_by_name(cls, account_id, name) -> PanAccounts:
        return PanAccounts.select().where(PanAccounts.user_id == account_id, PanAccounts.name == name).first()

    @classmethod
    @query_wrap_db
    def pan_account_by_bd_uid(cls, account_id, bd_uid) -> PanAccounts:
        return PanAccounts.select().where(PanAccounts.user_id == account_id, PanAccounts.bd_uid == bd_uid).first()

    @classmethod
    @query_wrap_db
    def account_ext_by_acc_id(cls, account_id) -> AccountExt:
        return AccountExt.select().where(AccountExt.account_id == account_id).first()

    @classmethod
    @query_wrap_db
    def account_ext_by_bd_user_id(cls, user_id) -> AccountExt:
        return AccountExt.select().where(AccountExt.user_id == user_id).first()

    @classmethod
    @query_wrap_db
    def check_expired_pan_account(cls, size=10, callback=None):
        fetch_size = size
        while fetch_size == size:
            _pan_account_list = PanAccounts.select().where(PanAccounts.expires_at < get_now_datetime()).limit(size)
            fetch_size = len(_pan_account_list)
            if callback:
                callback(_pan_account_list)

    @classmethod
    @query_wrap_db
    def check_expired_pan_account_by_id(cls, pan_id, callback=None):
        _pan_account_list = PanAccounts.select().where(PanAccounts.id == pan_id, PanAccounts.expires_at < get_now_datetime())
        if callback:
            return callback(_pan_account_list)
        return None

    @classmethod
    @query_wrap_db
    def get_data_item_by_fs_id(cls, fs_id):
        try:
            return DataItem.get(fs_id=fs_id)
        except Exception:
            pass
        return None

    @classmethod
    def query_data_item_by_fs_id(cls, fs_id):
        return cls.get_data_item_by_fs_id(fs_id)

    @classmethod
    @query_wrap_db
    def get_data_item_by_id(cls, pk_id):
        return DataItem.select().where(DataItem.id == pk_id).first()

    @classmethod
    @query_wrap_db
    def get_data_item_ext_by_id(cls, pk_id):
        return DataItemExt.select().where(DataItemExt.id == pk_id).first()

    @classmethod
    @query_wrap_db
    def data_item_ext_exist(cls, pk_id):
        return DataItemExt.select().where(DataItemExt.id == pk_id).exists()

    @classmethod
    @query_wrap_db
    def get_root_item_by_pan_id(cls, pan_id):
        return DataItem.select().where(DataItem.filename == TOP_DIR_FILE_NAME, DataItem.panacc == pan_id)

    @classmethod
    @query_wrap_db
    def get_root_item_by_user_id(cls, user_id):
        mode_select = DataItem.select(DataItem, PanAccounts).join(
            PanAccounts, on=(DataItem.panacc == PanAccounts.id),
            attr="pan").where(DataItem.filename == TOP_DIR_FILE_NAME, PanAccounts.user_id == user_id)
        # print("get_root_item_by_user_id:", mode_select)
        return mode_select

    @classmethod
    @query_wrap_db
    def query_shared_log_by_fs_id(cls, fs_id):
        share_logs = ShareLogs.select().where(ShareLogs.fs_id == fs_id).limit(1)
        if share_logs:
            return share_logs[0]
        return None

    @classmethod
    @query_wrap_db
    def query_shared_log_by_pk_id(cls, pk_id) -> ShareLogs:
        return ShareLogs.select().where(ShareLogs.id == pk_id).first()

    @classmethod
    @query_wrap_db
    def query_transfer_logs(cls, share_log_id):
        return TransferLogs.select().where(TransferLogs.share_log_id == share_log_id)

    @classmethod
    @query_wrap_db
    def query_transfer_logs_pan_id(cls, share_log_id, pan_id):
        return TransferLogs.select().where(TransferLogs.share_log_id == share_log_id, TransferLogs.pan_account_id == pan_id).first()

    @classmethod
    @query_wrap_db
    def query_transfer_logs_by_pk_id(cls, pk_id) -> TransferLogs:
        return TransferLogs.select().where(TransferLogs.id == pk_id).first()

    @classmethod
    @query_wrap_db
    def query_transfer_logs_by_fs_id(cls, fs_id):
        return TransferLogs.select().where(TransferLogs.fs_id == fs_id)

    @classmethod
    @query_wrap_db
    def query_root_files_by_user_id(cls, account_id):
        return UserRootCfg.select().where(UserRootCfg.account_id == account_id)

    @classmethod
    @query_wrap_db
    def check_free_root_files_exist(cls, fs_id, source):
        return UserRootCfg.select().where(UserRootCfg.fs_id == fs_id, UserRootCfg.source == source)

    @classmethod
    @query_wrap_db
    def query_root_files(cls):
        return UserRootCfg.select()

    @classmethod
    @query_wrap_db
    def query_free_root_files(cls):
        return UserRootCfg.select().where(UserRootCfg.source == 'local', UserRootCfg.pin == 0)

    #################################################################
    # split line
    #################################################################

    @classmethod
    @query_wrap_db
    def check_data_item_exists_by_parent(cls, item_id, parent_id):
        return DataItem.select().where(DataItem.id == item_id, DataItem.parent == parent_id).exists()

    @classmethod
    @query_wrap_db
    def query_data_item_by_parent(cls, parent_id, is_dir=True, offset=0, limit=100):
        return DataItem.select().where(DataItem.isdir == (1 if is_dir else 0), DataItem.parent == parent_id).limit(limit).offset(offset)

    @classmethod
    @query_wrap_db
    def query_data_item_by_parent_all(cls, parent_id, offset=0, limit=100):
        return DataItem.select().where(DataItem.parent == parent_id).limit(limit).offset(offset)

    @classmethod
    @query_wrap_db
    def query_user_list_by_keyword(cls, keyword, offset=0, limit=100):
        if keyword:
            return Accounts.select().where(Accounts.name.startswith(keyword) | Accounts.fuzzy_id.startswith(keyword)).limit(limit).offset(offset)
        else:
            return Accounts.select().limit(limit).offset(offset)

    @classmethod
    @query_wrap_db
    def query_data_item_by_parent_pin(cls, parent_id, pin=1, is_dir=True, offset=0, limit=100):
        return DataItem.select().where(DataItem.isdir == (1 if is_dir else 0), DataItem.parent == parent_id, DataItem.pin == pin).limit(
            limit).offset(offset)

    @classmethod
    @query_wrap_db
    def query_data_item_by_parent_synced(cls, parent_id, synced=1, is_dir=True, offset=0, limit=100):
        return DataItem.select().where(DataItem.isdir == (1 if is_dir else 0), DataItem.parent == parent_id,
                                       DataItem.synced == synced).limit(
            limit).offset(offset)

    @classmethod
    @query_wrap_db
    def query_leaf_data_item(cls, is_dir=True, offset=0, limit=100):
        # Parent = DataItem.alias()
        return DataItem.select().where(DataItem.isdir == (1 if is_dir else 0), DataItem.pin == 0).limit(limit).offset(offset)

    @classmethod
    def sync_data_item_to_es(cls, data_item: DataItem):
        es_item_path = data_item.path
        pos = 0
        if es_item_path.endswith(data_item.filename):
            # print("new path:", data_item.id)
            es_item_path = es_item_path[:-len(data_item.filename)]
            _p = es_item_path.strip('/')
            pos = len(_p.split('/'))
        body = utils_es.build_es_item_json_body(data_item.id, data_item.category, data_item.isdir, data_item.pin,
                                                data_item.fs_id, data_item.size, data_item.account_id,
                                                data_item.filename,
                                                es_item_path, data_item.server_ctime, data_item.updated_at,
                                                data_item.created_at, data_item.parent, data_item.panacc, pos=pos)
        es = es_dao_local()
        # print("body:", body)
        es.index(data_item.id, body)

    @classmethod
    @query_wrap_db
    def find_need_update_size_dir(cls, parent_id) -> DataItem:
        return DataItem.select().where(DataItem.parent == parent_id, DataItem.isdir == 1, DataItem.sized == 0).first()

    @classmethod
    @query_wrap_db
    def check_account_ext_exist(cls, user_id):
        return AccountExt.select().where(AccountExt.user_id == user_id).exists()


    @classmethod
    @query_wrap_db
    def sum_size_dir(cls, parent_id):
        model_rs: ModelSelect = DataItem.select(fn.SUM(DataItem.size).alias('total')).where(DataItem.parent == parent_id)
        if model_rs:
            # print('model_rs:', model_rs.dicts())
            v = model_rs.dicts()[0].get('total')
            if v:
                return v
        return 0

    ################################################
    # UPDATE FUNCTIONS                             #
    ################################################

    @classmethod
    def update_data_item(cls, pk_id, params):
        _params = {p: params[p] for p in params if p in DataItem.field_names()}
        with db:
            # old_data_item = DataItem.get_by_id(pk=pk_id)
            DataItem.update(**_params).where(DataItem.id == pk_id).execute()
            # for f in fields:
            #     if f in params:
            #         setattr(old_data_item, f, params[f])
            #         print("{}:{}".format(f, params[f]))
            # old_data_item.save()
            # print("update data item:", old_data_item)
            es_up_params = es_dao_local().filter_update_params(_params)
            if es_up_params:
                es_dao_local().update_fields(pk_id, **es_up_params)

    @classmethod
    def update_data_item_ext(cls, pk_id, params):
        _params = {p: params[p] for p in params if p in DataItemExt.field_names()}
        with db:
            DataItemExt.update(**_params).where(DataItemExt.id == pk_id).execute()

    @classmethod
    def update_data_item_by_parent_id(cls, parent_id, params):
        _params = {p: params[p] for p in params if p in DataItem.field_names()}
        with db:
            # old_data_item = DataItem.get_by_id(pk=pk_id)
            DataItem.update(**_params).where(DataItem.parent == parent_id).execute()

    @classmethod
    def update_account_by_pk(cls, pk_id, params):
        """
        :param pk_id:
        :param params:
        :return:
        """
        fields = ['password', 'client_id', 'client_secret', 'access_token', 'login_token', 'token_updated_at',
                  'login_updated_at', 'mobile_no', 'fuzzy_id', 'pin', 'last_login_at', 'nickname']
        _params = {p: params[p] for p in params if p in fields}
        with db:
            Accounts.update(**params).where(Accounts.id == pk_id).execute()

    @classmethod
    def update_pan_account_used(cls, params):
        with db:
            for item in params:
                _id = item['id']
                used = item['used']
                used_str = "+%s" % used
                if used < 0:
                    used_str = "%s" % used
                sql = "update panaccounts set use_count=use_count%s where id=%s" % (used_str, _id)
                print("sql:", sql)
                PanAccounts.raw(sql).execute()

    @classmethod
    def update_pan_account_by_pk(cls, pk_id, params):
        """
        :param pk_id:
        :param params:
        :return:
        """
        _params = {p: params[p] for p in params if p in PanAccounts.field_names()}
        print("update_pan_account_by_pk _params:", _params)
        with db:
            PanAccounts.update(**_params).where(PanAccounts.id == pk_id).execute()

    @classmethod
    def update_pan_account_by_acc_id(cls, acc_id, params):
        _params = {p: params[p] for p in params if p in PanAccounts.field_names()}
        with db:
            PanAccounts.update(**_params).where(PanAccounts.user_id == acc_id).execute()

    @classmethod
    def update_share_log_by_pk(cls, pk_id, params):
        """
        :param pk_id:
        :param params:
        :return:
        """
        _params = {p: params[p] for p in params if p in ShareLogs.field_names()}
        # print("update_share_log_by_pk _params:", _params)
        with db:
            ShareLogs.update(**_params).where(ShareLogs.id == pk_id).execute()

    @classmethod
    def update_account_ext_by_user_id(cls, user_id, params):
        _params = {p: params[p] for p in params if p in AccountExt.field_names()}
        print("update_account_ext_by_user_id _params:", _params)
        with db:
            AccountExt.update(**_params).where(AccountExt.user_id == user_id).execute()

    @classmethod
    def update_transfer_log_by_pk(cls, pk_id, params):
        """
        :param pk_id:
        :param params:
        :return:
        """
        _params = {p: params[p] for p in params if p in TransferLogs.field_names()}
        print("update_transfer_log_by_pk _params:", _params)
        with db:
            TransferLogs.update(**_params).where(TransferLogs.id == pk_id).execute()

    @classmethod
    def del_share_log_by_pk(cls, pk_id):
        with db:
            ShareLogs.delete_by_id(pk_id)

    @classmethod
    def del_data_item_by_parent_pin(cls, parent, pin, is_dir=True):
        with db:
            DataItem.delete().where(DataItem.parent == parent, DataItem.pin == pin, DataItem.isdir == (1 if is_dir else 0)).execute()

    @classmethod
    def del_data_item_by_parent_synced(cls, parent, synced, is_dir=True):
        with db:
            DataItem.delete().where(DataItem.parent == parent, DataItem.synced == synced,
                                    DataItem.isdir == (1 if is_dir else 0)).execute()

    @classmethod
    def del_data_item_by_id(cls, pk_id):
        with db:
            DataItem.delete().where(DataItem.id == pk_id).execute()

    ###############################
    # SAVE TO DB
    ###############################

    @classmethod
    def save_data_item(cls, is_dir, params):
        data_item = DataItem(category=params['category'],
                             isdir=is_dir,
                             filename=params['filename'],
                             fs_id=params['fs_id'],
                             path=params['path'],
                             size=params['size'],
                             md5_val=params.get('md5_val', ''),
                             account_id=params.get('account_id'),
                             parent=params.get('parent', 0),
                             panacc=params.get('panacc', 0)
                             )
        with db:
            data_item.save(force_insert=True)
        cls.sync_data_item_to_es(data_item)

    @classmethod
    def new_data_item_ext(cls, pk_id, params):
        data_item_ext = DataItemExt(id=pk_id, fs_id=params["fs_id"], mlink=params["mlink"],
                                    start_at_time=params["start_at_time"])
        with db:
            data_item_ext.save(force_insert=True)
        return data_item_ext

    @classmethod
    def new_pan_account(cls, user_id, name, client_id, client_secret, access_token, refresh_token, expires_at,
                        now, pin=0, bd_uid=0) -> int:

        with db:
            pan_acc: PanAccounts = PanAccounts(user_id=user_id, name=name, client_id=client_id,
                                               client_secret=client_secret, access_token=access_token,
                                               refresh_token=refresh_token, expires_at=expires_at, token_updated_at=now,
                                               pin=pin, bd_uid=bd_uid)
            pan_acc.save(force_insert=True)
            pan_acc_id = pan_acc.id
        if pan_acc_id:
            return pan_acc_id
        return 0

    @classmethod
    def new_share_log(cls, fs_id, filename, md5_val, dlink, password, period, account_id, pan_id):
        """
        :param fs_id:
        :param password:
        :param period:
        :return:
        """
        with db:
            share_log: ShareLogs = ShareLogs(fs_id=fs_id, filename=filename, password=password, period=period, pin=1,
                                             md5_val=md5_val, dlink=dlink, account_id=account_id, pan_account_id=pan_id)
            share_log.save(force_insert=True)
            share_log_id = share_log.id
        if share_log_id:
            return share_log_id, share_log
        return 0, None

    @classmethod
    def new_account(cls, mobile_no, password, now, envelop_user_lambda: Callable[..., Tuple[str, dict]]):
        with db:
            acc: Accounts = Accounts(name=mobile_no, mobile_no=mobile_no, nickname=mobile_no, password=password)
            acc.save(force_insert=True)
            acc_id = acc.id
        if acc_id:
            # fuzzy_id = obfuscate_id(acc_id)
            # token = make_token(fuzzy_id, acc)

            user_token, user_ext_dict = envelop_user_lambda(acc)
            cls.update_account_by_pk(pk_id=acc_id, params={"fuzzy_id": user_ext_dict['id'], "login_updated_at": now,
                                                           "login_token": user_token})
            return user_token, user_ext_dict

    @classmethod
    def new_transfer_log(cls, share_log_id, fs_id, path, filename, size, category, md5_val, dlink, account_id, expired_at, pan_account_id):
        """
        :param share_log_id:
        :param fs_id:
        :param path:
        :param size:
        :param category:
        :param md5_val:
        :return:
        """
        with db:
            transfer_log: TransferLogs = TransferLogs(share_log_id=share_log_id, fs_id=fs_id, path=path,
                                                      filename=filename, size=size,
                                                      category=category, md5_val=md5_val, dlink=dlink,
                                                      account_id=account_id, expired_at=expired_at,
                                                      pan_account_id=pan_account_id)
            transfer_log.save(force_insert=True)
            transfer_log_id = transfer_log.id
        if transfer_log_id:
            return transfer_log_id, transfer_log
        return 0, None

    @classmethod
    def new_accounts_ext(cls, user_id, username, realname, portrait, userdetail, birthday, marriage, sex, blood, figure,
                         constellation, education, trade, job, is_realname, account_id):
        with db:
            acc_ext: AccountExt = AccountExt(user_id=user_id, username=username, realname=realname, portrait=portrait,
                                             userdetail=userdetail, birthday=birthday, marriage=marriage, sex=sex,
                                             blood=blood, figure=figure, constellation=constellation,
                                             education=education, trade=trade, job=job, is_realname=is_realname,
                                             account_id=account_id)
            acc_ext.save(force_insert=True)
            return acc_ext

    @classmethod
    def new_root_item(cls, user_id, pan_id):
        data_item = DataItem(category=6,
                             isdir=1,
                             filename=TOP_DIR_FILE_NAME,
                             fs_id='0',
                             path='/',
                             size=0,
                             md5_val='',
                             account_id=user_id,
                             parent=0,
                             panacc=pan_id
                             )
        with db:
            data_item.save(force_insert=True)
            return data_item.id, data_item
