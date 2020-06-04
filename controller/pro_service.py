# -*- coding: utf-8 -*-
"""
Created by susy at 2020/3/7
"""
from controller.base_service import BaseService
from controller.open_service import open_service
from controller.auth_service import auth_service
from controller.async_service import async_service
from utils import singleton, log, guess_file_type
from dao.client_data_dao import ClientDataDao
from dao.product_dao import ProductDao
from dao.mdao import DataDao
from dao.auth_dao import AuthDao
from utils import restapi, obfuscate_id, is_image_media, get_now_datetime, log as logger
from utils.utils_es import SearchParams, build_query_item_es_body
from dao.es_dao import es_dao_share, es_dao_local
from dao.models import Product, Accounts, BASE_FIELDS, Assets, ShareLogs, DataItem, ClientDataItem, TransferLogs, PanAccounts
from utils.constant import TOP_DIR_FILE_NAME, SHARE_ES_TOP_POS, PRODUCT_TAG, LOGIC_ERR_TXT, DLINK_TIMEOUT
from utils import scale_size, decrypt_user_id, decrypt_id
from cfg import PAN_ROOT_DIR
import arrow
import sys
import time
sys.setrecursionlimit(1000000)


@singleton
class ProductService(BaseService):

    def tag_product(self, ref_id, itemid, layer, p_price) -> Product:
        es_rs = es_dao_local().es_get(itemid, {"_source": ",".join(['isdir', 'fs_id', 'size', 'account', 'tags',
                                                                    'filename', 'parent', 'sourceid'])})
        logger.info("es_rs:{},layer:{},price:{}".format(es_rs, layer, p_price))
        if es_rs and "_source" in es_rs:
            source = es_rs["_source"]
            isdir = source["isdir"]
            size = source["size"]
            # format_size = scale_size(size)
            tags = source["tags"]
            if not tags:
                tags = []
            if PRODUCT_TAG not in tags:
                tags.append(PRODUCT_TAG)
                es_dao_local().update_field(itemid, 'tags', tags)
            pro: Product = ProductDao.product_by_pro_no(itemid)
            if not pro:
                pro = ProductDao.new_product(itemid, ref_id, {'isdir': isdir, 'name': source['filename'],
                                                              'fs_id': source['fs_id'], 'size': size,
                                                              'price': int(p_price * 100)})
            else:
                ProductDao.update_product(itemid, {'pin': 0, 'price': int(p_price * 100)})
            return pro

    def un_tag_product(self, itemid):
        es_rs = es_dao_local().es_get(itemid, {"_source": ",".join(['isdir', 'fs_id', 'size', 'account', 'tags',
                                                                    'filename', 'parent', 'sourceid'])})
        if es_rs and "_source" in es_rs:
            source = es_rs["_source"]
            tags = source["tags"]
            if PRODUCT_TAG in tags:
                tags.remove(PRODUCT_TAG)
                es_dao_local().update_field(itemid, 'tags', tags)
            ProductDao.update_product(itemid, {'pin': 1})

    def buy_product(self, itemid, fuzzy_id):
        pro: Product = ProductDao.product_by_pro_no(itemid)
        if pro:
            user_id = decrypt_user_id(fuzzy_id)
            acc_auth = AuthDao.query_account_auth(user_id)
            if acc_auth:
                a = ProductDao.new_order_assets(acc_auth, pro)
                return a
        return None

    def user_list(self, kw, size, offset):
        items = DataDao.query_user_list_by_keyword(kw, offset=offset, limit=size)
        item_json_list = []
        # print("items:", items)
        for item in items:
            item_json_list.append(Accounts.to_dict(item, BASE_FIELDS + ['id']))
        return item_json_list

    def search_assets(self, user_ref_id, page, total):
        size = 15
        offset = int(page) * size
        if page == 0:
            total = ProductDao.query_assets_count_by_ref_id(user_ref_id)
        assets_list = ProductDao.query_assets_by_ref_id(user_ref_id, offset=offset, limit=size)
        datas = []
        for assets in assets_list:
            datas.append(Assets.to_dict(assets, ["id"]))
        has_next = offset + size < total
        rs = {"data": datas, "has_next": has_next, "total": total, "pagesize": size}
        return rs

    def check_file_authorized(self, user_ref_id, item_id, pids, tag):
        st = 0
        p_fuzzy_id_list = pids.split(",")
        logger.info("p_fuzzy_id_list:{}".format(p_fuzzy_id_list))

        def check_mid_parent(perent_item_id):
            pos = len(p_fuzzy_id_list) - 1
            check_pass = True
            while pos > 0:
                pos = pos - 1
                _item_id = decrypt_id(p_fuzzy_id_list[pos])
                if DataDao.check_data_item_exists_by_parent(_item_id, perent_item_id):
                    perent_item_id = _item_id
                else:
                    check_pass = False
                    break
            return check_pass, perent_item_id

        if "asset" == tag:
            asset_fuzzy_id = p_fuzzy_id_list[-1]
            asset_id = int(decrypt_id(asset_fuzzy_id))
            assets: Assets = ProductDao.fetch_assets_by_ref_id_assets_id(user_ref_id, asset_id)
            if assets and assets.pro_no:
                p_item_id = decrypt_id(assets.pro_no)
                # print("p_item_id:", p_item_id)
                check_pass, perent_item_id = check_mid_parent(p_item_id)

                if check_pass:
                    if p_item_id != item_id:
                        if not DataDao.check_data_item_exists_by_parent(item_id, perent_item_id):
                            st = -2
                else:
                    st = -2
                pass
            else:
                st = -2  # 未购买该资源
            # print("asset_fuzzy_id:", asset_fuzzy_id)
        elif "free" == tag:
            free_item_fuzzy_id = p_fuzzy_id_list[-1]
            # print("free_item_fuzzy_id:", free_item_fuzzy_id)
            free_item_id = int(decrypt_id(free_item_fuzzy_id))
            isok = DataDao.check_free_root_files_exist(str(free_item_id), "local")
            if isok:
                p_item_id = free_item_id
                check_pass, perent_item_id = check_mid_parent(p_item_id)
                if check_pass:
                    if p_item_id != item_id:
                        if not DataDao.check_data_item_exists_by_parent(item_id, perent_item_id):
                            st = -2
                else:
                    st = -2
                pass
            else:
                st = -2  # 未购买该资源
        elif "self" == tag:
            if not ClientDataDao.check_data_item_exists_by_ref_id_id(user_ref_id, item_id):
                st = -10
        else:
            st = -10
        return st

    def checkout_root_item(self, user_id, user_ref_id, default_pan_id):
        root_item: ClientDataItem = ClientDataDao.get_root_item_by_pan_id(default_pan_id)
        if not root_item:
            root_item = ClientDataDao.new_root_item(user_ref_id, default_pan_id)
        if root_item:
            top_dir_item = ClientDataDao.get_top_dir_item_by_pan_id(default_pan_id, PAN_ROOT_DIR['name'])
            if not top_dir_item:
                pan_acc: PanAccounts = auth_service.get_pan_account(default_pan_id, user_id)
                pan_acc = auth_service.check_pan_token_validation(pan_acc)
                jsonrs = restapi.pan_mkdir(pan_acc.access_token, "/%s" % PAN_ROOT_DIR['name'])

                if 'fs_id' in jsonrs:
                    fs_id = jsonrs['fs_id']
                    ctime = jsonrs['ctime']
                    top_dir_item = ClientDataDao.new_top_dir_item(user_ref_id, default_pan_id, fs_id, ctime, PAN_ROOT_DIR['name'])
                elif 'category' in jsonrs and 'errno' in jsonrs:
                    jsonrs = restapi.file_search(pan_acc.access_token, key=PAN_ROOT_DIR['name'], parent_dir="/")
                    if jsonrs:
                        for finfo in jsonrs:
                            if finfo["server_filename"] == PAN_ROOT_DIR['name']:
                                top_dir_item = ClientDataDao.new_top_dir_item(user_ref_id, default_pan_id,
                                                                              finfo["fs_id"], finfo["server_ctime"],
                                                                              PAN_ROOT_DIR['name'])
                                return top_dir_item
                    return None
                else:
                    return None
            return top_dir_item
        return None

    def build_client_item_params(self, finfo, parent_id, user_ref_id, pan_acc_id, source_fs_id):
        client_item_params = None
        if "fs_id" in finfo:
            client_item_params = {
                "category": finfo["category"],
                "isdir": finfo["isdir"],
                "filename": finfo["server_filename"],
                "aliasname": finfo["server_filename"],
                "fs_id": finfo["fs_id"],
                "path": finfo["path"],
                "size": finfo["size"],
                "md5_val": finfo["md5"],
                "parent": parent_id,
                "server_ctime": finfo["server_ctime"],
                "ref_id": user_ref_id,
                "pin": 0,
                "source_fs_id": source_fs_id,
                "panacc": pan_acc_id
            }
            thumbs = finfo.get("thumbs", None)
            if thumbs:
                if "url2" in thumbs:
                    client_item_params["thumb"] = thumbs["url2"]
                elif "url1" in thumbs:
                    client_item_params["thumb"] = thumbs["url1"]
                elif "icon" in thumbs:
                    client_item_params["thumb"] = thumbs["icon"]
        return client_item_params

    def parse_query_key(self, file_path):
        key = file_path
        idx = key.rfind(".")
        if idx > 0:
            key = key[:idx]
        idx = key.rfind("/")
        if idx > 0:
            key = key[idx + 1:]
        if len(key) > 6:
            key = key[len(key) - 6:]
        return key

    def __build_client_item_simple_dict(self, client_item: ClientDataItem):
        rs = {}
        if client_item:
            name = client_item.filename
            if client_item.aliasname:
                name = client_item.aliasname
            rs['filename'] = name
            rs['fs_id'] = client_item.fs_id
            rs['source'] = client_item.source_fs_id
        return rs

    def check_file_by_key_search(self, key, parent_dir, parent_id, _md5_val, fs_id, user_ref_id, pan_acc: PanAccounts):
        jsonrs = restapi.file_search(pan_acc.access_token, key=key, parent_dir=parent_dir)
        for finfo in jsonrs:
            logger.info("check_file_by_key_search finfo:{}, target md5:{}".format(finfo, _md5_val))
            if "fs_id" in finfo:
                md5_val = finfo["md5"]
                if md5_val == _md5_val:
                    client_item_params = self.build_client_item_params(finfo, parent_id, user_ref_id,
                                                                       pan_acc.id, fs_id)
                    client_data_item = ClientDataDao.new_data_item(client_item_params)
                    # rename
                    old_name = client_data_item.filename
                    ftype = guess_file_type(old_name)
                    if not ftype:
                        idx = old_name.rfind('.')
                        if idx > 0:
                            ftype = old_name[idx + 1:]
                    new_name = "%s.%s" % (fs_id, ftype)
                    logger.info("old name:{}, new_name:{}".format(old_name, new_name))
                    _jsonrs = restapi.file_rename(pan_acc.access_token, client_data_item.path, new_name)
                    if 'info' in _jsonrs:
                        info_list = _jsonrs['info']
                        # print("rename info_list:", info_list)
                        new_path = "%s/%s" % (parent_dir, new_name)
                        # jsonrs = restapi.file_search(pan_acc.access_token, key=fs_id, parent_dir=parent_dir)
                        # print("search new file jsonrs:", jsonrs)
                        ClientDataDao.update_client_item(client_data_item.id, {"path": new_path, "filename": new_name, "pin": 1})
                        client_data_item.path = new_path
                        client_data_item.filename = new_name
                        client_data_item.pin = 1
                    return client_data_item
        return None

    def copy_to_my_pan(self, user_id, user_ref_id, share_log: ShareLogs, default_pan_id):
        fs_id = share_log.fs_id
        key_prefix = "client:ready:"
        # 文件已迁出,等待迁入
        async_service.update_state(key_prefix, user_id, {"state": 0, "pos": 1})
        top_dir_item = self.checkout_root_item(user_id, user_ref_id, default_pan_id)
        if not top_dir_item:
            return -3, None  # 无法创建顶级目录
        pan_acc: PanAccounts = auth_service.get_pan_account(default_pan_id, user_id)
        if not pan_acc:
            logger.error("PanAccount not exists![{}],user_id:{}".format(default_pan_id, user_id))
            return -3, None
        pan_acc = auth_service.check_pan_token_validation(pan_acc)
        # 目录结构构建
        async_service.update_state(key_prefix, user_id, {"state": 0, "pos": 2})

        find_pan_file = False
        client_item_params = {}
        jsonrs = restapi.file_search(pan_acc.access_token, key=fs_id, parent_dir=top_dir_item.path)
        if jsonrs:
            for finfo in jsonrs:
                if "fs_id" in finfo:
                    md5_val = finfo["md5"]
                    if md5_val == share_log.md5_val:
                        find_pan_file = True
                        client_item_params = self.build_client_item_params(finfo, top_dir_item.id, user_ref_id,
                                                                           pan_acc.id, fs_id)
                        break
        if find_pan_file:
            client_data_item = ClientDataDao.new_data_item(client_item_params)
            return 0, client_data_item
        # print("target pan acc id:", pan_acc.id)

        jsonrs = restapi.transfer_share_files(pan_acc.access_token, share_id=share_log.share_id,
                                              from_uk=share_log.uk, randsk=share_log.randsk,
                                              fs_id=share_log.fs_id, path=top_dir_item.path)
        if "extra" in jsonrs and "list" in jsonrs["extra"]:
            file_path = jsonrs["extra"]["list"][0]["to"]
            key = self.parse_query_key(file_path)
            # 迁出后, 获取信息
            async_service.update_state(key_prefix, user_id, {"state": 0, "pos": 3})
            time.sleep(3)
            client_data_item = self.check_file_by_key_search(key, top_dir_item.path, top_dir_item.id, share_log.md5_val, fs_id, user_ref_id, pan_acc)
            if client_data_item:
                return 0, client_data_item
            return -4, None  # 无法转存文件
        elif jsonrs.get('errno', 0) == -30 and 'path' in jsonrs:
            logger.info("exists jsonrs:{}".format(jsonrs))
            file_path = jsonrs.get('path', None)
            if file_path:
                # 迁出后, 获取信息
                async_service.update_state(key_prefix, user_id, {"state": 0, "pos": 3})
                key = self.parse_query_key(file_path)
                client_data_item = self.check_file_by_key_search(key, top_dir_item.path, top_dir_item.id,
                                                                 share_log.md5_val, fs_id, user_ref_id, pan_acc)
                if client_data_item:
                    return 0, client_data_item
            return -4, None  # 无法转存文件
        elif "errno" in jsonrs:
            return -4, None  # 无法转存文件

    def check_copy_file(self, user_id, user_ref_id, default_pan_id, item_id, pids, tag):
        ctx = self
        key_prefix = "client:ready:"
        if not default_pan_id:
            pan_acc = auth_service.default_pan_account(user_id)
            if pan_acc:
                default_pan_id = pan_acc.id
        if not default_pan_id:
            return {"state": -2, "err": LOGIC_ERR_TXT['need_pann_acc']}

        def final_do():
            pass

        def to_do(key, rs_key):
            _result = {'state': 0}
            data_item: DataItem = DataDao.get_data_item_by_id(item_id)
            _client_data_item: ClientDataItem = ClientDataDao.get_data_item_by_source_fs_id(data_item.fs_id, user_ref_id)
            if _client_data_item:
                if _client_data_item.pin == 0:
                    pan_acc: PanAccounts = auth_service.get_pan_account(default_pan_id, user_id)
                    pan_acc = auth_service.check_pan_token_validation(pan_acc)
                    # 文件已迁出,等待迁入, 目录结构已存在
                    async_service.update_state(key_prefix, user_id, {"state": 0, "pos": 2})
                    old_name = _client_data_item.filename
                    ftype = guess_file_type(old_name)
                    if not ftype:
                        idx = old_name.rfind('.')
                        if idx > 0:
                            ftype = old_name[idx + 1:]
                    new_name = "%s.%s" % (_client_data_item.source_fs_id, ftype)
                    parent_dir = "/%s" % PAN_ROOT_DIR['name']
                    new_path = "%s/%s" % (parent_dir, new_name)
                    _jsonrs = restapi.file_rename(pan_acc.access_token, _client_data_item.path, new_name)
                    # jsonrs = restapi.file_search(pan_acc.access_token, key=fs_id, parent_dir=parent_dir)
                    # print("search new file jsonrs:", jsonrs)
                    if "errno" in _jsonrs and _jsonrs["errno"] == 0:
                        _client_data_item.path = new_path
                        _client_data_item.filename = new_name
                        _client_data_item.pin = 1
                        ClientDataDao.update_client_item(_client_data_item.id,
                                                         {"path": new_path, "filename": new_name, "pin": 1})
                        _result['state'] = 0
                        _result['item'] = ctx.__build_client_item_simple_dict(_client_data_item)
                        _result['item']['id'] = obfuscate_id(_client_data_item.id)
                        _result['pos'] = 4
                    else:
                        _result['state'] = -4
                        _result["err"] = LOGIC_ERR_TXT['rename_fail']
                else:
                    _result['state'] = 0
                    _result['item'] = ctx.__build_client_item_simple_dict(_client_data_item)
                    _result['item']['id'] = obfuscate_id(_client_data_item.id)
                    _result['pos'] = 4
            else:
                _rs, share_log = open_service.build_shared_log(data_item)
                if not share_log:
                    if 'state' in _rs:
                        _result['state'] = _rs['state']
                    if 'err' in _rs:
                        _result['state'] = -9
                        _result['err'] = _rs['err']
                else:
                    # copy
                    if share_log.is_black == 1:
                        _result['state'] = -9
                        _result['err'] = share_log.err
                    else:
                        _st, _client_data_item = self.copy_to_my_pan(user_id, user_ref_id, share_log, default_pan_id)
                        _result['state'] = _st
                        if _st < 0:
                            if _st == -3:
                                _result['err'] = LOGIC_ERR_TXT['mk_top_fail']
                            elif _st == -4:
                                _result['err'] = LOGIC_ERR_TXT['rename_fail']
                        if _client_data_item:
                            _result['item'] = ctx.__build_client_item_simple_dict(_client_data_item)
                            _result['item']['id'] = obfuscate_id(_client_data_item.id)
                            _result['pos'] = 4
            return _result

        st = self.check_file_authorized(user_ref_id, item_id, pids, tag)
        result = {'state': 0}
        if st == 0:
            if "self" == tag:
                client_data_item: ClientDataItem = ClientDataDao.get_data_item_by_id(item_id, user_ref_id)
                if client_data_item:
                    result['state'] = 0
                    result['item'] = ctx.__build_client_item_simple_dict(client_data_item)
                    result['item']['id'] = obfuscate_id(client_data_item.id)
                    result['pos'] = 4
                    return result
                else:
                    # 找不到文件 search
                    return {"state": -5, "err": LOGIC_ERR_TXT['not_exists']}
            else:
                async_service.init_state(key_prefix, user_id, {"state": 0, "pos": 0})
                async_rs = async_service.async_checkout_client_item(key_prefix, user_id, to_do, final_do)
                if async_rs['state'] == 'block':
                    result['state'] = -11
                    result['err'] = LOGIC_ERR_TXT['sys_lvl_down']
        else:
            err_msg = LOGIC_ERR_TXT['unknown']
            if -10 == st:
                err_msg = LOGIC_ERR_TXT['ill_data']
            elif -2 == st:
                err_msg = LOGIC_ERR_TXT['need_access']
            result = {"state": st, "err": err_msg}

        return result

    def check_transfer_file(self, user_id, user_ref_id, default_pan_id, item_id, pids, tag):
        ctx = self
        key_prefix = "client:ready:"
        if not default_pan_id:
            pan_acc = auth_service.default_pan_account(user_id)
            if pan_acc:
                default_pan_id = pan_acc.id
        if not default_pan_id:
            return {"state": -2, "err": LOGIC_ERR_TXT['need_pann_acc']}

        def final_do():
            pass

        def to_do(key, rs_key):
            _result = {'state': 0}
            data_item: DataItem = DataDao.get_data_item_by_id(item_id)
            _rs, share_log = open_service.build_shared_log(data_item)
            if not share_log:
                if 'state' in _rs:
                    _result['state'] = _rs['state']
                if 'err' in _rs:
                    _result['state'] = -9
                    _result['err'] = _rs['err']
            else:
                if share_log.is_black == 1:
                    _result['state'] = -9
                    _result['err'] = share_log.err
                else:
                    _result['item'] = {"link": share_log.link, "pass": share_log.password}
                    _result['pos'] = 1
            # copy

            return _result

        st = self.check_file_authorized(user_ref_id, item_id, pids, tag)
        result = {'state': 0}
        if st == 0:
            if "self" == tag:
                # 找不到文件 search
                return {"state": -5, "err": LOGIC_ERR_TXT['not_exists']}
            else:
                async_service.init_state(key_prefix, user_id, {"state": 0, "pos": 0})
                async_rs = async_service.async_checkout_client_item(key_prefix, user_id, to_do, final_do)
                if async_rs['state'] == 'block':
                    result['state'] = -11
                    result['err'] = LOGIC_ERR_TXT['sys_lvl_down']
        else:
            err_msg = LOGIC_ERR_TXT['unknown']
            if -10 == st:
                err_msg = LOGIC_ERR_TXT['ill_data']
            elif -2 == st:
                err_msg = LOGIC_ERR_TXT['need_access']
            result = {"state": st, "err": err_msg}
        return result

    def checkout_dlink(self, item_id, user_id, user_ref_id):
        _client_data_item: ClientDataItem = ClientDataDao.get_data_item_by_id(item_id, user_ref_id)
        need_sync = False
        if not _client_data_item.dlink_updated_at or not _client_data_item.dlink:
            need_sync = True
        elif _client_data_item.dlink_updated_at:
            dt = arrow.get(_client_data_item.dlink_updated_at).replace(tzinfo=self.default_tz)
            if dt.shift(hours=+DLINK_TIMEOUT) < arrow.now():
                need_sync = True
        need_thumbs = False
        if is_image_media(_client_data_item.filename) and _client_data_item.category == 3:
            need_thumbs = True

        if need_sync:
            pan_id = _client_data_item.panacc
            pan_acc: PanAccounts = auth_service.get_pan_account(pan_id, user_id)
            # sync_list = restapi.sync_file(self.pan_acc.access_token, [int(data_item.fs_id)])
            sync_dlink, thumbs = restapi.get_dlink_by_sync_file(pan_acc.access_token, int(_client_data_item.fs_id),
                                                                need_thumbs)
            if sync_dlink:
                _client_data_item.dlink = "{}&access_token={}".format(sync_dlink, pan_acc.access_token)
                _client_data_item.dlink_updated_at = get_now_datetime()
                data_item_params = {"dlink": _client_data_item.dlink, "dlink_updated_at": _client_data_item.dlink_updated_at}
                if need_thumbs:
                    if "url2" in thumbs:
                        data_item_params["thumb"] = thumbs["url2"]
                        _client_data_item.thumb = data_item_params["thumb"]
                    elif "url1" in thumbs:
                        data_item_params["thumb"] = thumbs["url1"]
                        _client_data_item.thumb = data_item_params["thumb"]
                    elif "icon" in thumbs:
                        data_item_params["thumb"] = thumbs["icon"]
                        _client_data_item.thumb = data_item_params["thumb"]
                ClientDataDao.update_client_item(_client_data_item.id, data_item_params)
        expired_at = arrow.get(_client_data_item.dlink_updated_at).replace(tzinfo=self.default_tz).shift(
            hours=+DLINK_TIMEOUT).datetime
        loader = {
            'id': 0,
            'created_at': _client_data_item.created_at,
            'updated_at': _client_data_item.updated_at,
            'fs_id': _client_data_item.fs_id,
            'md5_val': _client_data_item.md5_val,
            'path': _client_data_item.path,
            'size': _client_data_item.size,
            'category': _client_data_item.category,
            'pin': _client_data_item.pin,
            'dlink': _client_data_item.dlink,
            'filename': _client_data_item.filename,
            'expired_at': expired_at
        }
        return [loader]

    def test_async_task(self, user_id, default_pan_id):
        import time
        import random
        key_prefix = "client:ready:"
        if not default_pan_id:
            pan_acc = auth_service.default_pan_account(user_id)
            if pan_acc:
                default_pan_id = pan_acc.id
        if not default_pan_id:
            return {"state": -2, "err": LOGIC_ERR_TXT['need_pann_acc']}

        def final_do():
            pass

        def to_do(key, rs_key):
            _result = {'state': 0}
            time.sleep(random.randint(1, 10))
            # 文件已迁出,等待迁入
            async_service.update_state(key_prefix, user_id, {"state": 0, "pos": 1})
            time.sleep(random.randint(1, 10))
            # 文件已迁出,等待迁入, 目录结构已存在
            async_service.update_state(key_prefix, user_id, {"state": 0, "pos": 2})
            rv = random.randint(1, 10)
            # print("rv:", rv)
            test_err = rv <= 6
            if test_err:
                _result['err'] = LOGIC_ERR_TXT['rename_fail']
                _result['state'] = -4
            else:
                time.sleep(random.randint(1, 10))
                # 迁出后, 获取信息
                async_service.update_state(key_prefix, user_id, {"state": 0, "pos": 3})
                _result['item'] = {}
                _result['item']['id'] = 'a'
                _result['pos'] = 4
            time.sleep(random.randint(1, 10))
            return _result

        result = {'state': 0, 'pos': 0}
        async_service.init_state(key_prefix, user_id, {"state": 0, "pos": 0})
        async_rs = async_service.async_checkout_client_item(key_prefix, user_id, to_do, final_do)
        if async_rs['state'] == 'block':
            result['state'] = -11
            result['err'] = LOGIC_ERR_TXT['sys_lvl_down']

        return result

    def __rm_data_item(self, user_id, user_ref_id, default_pan_id, item_id):
        if not default_pan_id:
            pan_acc = auth_service.default_pan_account(user_id)
            if pan_acc:
                default_pan_id = pan_acc.id
        if not default_pan_id:
            return {"state": -2, "err": LOGIC_ERR_TXT['need_pann_acc']}

        _client_data_item: ClientDataItem = ClientDataDao.get_data_item_by_id(item_id, user_ref_id)
        if _client_data_item:
            pan_acc: PanAccounts = auth_service.get_pan_account(default_pan_id, user_id)
            if not pan_acc:
                logger.error("PanAccount not exists![{}],user_id:{}".format(default_pan_id, user_id))
                return {"state": -2, "err": LOGIC_ERR_TXT['need_pann_acc']}
            jsonrs = restapi.del_file(pan_acc.access_token, _client_data_item.path)
            if "errno" in jsonrs and jsonrs["errno"]:
                errmsg = jsonrs.get("errmsg", "")
                if not errmsg:
                    errmsg = "clear failed!"
                return {"state": -1, "errmsg": errmsg}
            else:
                ClientDataDao.del_data_item_by_id(_client_data_item.id)
                return {"state": 0}
        else:
            return {"state": -3, "err": LOGIC_ERR_TXT['not_exists']}

    def rm(self, user_id, user_ref_id, default_pan_id, item_id, source):
        rs = {"state": 0}
        if "self" == source:
            rs = self.__rm_data_item( user_id, user_ref_id, default_pan_id, item_id)
        else:
            rs["state"] = -1
            rs["errmsg"] = "parameters error!"

        return rs


product_service = ProductService()
