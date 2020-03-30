# -*- coding: utf-8 -*-
"""
Created by susy at 2019/11/8
"""
import requests
from dao.dao import DataDao
from dao.community_dao import CommunityDao
from dao.models import PanAccounts, ShareLogs, DataItem, TransferLogs, try_release_conn, CommunityDataItem
from utils import singleton, log, make_token, obfuscate_id, get_now_datetime, random_password, get_now_ts, restapi, guess_file_type, constant
import pytz
import arrow
from controller.base_service import BaseService
from controller.mpan_service import mpan_service
from controller.auth_service import auth_service
from cfg import PAN_SERVICE, MASTER_ACCOUNT_ID
import time
from dao.es_dao import es_dao_local, es_dao_share
from threading import Thread
from utils.caches import cache_service
# from apscheduler.schedulers.background import BackgroundScheduler
LOGIN_TOKEN_TIMEOUT = constant.LOGIN_TOKEN_TIMEOUT
PAN_ACCESS_TOKEN_TIMEOUT = constant.PAN_ACCESS_TOKEN_TIMEOUT


@singleton
class SyncPanService(BaseService):

    def __init__(self):
        super().__init__()
        self.es_dao_item = es_dao_local()
        self.__thread = None

    def __clear_data_items(self, parent_id, synced=-1, is_dir=True):
        will_del_data_items = DataDao.query_data_item_by_parent_synced(parent_id, synced=synced, is_dir=is_dir, limit=500)
        di: DataItem = None
        doc_ids = []
        for di in will_del_data_items:
            if di.isdir == 1:
                DataDao.update_data_item_by_parent_id(di.id, {"synced": -1})
                self.__clear_data_items(di.id, -1, True)
                self.__clear_data_items(di.id, -1, False)
            doc_ids.append(di.id)
        if doc_ids:
            log.info("delete file by parent_id:{}".format(parent_id))
            self.es_dao_item.bulk_delete(doc_ids)
            DataDao.del_data_item_by_parent_synced(parent_id, synced, is_dir)

    def get_file_list_by_list(self, data_item_list):
        def req_file_list(data_item: DataItem, pan_acc: PanAccounts):
            parent_id = 55
            from_dir = '/'
            if data_item:
                from_dir = data_item.path
                parent_id = data_item.id
            else:
                return
            log.info("sync file:{}, filename:{}".format(data_item.id, data_item.filename))
            if data_item.isdir == 1:
                json_data_list = restapi.file_list(pan_acc.access_token, from_dir)
                if json_data_list is not None:
                    log.info("update synced is -1, parent_id:{}".format(parent_id))
                    DataDao.update_data_item_by_parent_id(parent_id, {"synced": -1})
                else:
                    log.warn("json_data_list is null!")
                if json_data_list:
                    for fi in json_data_list:
                        item_map = dict(category=fi['category'],
                                        isdir=fi['isdir'],
                                        filename=fi['server_filename'],
                                        server_ctime=fi['server_ctime'],
                                        fs_id=fi['fs_id'],
                                        path=fi['path'],
                                        size=fi['size'],
                                        md5_val=fi.get('md5', ''),
                                        account_id=pan_acc.user_id,
                                        panacc=pan_acc.id,
                                        parent=parent_id,
                                        synced=0,
                                        pin=0
                                        )
                        di: DataItem = DataDao.get_data_item_by_fs_id(item_map['fs_id'])

                        if di:
                            DataDao.update_data_item(di.id, item_map)
                            data_item: DataItem = DataDao.get_data_item_by_id(di.id)
                            DataDao.sync_data_item_to_es(data_item)
                            # print("will update data item:", item_map)
                        else:
                            DataDao.save_data_item(fi['isdir'], item_map)
                            # print("will save data item:", item_map)
                        time.sleep(0.1)
                else:
                    log.info("have not any sub files!")
                self.__clear_data_items(parent_id, -1, True)
                self.__clear_data_items(parent_id, -1, False)
            DataDao.update_data_item(data_item.id, {"synced": 1})

        if data_item_list:
            for _data_item in data_item_list:
                pan_acc: PanAccounts = DataDao.pan_account_by_id(_data_item.panacc)
                log.info("will sync data item:{}".format(_data_item.filename))
                req_file_list(_data_item, pan_acc)
        # else:
        #     req_file_list(None, self.pan_acc)

    def sync_dir_file_list(self, data_item, recursion=False):
        # parent_id = 0
        # get_size = 0
        # count = 0
        is_dir = True
        size = 500
        offset = 0
        self.get_file_list_by_list([data_item])
        if data_item.isdir and recursion:
            data_item_list = DataDao.query_data_item_by_parent_pin(parent_id=data_item.id, pin=0, is_dir=is_dir,
                                                                   offset=offset, limit=size)
            if data_item_list and recursion:
                # get_size = len(data_item_list)
                # count = count + get_size
                self.get_file_list_by_list(data_item_list)
                for di in data_item_list:
                    self.sync_dir_file_list(di, recursion)

        #
        # dog = 1000
        # while get_size > 0 and dog > 0:
        #     # offset = offset + size
        #     data_item_list = DataDao.query_leaf_data_item(is_dir, offset, size)
        #     get_size = 0
        #     if data_item_list:
        #         get_size = len(data_item_list)
        #         count = count + get_size
        #         self.get_file_list_by_list(data_item_list)
        #
        #     time.sleep(0.3)
        #     print("sync_dir_file_list did count:", count)
        #     dog = dog - 1

    def sync_from_root(self, item_id, recursion, pan_id, user_id):
        def __run():
            dir_data_item_id = item_id
            key = "sync:pan:dir:%s_%s" % (user_id, pan_id)
            not_exists = cache_service.put(key, get_now_ts())
            if not_exists:
                rs_key = "synced:pan:dir:%s_%s" % (user_id, pan_id)
                cache_service.rm(rs_key)
                root_data_item: DataItem = DataDao.get_data_item_by_id(dir_data_item_id)
                self.sync_dir_file_list(root_data_item, recursion)
                self.__thread = None
                cache_service.rm(key)
                cache_service.put(rs_key, root_data_item.id)
                mpan_service.update_dir_size(root_data_item)
                try_release_conn()
            pass
        if self.__thread:
            return {"state": "block"}
        self.__thread = Thread(target=__run)
        self.__thread.start()
        return {"state": "run"}

    def clear_share_log(self, share_log_id):
        transfer_logs = CommunityDao.query_transfer_logs_by_share_log_id(share_log_id)
        pan_map_cache = {}
        if transfer_logs:
            tl: TransferLogs = None
            for tl in transfer_logs:
                pan_id = tl.pan_account_id
                if pan_id not in pan_map_cache:
                    pan_acc: PanAccounts = DataDao.pan_account_by_id(pan_id)
                    pan_map_cache[pan_id] = pan_acc
                pan_acc = pan_map_cache[pan_id]
                restapi.del_file(pan_acc.access_token, tl.path)
                di: DataItem = DataDao.query_data_item_by_fs_id(tl.fs_id)
                if di:
                    self.es_dao_item.delete(di.id)
                    DataDao.del_data_item_by_id(di.id)
                CommunityDao.del_transfer_log_by_id(tl.id)
        CommunityDao.del_share_log_by_id(share_log_id)

    def clear_all_expired_share_log(self):
        item_list = CommunityDao.query_share_logs_by_hours(-48, 0, 50)
        sl: ShareLogs = None
        for sl in item_list:
            self.clear_share_log(sl.id)

    def __clear_data_item(self, item_id, pan_id):
        out_pan_acc: PanAccounts = DataDao.pan_account_by_id(pan_id)
        _es_dao_item = self.es_dao_item

        def deep_clear(di, pan_acc):
            if di:
                if di.isdir == 1:
                    # 迭代处理
                    size = 50
                    l = size
                    while l == size:
                        sub_items = DataDao.query_data_item_by_parent_all(di.id, limit=size)
                        l = 0
                        if sub_items:
                            l = len(sub_items)
                            for sub_item in sub_items:
                                deep_clear(sub_item, pan_acc)
                        time.sleep(0.2)
                else:
                    fs_id = di.fs_id
                    share_log: ShareLogs = DataDao.query_shared_log_by_fs_id(fs_id)
                    if share_log:
                        self.clear_share_log(share_log.id)
                    transfer_logs = DataDao.query_transfer_logs_by_fs_id(fs_id)
                    if transfer_logs:
                        for tl in transfer_logs:
                            CommunityDao.del_transfer_log_by_id(tl.id)

                _es_dao_item.delete(di.id)
                DataDao.del_data_item_by_id(di.id)

        root_di: DataItem = DataDao.get_data_item_by_id(item_id)
        deep_clear(root_di, out_pan_acc)
        if root_di.parent:
            p_data_item = DataDao.get_data_item_by_fs_id(root_di.parent)
            if p_data_item:
                mpan_service.update_dir_size(p_data_item)
        restapi.del_file(out_pan_acc.access_token, root_di.path)
        # DataDao.del_data_item_by_id(root_di.id)

    def __clear_community_item(self, item_id):

        def deep_clear(di: CommunityDataItem):
            if di:
                if di.isdir == 1:
                    # 迭代处理
                    size = 50
                    l = size
                    while l == size:
                        sub_items = CommunityDao.query_community_item_by_parent_all(di.fs_id, limit=size)
                        l = 0
                        if sub_items:
                            l = len(sub_items)
                            for sub_item in sub_items:
                                deep_clear(sub_item)
                        time.sleep(0.2)

                es_dao_share().delete(di.id)
                CommunityDao.del_community_item_by_id(di.id)

        root_di: CommunityDataItem = CommunityDao.get_data_item_by_id(item_id)
        deep_clear(root_di)

    def clear(self, item_id, pan_id, source):
        if "local" == source:
            self.__clear_data_item(item_id, pan_id)
        elif "shared" == source:
            self.__clear_community_item(item_id)

    def rename(self, item_id, old_name, alias_name, source):
        result = {'state': 0}
        if "local" == source:
            data_item: DataItem = DataDao.get_data_item_by_id(item_id)
            # print("rename data_item:", DataItem.to_dict(data_item))
            # print("old_name:", old_name)
            # print("alias_name:", alias_name)
            if data_item.filename != old_name or data_item.aliasname != alias_name:
                params = {"filename": old_name, "aliasname": alias_name}
                fs_id = int(data_item.fs_id)  # 重要, 网盘服务中类型为Int,本地为了兼容所有类型id使用了varchar
                pan_acc: PanAccounts = auth_service.get_pan_account(data_item.panacc, data_item.account_id)
                file_info_json = restapi.sync_file(pan_acc.access_token, [fs_id], False)
                if file_info_json:
                    find_item = False
                    for sync_item in file_info_json:
                        if sync_item['fs_id'] == fs_id:
                            find_item = True
                            origin_filename = sync_item['filename']
                            if origin_filename != old_name:
                                origin_path = sync_item['path']
                                _jsonrs = restapi.file_rename(pan_acc.access_token, origin_path, old_name)
                                err_no = _jsonrs.get("errno", None)
                                if 'info' in _jsonrs and not err_no:
                                    info_list = _jsonrs['info']
                                    # print("rename info_list:", info_list)
                                    if origin_path != data_item.path:
                                        params["path"] = origin_path
                                    DataDao.update_data_item(data_item.id, params)
                                else:
                                    err_msg = _jsonrs.get("errmsg", "")
                                    result['state'] = -1
                                    result['err'] = err_msg
                                    return result
                            else:
                                DataDao.update_data_item(data_item.id, params)
                    if not find_item:
                        result['state'] = -2
                        result['errmsg'] = "not find file in NetDisk,[{}]".format(data_item.filename)
                        return result
                else:
                    result['state'] = -2
                    result['err'] = "not find file in NetDisk,[{}]".format(data_item.filename)
                    return result
            return result

    def check_sync_state(self, pan_id, user_id):
        rs_key = "synced:pan:dir:%s_%s" % (user_id, pan_id)
        return cache_service.rm(rs_key)

    def fetch_root_item(self, pan_id):
        root_items = DataDao.get_root_item_by_pan_id(pan_id)
        if root_items:
            return root_items[0]
        return None

    def new_root_item(self, user_id, pan_id):
        return DataDao.new_root_item(user_id, pan_id)


sync_pan_service = SyncPanService()

