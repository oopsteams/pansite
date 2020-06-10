# -*- coding: utf-8 -*-
"""
Created by susy at 2019/11/2
"""
import requests
from dao.mdao import DataDao
from dao.client_data_dao import ClientDataDao
from dao.models import Accounts, PanAccounts, ShareLogs, DataItem, TransferLogs, CommunityDataItem, ClientDataItem, \
    AccountExt
from utils import singleton, log, make_token, obfuscate_id, get_now_datetime, random_password, get_now_ts, restapi, \
    guess_file_type, constant, split_filename
from utils.utils_es import SearchParams, build_query_item_es_body
from utils import get_payload_from_token, is_video_media, is_image_media, is_plain_media, scale_size, log as logger
from dao.es_dao import es_dao_share, es_dao_local
import arrow
from cfg import PAN_SERVICE, get_bd_auth_uri, PAN_ROOT_DIR
from controller.base_service import BaseService
from controller.auth_service import auth_service
import time
LOGIN_TOKEN_TIMEOUT = constant.LOGIN_TOKEN_TIMEOUT
PAN_ACCESS_TOKEN_TIMEOUT = constant.PAN_ACCESS_TOKEN_TIMEOUT
DLINK_TIMEOUT = constant.DLINK_TIMEOUT
# PAN_ACC_CACHE_TIMEOUT = 24 * 60 * 60
ACCOUNT_PAN_ACC_CACHE_CNT = 5
MAX_RESULT_WINDOW = 10000


@singleton
class PanService(BaseService):
    PAN_ACC_CACHE = {}
    PAN_ACC_CACHE_LAST_TIME = 0
    TMP_PATH = "/__tmp"
    TMP_MANUAL_PATH = "/__tmp/manual"
    auth_point = "{}://{}".format(PAN_SERVICE['protocol'], PAN_SERVICE['auth_domain'])
    client_id = PAN_SERVICE['client_id']
    client_secret = PAN_SERVICE['client_secret']
    pan_auth = get_bd_auth_uri()

    def check_data_item_media_type(self, category, filename):
        media_type = ""
        if is_plain_media(filename):
            media_type = "plain"
        if category == 1 and is_video_media(filename):
            media_type = "video"
        if is_image_media(filename):
            media_type = "image"
        if category == 2:
            media_type = "audio"
        return media_type

    def pan_accounts_dict(self) -> list:
        pan_acc_list = DataDao.pan_account_list()
        rs = []
        for acc in pan_acc_list:
            rs.append(PanAccounts.to_dict(acc))
        return rs

    def load_pan_acc_list_by_user(self, user_id):
        acc: Accounts = DataDao.account_by_id(user_id)
        pan_acc_list = DataDao.pan_account_list(user_id)
        l = len(pan_acc_list)
        result = {}
        need_renew_pan_acc = []
        for pan_acc in pan_acc_list:
            if pan_acc.client_id != self.client_id or pan_acc.client_secret != self.client_secret:
                need_renew_access_token = True
                need_renew_pan_acc.append({"id": pan_acc.id, "name": pan_acc.name, "use_cnt": pan_acc.use_count,
                                           "refresh": False, 'auth': self.pan_auth})
            elif pan_acc.access_token and pan_acc.token_updated_at:
                tud = arrow.get(pan_acc.token_updated_at).replace(tzinfo=self.default_tz)
                if (arrow.now(self.default_tz) - tud).total_seconds() > PAN_ACCESS_TOKEN_TIMEOUT:
                    need_renew_access_token = True
                    need_renew_pan_acc.append({"id": pan_acc.id, "name": pan_acc.name, "use_cnt": pan_acc.use_count,
                                               "refresh": True, 'auth': self.pan_auth})
            else:
                need_renew_access_token = True
                need_renew_pan_acc.append({"id": pan_acc.id, "name": pan_acc.name, "use_cnt": pan_acc.use_count,
                                           "refresh": True, 'auth': self.pan_auth})
        return need_renew_pan_acc

    def all_pan_acc_list_by_user(self, user_id):
        # acc: Accounts = DataDao.account_by_id(user_id)
        pan_acc_list = DataDao.pan_account_list(user_id)
        need_renew_pan_acc = []
        for pan_acc in pan_acc_list:
            need_renew_pan_acc.append({"id": pan_acc.id, "name": pan_acc.name, "use_cnt": pan_acc.use_count,
                                       "refresh": True, 'auth': self.pan_auth})
        return need_renew_pan_acc

    def check_user(self, user_name, user_passwd):
        acc: Accounts = DataDao.account_by_passwd(user_name, user_passwd)
        return auth_service.login_check_user(acc)

    # def _check_user(self, acc: Accounts):
    #     need_renew_pan_acc = []
    #     if acc:
    #         pan_acc_list = DataDao.pan_account_list(acc.id)
    #         # pan_acc: PanAccounts = DataDao.pan_account_list(acc.id)
    #         need_renew_access_token = False
    #         l = len(pan_acc_list)
    #         for pan_acc in pan_acc_list:
    #             if pan_acc.client_id != self.client_id or pan_acc.client_secret != self.client_secret:
    #                 need_renew_access_token = True
    #                 need_renew_pan_acc.append({"id": pan_acc.id, "name": pan_acc.name, "use_cnt": pan_acc.use_count,
    #                                            "refresh": False, 'auth': self.pan_auth})
    #             elif pan_acc.access_token and pan_acc.token_updated_at:
    #                 tud = arrow.get(pan_acc.token_updated_at).replace(tzinfo=self.default_tz)
    #                 if (arrow.now(self.default_tz) - tud).total_seconds() > PAN_ACCESS_TOKEN_TIMEOUT:
    #                     need_renew_access_token = True
    #                     need_renew_pan_acc.append({"id": pan_acc.id, "name": pan_acc.name, "use_cnt": pan_acc.use_count,
    #                                                "refresh": True, 'auth': self.pan_auth})
    #             else:
    #                 need_renew_access_token = True
    #                 need_renew_pan_acc.append({"id": pan_acc.id, "name": pan_acc.name, "use_cnt": pan_acc.use_count,
    #                                            "refresh": True, 'auth': self.pan_auth})
    #         if l == 0:
    #             need_renew_access_token = True
    #         # if pan_acc and pan_acc['access_token'] and pan_acc['token_updated_at']:
    #         #     tud = arrow.get(pan_acc['token_updated_at']).replace(tzinfo=self.default_tz)
    #         #     if (arrow.now(self.default_tz) - tud).total_seconds() < PAN_ACCESS_TOKEN_TIMEOUT:
    #         #         need_renew_access_token = False
    #
    #         lud = arrow.get(acc.login_updated_at).replace(tzinfo=self.default_tz)
    #         diff = arrow.now(self.default_tz) - lud
    #         params = {}
    #         if diff.total_seconds() > LOGIN_TOKEN_TIMEOUT or not acc.login_token:
    #             if not acc.fuzzy_id:
    #                 acc.fuzzy_id = obfuscate_id(acc.id)
    #                 params["fuzzy_id"] = acc.fuzzy_id
    #             # login_token = make_token(acc.fuzzy_id)
    #             login_token, _ = auth_service.build_user_payload(acc)
    #             acc.login_token = login_token
    #             params["login_token"] = login_token
    #             lud = params["login_updated_at"] = get_now_datetime()
    #             DataDao.update_account_by_pk(acc.id, params=params)
    #         else:
    #             tk = acc.login_token
    #             if tk:
    #                 user_payload = get_payload_from_token(tk)
    #                 if user_payload:
    #                     tm = user_payload['tm']
    #                     ctm = get_now_ts()
    #                     if ctm - tm > LOGIN_TOKEN_TIMEOUT:
    #                         # login_token = make_token(acc.fuzzy_id)
    #                         login_token, _ = auth_service.build_user_payload(acc)
    #                         acc.login_token = login_token
    #                         params["login_token"] = login_token
    #                         lud = params["login_updated_at"] = get_now_datetime()
    #                         DataDao.update_account_by_pk(acc.id, params=params)
    #         log.debug("login_token:{}".format(acc.login_token))
    #         result = {"need_renew_access_token": need_renew_access_token}
    #         if need_renew_access_token:
    #             result['auth'] = self.pan_auth
    #         result['token'] = acc.login_token
    #         result['login_at'] = int(arrow.get(lud).timestamp * 1000)
    #         # print('login_at:', result['login_at'])
    #         result['pan_acc_list'] = need_renew_pan_acc
    #         account_ext = DataDao.account_ext_by_acc_id(acc.id)
    #         result['username'] = account_ext.username
    #         result['portrait'] = account_ext.portrait
    #         result['id'] = acc.fuzzy_id
    #         return result
    #
    #     return None

    def save_user(self, mobile_no, passwd):
        acc: Accounts = DataDao.account_by_name(mobile_no)
        if acc:
            return None, None, "exist"
        else:
            user_token, user_ext_dict = DataDao.new_account(mobile_no, passwd, get_now_datetime(),
                                                            lambda account: auth_service.build_user_payload(account))
            fuzzy_id = user_ext_dict['id']
            return user_token, fuzzy_id, None

    def get_pan_user_access_token(self, user_id, code, pan_name, can_refresh=True):
        # access_token = ""
        pan_url = '{}token'.format(self.auth_point)
        # _pan_acc: PanAccounts = DataDao.pan_account_list(user_id)
        _pan_acc = DataDao.pan_account_by_name(user_id, pan_name)
        # pan_acc = DataDao.pan_account_list(user_id, transfer_to_dict=False)
        pan_acc_id = 0
        pan_acc_not_exist = False
        can_refresh_token = False
        if not _pan_acc:
            pan_acc_not_exist = True
        else:
            pan_acc_id = _pan_acc.id
            if can_refresh and _pan_acc.refresh_token:
                can_refresh_token = True
        now = arrow.now(self.default_tz)
        logger.info("pan_acc_not_exist:{}, can_refresh_token:{}".format(pan_acc_not_exist, can_refresh_token))
        if pan_acc_not_exist or not can_refresh_token:
            # params = {'grant_type': 'authorization_code', 'client_id': PAN_SERVICE["client_id"],
            #           'code': code,
            #           'redirect_uri': 'oob',
            #           'client_secret': PAN_SERVICE["client_secret"]}
            # print("query access_token pan_url:", pan_url)
            # rs = requests.get(pan_url, params=params)
            # print(rs.content)
            # jsonrs = rs.json()
            jsonrs = restapi.access_token_code(code)
            access_token = jsonrs["access_token"]
            refresh_token = jsonrs["refresh_token"]
            expires_in = jsonrs["expires_in"]  # seconds
            expires_at = now.shift(seconds=+expires_in).datetime
            account_ext: AccountExt = self.sync_pan_user_info(access_token, user_id)
            if pan_acc_not_exist:
                # print("will new pan account")
                account_ext_id = 0
                if account_ext:
                    account_ext_id = account_ext.user_id
                pan_acc_id = DataDao.new_pan_account(user_id, pan_name, self.client_id, self.client_secret,
                                                     access_token, refresh_token, expires_at, get_now_datetime(), pin=1,
                                                     bd_uid=account_ext_id)
            else:
                # print("will update pan account")
                DataDao.update_pan_account_by_pk(pan_acc_id, {"access_token": access_token, 'name': pan_name,
                                                              'client_id': self.client_id,
                                                              'client_secret': self.client_secret,
                                                              "refresh_token": refresh_token, "expires_at": expires_at,
                                                              "token_updated_at": get_now_datetime()})
        else:
            params = {'grant_type': 'refresh_token', 'client_id': self.client_id,
                      'refresh_token': _pan_acc.refresh_token, 'client_secret': self.client_secret}
            print("query refresh_token pan_url:", pan_url)
            rs = requests.get(pan_url, params=params)
            print(rs.content)
            jsonrs = rs.json()
            access_token = jsonrs["access_token"]
            refresh_token = jsonrs["refresh_token"]
            expires_in = jsonrs["expires_in"]  # seconds
            expires_at = now.shift(seconds=+expires_in).datetime
            DataDao.update_pan_account_by_pk(pan_acc_id, {"access_token": access_token, "refresh_token": refresh_token,
                                                          "expires_at": expires_at,
                                                          "token_updated_at": get_now_datetime()})
            self.sync_pan_user_info(access_token, user_id)
        return access_token, pan_acc_id, None

    def sync_pan_user_info(self, access_token, account_id):
        return auth_service.sync_pan_user_info(access_token, account_id)

    def fresh_token(self, pan_id):
        auth_service.fresh_token(pan_id)

    def query_file(self, item_id):
        data_item: DataItem = DataDao.get_data_item_by_id(item_id)
        need_sync = False
        logger.info("query_file dlink:{}".format(data_item.dlink))
        if not data_item.dlink_updated_at or not data_item.dlink:
            need_sync = True
        elif data_item.dlink_updated_at:
            dt = arrow.get(data_item.dlink_updated_at).replace(tzinfo=self.default_tz)
            if dt.shift(hours=+DLINK_TIMEOUT) < arrow.now():
                need_sync = True
        account_id = data_item.account_id
        acc: Accounts = DataDao.account_by_id(account_id)
        flv_json = None
        need_thumbs = False
        # data_item_ext = None
        # if data_item.category == 1 and is_video_media(data_item.filename):
        #     data_item_ext = DataDao.get_data_item_ext_by_id(data_item.id)
        if is_image_media(data_item.filename) and data_item.category == 3:
            need_thumbs = True
        if need_sync:
            pan_acc: PanAccounts = self.get_pan_account(data_item.panacc, data_item.account_id)
            # sync_list = restapi.sync_file(self.pan_acc.access_token, [int(data_item.fs_id)])
            sync_dlink, thumbs = restapi.get_dlink_by_sync_file(pan_acc.access_token, int(data_item.fs_id), need_thumbs)
            if sync_dlink:
                data_item.dlink = "{}&access_token={}".format(sync_dlink, pan_acc.access_token)
                data_item.dlink_updated_at = get_now_datetime()
                data_item_params = {"dlink": data_item.dlink, "dlink_updated_at": data_item.dlink_updated_at}
                if need_thumbs:
                    if "url3" in thumbs:
                        data_item_params["thumb"] = thumbs["url3"]
                        data_item.thumb = data_item_params["thumb"]
                    elif "url2" in thumbs:
                        data_item_params["thumb"] = thumbs["url2"]
                        data_item.thumb = data_item_params["thumb"]
                    elif "url1" in thumbs:
                        data_item_params["thumb"] = thumbs["url1"]
                        data_item.thumb = data_item_params["thumb"]
                    elif "icon" in thumbs:
                        data_item_params["thumb"] = thumbs["icon"]
                        data_item.thumb = data_item_params["thumb"]
                DataDao.update_data_item(data_item.id, data_item_params)
            # not authorized
            # if data_item.category == 1 and is_video_media(data_item.filename):
            #     flv_json = restapi.get_media_flv_info(pan_acc.access_token, data_item.path)
            #     if flv_json and "mlink" in flv_json:
            #         flv_params = {"fs_id": data_item.fs_id, "mlink": flv_json["mlink"],
            #                       "start_at_time": flv_json["mlink_start_at"]}
            #         if data_item_ext:
            #             data_item_ext.mlink = flv_params["mlink"]
            #             data_item_ext.start_at_time = flv_params["start_at_time"]
            #             DataDao.update_data_item_ext(data_item.id, flv_params)
            #         else:
            #             data_item_ext = DataDao.new_data_item_ext(data_item.id, flv_params)

        used_pan_acc_id = data_item.panacc
        if data_item:
            data_item.size = int(data_item.size / 1024)

        f_type = guess_file_type(data_item.filename)
        params = {"item": DataItem.to_dict(data_item, ['id', 'parent'])}
        params["item"]["id"] = obfuscate_id(data_item.id)
        params["item"]["type"] = f_type
        params["item"]["media_type"] = self.check_data_item_media_type(data_item.category, data_item.filename)
        params["item"]["dlink_tokens"] = [used_pan_acc_id]
        # if data_item.category == 1 and is_video_media(data_item.filename) and data_item_ext:
        #     params["item"]["mlink"] = data_item_ext.mlink
        #     params["item"]["start_at_time"] = data_item_ext.start_at_time
        return params

    def query_root_list(self, account_id=None):
        if account_id:
            root_item_list = DataDao.query_root_files_by_user_id(account_id)
        else:
            root_item_list = DataDao.query_free_root_files()
        params = []
        for item in root_item_list:
            item_id = item.fs_id
            if "local" == item.source:
                fuzzy_id = obfuscate_id(int(item_id))
                # print("query_root_list item_id:", item_id, ",fuzzy_id:", fuzzy_id)
                params.append({"id": fuzzy_id, "text": item.desc, "data": {"source": item.source, "_id": fuzzy_id,
                                                                           "tag": "free", "path": "#"},
                               "children": True, "icon": "folder"})
        return params

    def query_client_root_list(self, pan_id):
        # cdi: ClientDataItem = ClientDataDao.query_root_files_by_user_id(ref_id)
        params = []
        cdi: ClientDataItem = ClientDataDao.get_top_dir_item_by_pan_id(pan_id)
        if cdi:
            fuzzy_id = obfuscate_id(cdi.id)
            name = "%s(%s)" % (PAN_ROOT_DIR['alias'], cdi.source_fs_id)
            # print("query_root_list item_id:", item_id, ",fuzzy_id:", fuzzy_id)
            params.append({"id": fuzzy_id, "text": name, "data": {"source": "self", "_id": fuzzy_id,
                                                                  "tag": "self", "path": "#"},
                           "children": True, "icon": "folder"})
        return params

    def query_client_sub_list(self, parent_id, ref_id):
        cdi_list = ClientDataDao.query_client_item_list_by_parent(parent_id, ref_id)
        params = []
        if cdi_list:
            for item in cdi_list:
                item_id = item.id
                fuzzy_id = obfuscate_id(int(item_id))
                # print("query_root_list item_id:", item_id, ",fuzzy_id:", fuzzy_id)
                icon_val = "file"
                name = item.filename

                if item.aliasname:
                    name = item.aliasname
                isdir = item.isdir
                has_children = True if isdir == 1 else False
                if not has_children:
                    f_type = guess_file_type(name)
                    if f_type:
                        icon_val = "file file-%s" % f_type
                format_size = scale_size(item.size)

                params.append({"id": fuzzy_id, "text": name, "data": {"source": "self", "_id": fuzzy_id, "isdir": isdir,
                                                                      "tag": "free", "path": item.path,
                                                                      "category": item.category, "fs_id": item.fs_id,
                                                                      "format_size": format_size},
                               "children": has_children, "icon": icon_val})
        return params

    def query_shared_file_list(self, parent_id, account_id):
        params = []
        sp: SearchParams = SearchParams.build_params(0, 1000)
        sp.add_must(is_match=False, field="parent", value=parent_id)
        sp.add_must(is_match=False, field="account", value=account_id)
        es_body = build_query_item_es_body(sp)
        # es_result = es_dao_dir().es_search_exec(es_body)
        es_result = es_dao_share().es_search_exec(es_body)
        hits_rs = es_result["hits"]
        total = hits_rs["total"]
        logger.info("files es total:{}".format(total))
        for _s in hits_rs["hits"]:
            params.append({"id": _s["_source"]["fs_id"], "text": _s["_source"]["filename"],
                           "data": {"path": _s["_source"]["path"],
                                    "server_ctime": _s["_source"].get("server_ctime", 0),
                                    "isdir": _s["_source"]["isdir"], "source": "shared"}, "children": True, "icon": "folder"})
        return params

    def query_file_list(self, parent_item_id, page, size):
        offset = int(page) * size
        if offset > MAX_RESULT_WINDOW - size:
            offset = MAX_RESULT_WINDOW - size

        parent_item_fuzzy_id = obfuscate_id(parent_item_id)

        # item_list = DataDao.query_data_item_by_parent(parent_item_id, True, limit=1000)
        # params = []
        # for item in item_list:
        #     _item_path = item.path
        #     txt = item.filename
        #     if item.aliasname:
        #         txt = item.aliasname
        #     item_fuzzy_id = obfuscate_id(item.id)
        #     format_size = scale_size(item.size)
        #     # print("id:", item.id, ",item_fuzzy_id:", item_fuzzy_id)
        #     params.append({"id": item_fuzzy_id, "text": txt, "data": {"path": _item_path, "_id": item_fuzzy_id,
        #                                                               "format_size": format_size, "fs_id": item.fs_id,
        #                                                               "category": item.category, "source": "local",
        #                                                               "isdir": item.isdir},
        #                    "children": True, "icon": "folder"})
        # print("dirs total:", len(params))
        params = []
        # sp: SearchParams = SearchParams.build_params(0, 1000)
        sp: SearchParams = SearchParams.build_params(offset, size)
        # sp.add_must(is_match=False, field="path", value=parent_path)
        sp.add_must(is_match=False, field="parent", value=parent_item_id)
        # sp.add_must(is_match=False, field="isdir", value=0)
        _sort_fields = [{"isdir": {"order": "desc"}}, {"filename": {"order": "asc"}}]
        es_body = build_query_item_es_body(sp, sort_fields=_sort_fields)
        # logger.info("es_body:{}".format(es_body))
        es_result = es_dao_local().es_search_exec(es_body)
        hits_rs = es_result["hits"]
        total = hits_rs["total"]
        logger.info("files es total:{}".format(total))
        for _s in hits_rs["hits"]:
            icon_val = "file"
            fn_name = _s["_source"]["filename"]
            category = _s["_source"]["category"]
            format_size = scale_size(_s["_source"]["size"])
            media_type = self.check_data_item_media_type(category, fn_name)
            txt = fn_name
            aliasname = None
            if "aliasname" in _s["_source"] and _s["_source"]["aliasname"]:
                aliasname = _s["_source"]["aliasname"]
            if aliasname:
                fn_name, extname = split_filename(fn_name)
                alias_fn, alias_extname = split_filename(aliasname)
                if not alias_extname:
                    alias_extname = extname
                aliasname = "{}{}".format(alias_fn, "." + alias_extname if alias_extname.strip() else "")
                # __idx = fn_name.rfind(".")
                # if __idx > 0:
                #     fn_name = fn_name[0:__idx]
                txt = "[{}]{}".format(fn_name, aliasname)
            if _s["_source"]["isdir"] == 1:
                icon_val = "folder"
            else:
                f_type = guess_file_type(txt)
                if f_type:
                    icon_val = "file file-%s" % f_type
            item_fuzzy_id = obfuscate_id(_s["_source"]["id"])
            params.append({"id": item_fuzzy_id, "text": txt,
                           "data": {"path": _s["_source"]["path"], "isdir": _s["_source"]["isdir"], "source": "local",
                                    "media_type": media_type, "format_size": format_size, "category": category,
                                    "fs_id": _s["_source"]["fs_id"], "_id": item_fuzzy_id,
                                    "parent_id": parent_item_fuzzy_id, "price": 1
                                    },
                           "children": False, "icon": icon_val})
        has_next = offset + size < total
        meta = {"has_next": has_next, "total": total, "pagesize": size}
        return params, meta

    # 分享文件
    def share_folder(self, fs_id):
        data_item: DataItem = DataDao.get_data_item_by_fs_id(fs_id)
        share_log: ShareLogs = DataDao.query_shared_log_by_fs_id(fs_id)
        need_create_share_file = True
        expired_at = arrow.get(data_item.dlink_updated_at).replace(tzinfo=self.default_tz).shift(
            hours=+DLINK_TIMEOUT).datetime
        if share_log:
            jsonrs = restapi.get_share_info(share_log.share_id, share_log.special_short_url(), share_log.randsk)
            # print('"shareid" in jsonrs and "uk" in jsonrs ? ', "shareid" in jsonrs and "uk" in jsonrs)

            if jsonrs and "shareid" in jsonrs and "uk" in jsonrs:
                if data_item.dlink and not share_log.dlink:
                    pan_acc: PanAccounts = self.get_pan_account(data_item.panacc, data_item.account_id)
                    if data_item.dlink:
                        dlink = "%s&access_token=%s" % (data_item.dlink, pan_acc.access_token)
                        share_log.dlink = dlink
                        DataDao.update_share_log_by_pk(share_log.id, {'dlink': dlink})
                dict_obj = ShareLogs.to_dict(share_log)
                dict_obj['expired_at'] = expired_at
                return dict_obj, share_log, data_item
            else:
                DataDao.del_share_log_by_pk(share_log.id)
        logger.info("need_create_share_file:{}, fs_id:{}".format(need_create_share_file, fs_id))
        if need_create_share_file:
            pwd = random_password(4)
            period = 1
            pan_acc: PanAccounts = self.get_pan_account(data_item.panacc, data_item.account_id)
            dlink = None
            if data_item.dlink:
                dlink = "%s&access_token=%s" % (data_item.dlink, pan_acc.access_token)
            share_log_id, share_log = DataDao.new_share_log(fs_id, data_item.filename, data_item.md5_val, dlink, pwd, period, data_item.account_id, pan_acc.id)
            logger.info("share_log_id:{}, fs_id:{}, pan_acc_id:{}".format(share_log_id, fs_id, pan_acc.id))
            if share_log_id:
                jsonrs = restapi.share_folder(pan_acc.access_token, fs_id, pwd, period)
                logger.info("share_folder jsonrs:{}, fs_id:{}".format(jsonrs, fs_id))
                if restapi.is_black_list_error(jsonrs):
                    share_log.is_black = 1
                    err_msg = jsonrs.get('err_msg', '')
                    if "show_msg" in jsonrs:
                        err_msg = jsonrs['show_msg']
                    share_log.err = err_msg
                    DataDao.update_share_log_by_pk(share_log_id, {"is_black": share_log.is_black, "err": share_log.err})
                    dict_obj = ShareLogs.to_dict(share_log)
                    dict_obj['expired_at'] = expired_at
                    return dict_obj, share_log, data_item
                if "shareid" in jsonrs and "shorturl" in jsonrs:
                    _shareid = jsonrs["shareid"]
                    if _shareid == -1:
                        err_msg = jsonrs.get('err_msg', '')
                        share_log.is_failed = 1
                        share_log.err = err_msg
                        DataDao.update_share_log_by_pk(share_log_id,
                                                       {"is_failed": share_log.is_failed, "err": share_log.err})
                        dict_obj = ShareLogs.to_dict(share_log)
                        return dict_obj, share_log, data_item
                    else:
                        share_log.share_id = str(jsonrs["shareid"])
                        share_log.link = jsonrs["link"]
                        share_log.shorturl = jsonrs["shorturl"]
                        share_log.pin = 2
                        params = {"share_id": share_log.share_id, "link": share_log.link, "shorturl": share_log.shorturl, "pin": share_log.pin}
                        DataDao.update_share_log_by_pk(share_log_id, params)
                        jsonrs = restapi.get_share_randsk(share_log.share_id, share_log.password, share_log.common_short_url())
                        logger.info("get_share_randsk jsonrs:{}, fs_id:{}".format(jsonrs, fs_id))
                        if "randsk" in jsonrs:
                            share_log.randsk = jsonrs["randsk"]
                            jsonrs = restapi.get_share_info(share_log.share_id, share_log.special_short_url(), share_log.randsk)
                            if jsonrs and "shareid" in jsonrs and "uk" in jsonrs:
                                share_log.uk = str(jsonrs["uk"])
                                share_log.pin = 3
                                params = {"randsk": share_log.randsk, "uk": share_log.uk, "pin": share_log.pin}
                                DataDao.update_share_log_by_pk(share_log_id, params)
                                dict_obj = ShareLogs.to_dict(share_log)
                                dict_obj['expired_at'] = expired_at
                                return dict_obj, share_log, data_item

        return {}, None, data_item

    def recheck_transfer_d_link(self, transfer_log_id):
        # print("recheck_transfer_d_link transfer_log_id:", transfer_log_id)
        tl: TransferLogs = DataDao.query_transfer_logs_by_pk_id(transfer_log_id)

        if tl:
            # print("expired_at:", arrow.get(tl.expired_at).replace(tzinfo=self.default_tz), ",now:", arrow.now())
            if arrow.get(tl.expired_at).replace(tzinfo=self.default_tz) < arrow.now():
                __pan_acc = self.get_pan_account(tl.pan_account_id, tl.account_id)
                sync_dlink, thumbs = restapi.get_dlink_by_sync_file(__pan_acc.access_token, int(tl.fs_id))
                # print("sync_dlink:", sync_dlink)
                if sync_dlink:
                    # tl.dlink = sync_dlink
                    tl.dlink = "%s&access_token=%s" % (sync_dlink, __pan_acc.access_token)
                    tl.expired_at = arrow.now(self.default_tz).shift(hours=+DLINK_TIMEOUT).datetime
                    # print("new expired_at:", tl.expired_at)
                    DataDao.update_transfer_log_by_pk(tl.id, {"dlink": tl.dlink, "expired_at": tl.expired_at})
                    return TransferLogs.to_dict(tl)
            else:
                return TransferLogs.to_dict(tl)
        else:
            logger.info("[transfer_log:%s] not exists!" % transfer_log_id)
        return None

    def recheck_shared_d_link(self, shared_log_id):
        share_log: ShareLogs = DataDao.query_shared_log_by_pk_id(shared_log_id)
        if share_log:
            data_item: DataItem = DataDao.get_data_item_by_fs_id(share_log.fs_id)
            need_sync = False
            # print("query_file dlink:", data_item.dlink)
            if not data_item.dlink_updated_at or not data_item.dlink:
                need_sync = True
            elif data_item.dlink_updated_at:
                dt = arrow.get(data_item.dlink_updated_at).replace(tzinfo=self.default_tz)
                if dt.shift(hours=+DLINK_TIMEOUT) < arrow.now():
                    need_sync = True

            if need_sync:
                account_id = data_item.account_id
                acc: Accounts = DataDao.account_by_id(account_id)
                pan_acc: PanAccounts = self.get_pan_account(data_item.panacc, data_item.account_id)
                # sync_list = restapi.sync_file(self.pan_acc.access_token, [int(data_item.fs_id)])
                sync_dlink, thumbs = restapi.get_dlink_by_sync_file(pan_acc.access_token, int(data_item.fs_id))
                if sync_dlink:
                    data_item.dlink = sync_dlink
                    data_item.dlink_updated_at = get_now_datetime()
                    DataDao.update_data_item(data_item.id, {"dlink": data_item.dlink,
                                                            "dlink_updated_at": data_item.dlink_updated_at})

            share_log.dlink = data_item.dlink
            DataDao.update_share_log_by_pk(share_log.id, {'dlink': data_item.dlink})
            return ShareLogs.to_dict(share_log)
        return None

    def check_file_by_key_search(self, key, _md5_val, share_log_id, pan_acc: PanAccounts):
        jsonrs = restapi.file_search(pan_acc.access_token, key=key, parent_dir=self.TMP_PATH)
        for finfo in jsonrs:
            if "fs_id" in finfo:
                md5_val = finfo["md5"]
                if md5_val == _md5_val:
                    dlink = ""
                    sync_list = restapi.sync_file(pan_acc.access_token, [int(finfo["fs_id"])])
                    expired_at = None
                    for sync_item in sync_list:
                        if finfo["fs_id"] == sync_item['fs_id']:
                            dlink = sync_item['dlink']
                            dlink = "%s&access_token=%s" % (dlink, pan_acc.access_token)
                            expired_at = arrow.now(self.default_tz).shift(hours=+DLINK_TIMEOUT).datetime
                            break
                    transfer_log_id, transfer_log = DataDao.new_transfer_log(share_log_id,
                                                                             str(finfo["fs_id"]),
                                                                             finfo["path"],
                                                                             finfo["server_filename"],
                                                                             finfo["size"],
                                                                             finfo["category"],
                                                                             finfo["md5"],
                                                                             dlink,
                                                                             pan_acc.user_id, expired_at,
                                                                             pan_acc.id)
                    if transfer_log_id:
                        # if transfer_log.dlink:
                        #     transfer_log.dlink = restapi.query_file_head(transfer_log.dlink)
                        # result.append(TransferLogs.to_dict(transfer_log))
                        DataDao.update_pan_account_by_pk(pan_acc.id, {'use_count': pan_acc.use_count + 1})
                        return transfer_log
        return None


    # 子账号转存分享文件
    def sub_account_transfer(self, share_log: ShareLogs):
        pan_acc_cache = self.checkout_pan_accounts(share_log.account_id)
        result = []
        sub_transfer_logs = DataDao.query_transfer_logs(share_log.id)
        # print("sub_transfer_logs:", sub_transfer_logs)
        if sub_transfer_logs:
            tl: TransferLogs = None
            for tl in sub_transfer_logs:

                if tl.md5_val == share_log.md5_val and tl.dlink:
                    # print("expired_at:", arrow.get(tl.expired_at).replace(tzinfo=self.default_tz))
                    # print("expired_at now:", arrow.now())
                    # print("compare:", arrow.get(tl.expired_at).replace(tzinfo=self.default_tz) < arrow.now())
                    if arrow.get(tl.expired_at).replace(tzinfo=self.default_tz) < arrow.now():
                        __pan_acc = self.get_pan_account(tl.pan_account_id, tl.account_id)
                        sync_dlink, thumbs = restapi.get_dlink_by_sync_file(__pan_acc.access_token, int(tl.fs_id))
                        # print("sync_dlink:", sync_dlink)
                        if sync_dlink:
                            # tl.dlink = sync_dlink
                            tl.dlink = "%s&access_token=%s" % (sync_dlink, __pan_acc.access_token)
                            tl.expired_at = arrow.now(self.default_tz).shift(hours=+DLINK_TIMEOUT).datetime
                            # print("new expired_at:", tl.expired_at)
                            DataDao.update_transfer_log_by_pk(tl.id, {"dlink": tl.dlink, "expired_at": tl.expired_at})
                    # tl.dlink = restapi.query_file_head(tl.dlink)
                    result.append(TransferLogs.to_dict(tl))

        if result:
            return result

        if share_log.is_black:
            data_item: DataItem = DataDao.get_data_item_by_fs_id(share_log.fs_id)
            key = self.parse_query_key(data_item.filename)
            for pan_acc_id in pan_acc_cache:
                # if pan_acc_id == self.pan_acc.id:
                #     continue
                time.sleep(0.8)
                _pan_acc: PanAccounts = pan_acc_cache[pan_acc_id]
                result = result + self.fetch_tmp_manual_file(key, _pan_acc, share_log, self.TMP_MANUAL_PATH)
            return result

        for pan_acc_id in pan_acc_cache:
            # if pan_acc_id == self.pan_acc.id:
            #     continue
            time.sleep(0.8)
            _pan_acc: PanAccounts = pan_acc_cache[pan_acc_id]
            try:
                jsonrs = restapi.pan_mkdir(_pan_acc.access_token, self.TMP_PATH)
                log.info("pan_mkdir jsonrs:", jsonrs)
                jsonrs = restapi.transfer_share_files(_pan_acc.access_token, share_id=share_log.share_id,
                                                      from_uk=share_log.uk, randsk=share_log.randsk,
                                                      fs_id=share_log.fs_id, path=self.TMP_PATH)
                if "extra" in jsonrs and "list" in jsonrs["extra"]:
                    file_path = jsonrs["extra"]["list"][0]["to"]  # /tmp/家长看（C妈力荐）  PDF 做孩子最好的英语学习规划师  中国儿童英语习得全路线图.pdf
                    key = self.parse_query_key(file_path)
                    transfer_log = self.check_file_by_key_search(key, share_log.md5_val, share_log.id, _pan_acc)
                    if transfer_log:
                        result.append(TransferLogs.to_dict(transfer_log))
                    # jsonrs = restapi.file_search(_pan_acc.access_token, key=key, parent_dir=self.TMP_PATH)
                    # for finfo in jsonrs:
                    #     if "fs_id" in finfo:
                    #         md5_val = finfo["md5"]
                    #         if md5_val == share_log.md5_val:
                    #             dlink = ""
                    #             sync_list = restapi.sync_file(_pan_acc.access_token, [int(finfo["fs_id"])])
                    #             expired_at = None
                    #             for sync_item in sync_list:
                    #                 if finfo["fs_id"] == sync_item['fs_id']:
                    #                     dlink = sync_item['dlink']
                    #                     dlink = "%s&access_token=%s" % (dlink, _pan_acc.access_token)
                    #                     expired_at = arrow.now(self.default_tz).shift(hours=+DLINK_TIMEOUT).datetime
                    #                     break
                    #             transfer_log_id, transfer_log = DataDao.new_transfer_log(share_log.id,
                    #                                                                      str(finfo["fs_id"]),
                    #                                                                      finfo["path"],
                    #                                                                      finfo["server_filename"],
                    #                                                                      finfo["size"],
                    #                                                                      finfo["category"],
                    #                                                                      finfo["md5"],
                    #                                                                      dlink,
                    #                                                                      _pan_acc.user_id, expired_at,
                    #                                                                      _pan_acc.id)
                    #             if transfer_log_id:
                    #                 # if transfer_log.dlink:
                    #                 #     transfer_log.dlink = restapi.query_file_head(transfer_log.dlink)
                    #                 result.append(TransferLogs.to_dict(transfer_log))
                    #                 DataDao.update_pan_account_by_pk(_pan_acc.id, {'use_count': _pan_acc.use_count+1})
                    #                 continue
                elif jsonrs.get('errno', 0) == -30 and 'path' in jsonrs:
                    file_path = jsonrs.get('path', None)
                    if file_path:
                        key = self.parse_query_key(file_path)
                        transfer_log = self.check_file_by_key_search(key, share_log.md5_val, share_log.id, _pan_acc)
                        if transfer_log:
                            result.append(TransferLogs.to_dict(transfer_log))
            except Exception:
                pass
        return result

    def fetch_tmp_manual_file(self, key, _pan_acc: PanAccounts, share_log: ShareLogs, parent_dir):
        # TMP_MANUAL_PATH
        jsonrs = restapi.file_search(_pan_acc.access_token, key=key, parent_dir=parent_dir)
        result = []
        for finfo in jsonrs:
            if "fs_id" in finfo:
                md5_val = finfo["md5"]
                if md5_val == share_log.md5_val:
                    dlink = ""
                    # sync_list = restapi.sync_file(_pan_acc.access_token, [int(finfo["fs_id"])])
                    sync_dlink, thumbs = restapi.get_dlink_by_sync_file(_pan_acc.access_token, int(finfo["fs_id"]))
                    expired_at = None
                    if sync_dlink:
                        dlink = "%s&access_token=%s" % (sync_dlink, _pan_acc.access_token)
                        expired_at = arrow.now(self.default_tz).shift(hours=+DLINK_TIMEOUT).datetime
                    transfer_log_id, transfer_log = DataDao.new_transfer_log(share_log.id,
                                                                             str(finfo["fs_id"]),
                                                                             finfo["path"],
                                                                             finfo["server_filename"],
                                                                             finfo["size"],
                                                                             finfo["category"],
                                                                             finfo["md5"],
                                                                             dlink,
                                                                             _pan_acc.user_id, expired_at, _pan_acc.id)
                    if transfer_log_id:
                        result.append(TransferLogs.to_dict(transfer_log))
                        DataDao.update_pan_account_by_pk(_pan_acc.id, {'use_count': _pan_acc.use_count + 1})
                        continue
        return result

    def parse_query_key(self, file_path):
        key = file_path
        idx = key.rfind(".")
        if idx > 0:
            key = key[:idx - 1]
        idx = key.rfind("/")
        if idx > 0:
            key = key[idx + 1:]
        if len(key) > 6:
            key = key[len(key) - 6:]
        return key

    def checkout_pan_accounts(self, account_id=0):
        return auth_service.checkout_pan_accounts(account_id)

    def get_pan_account(self, pan_account_id, account_id) -> PanAccounts:
        # if get_now_ts() - self.PAN_ACC_CACHE_LAST_TIME > PAN_ACC_CACHE_TIMEOUT:
        #     pan_acc_list = DataDao.pan_account_list(account_id)
        #     self.PAN_ACC_CACHE = {pan_acc_dict.id: pan_acc_dict for pan_acc_dict in pan_acc_list}
        #     self.PAN_ACC_CACHE_LAST_TIME = get_now_ts()
        pan_acc_cache = self.checkout_pan_accounts(account_id)
        if pan_account_id in pan_acc_cache:
            return pan_acc_cache[pan_account_id]
        return DataDao.pan_account_by_id(pan_account_id)


pan_service = PanService()
