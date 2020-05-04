# -*- coding: utf-8 -*-
"""
Created by susy at 2019/10/17
"""
import sys
import json
import traceback
from utils import CJsonEncoder, get_payload_from_token, decrypt_user_id, get_now_ts, decrypt_id, log as logger
from typing import Optional, Awaitable, Any
from dao.mdao import DataDao
from dao.product_dao import ProductDao
from dao.models import DataItem, try_release_conn, Accounts
from dao.es_dao import es_dao_share, es_dao_local
from tornado.web import RequestHandler, authenticated
from utils.utils_es import SearchParams, build_query_item_es_body
from utils.constant import LOGIN_TOKEN_TIMEOUT, USER_TYPE, PAN_TREE_TXT
from controller.service import pan_service
from controller.open_service import open_service
from controller.sync_service import sync_pan_service
from controller.auth_service import auth_service
import traceback
from cfg import get_bd_auth_uri

LOGIN_TOKEN_KEY = "Suri-Token"
FIELDS = ['id', 'category', 'isdir', 'filename', 'dlink', 'fs_id', 'path', 'size', 'parent', 'dlink_updated_at', 'account_id']
PAN_ACC_CACHE = {}
PAN_ACC_CACHE_TIMEOUT = 24 * 60 * 60
PAN_ACC_CACHE_LAST_TIME = 0


class BaseHandler(RequestHandler):

    def __init__(self, application: "Application", request, **kwargs):
        self.release_db = True
        self.middleware = None
        self.user_payload = None
        self.user_type = USER_TYPE['SINGLE']
        self.user_id = 0
        self.ref_id = 0
        self.default_pan_id = 0
        self.is_web = False
        self.query_path = ''
        self.token = None
        self.context = {}
        self.guest: Accounts = None
        super(BaseHandler, self).__init__(application, request, **kwargs)

    def initialize(self, middleware, context=None) -> None:
        self.middleware = middleware
        if context:
            self.context = context
            _guest = context.get('guest', None)
            if _guest:
                self.guest = _guest

    def prepare(self):
        for middleware in self.middleware:
            middleware.process_request(self)

    def get_current_user(self):
        # headers = self.request.headers
        # print("get_current_user headers:", headers)
        # print("get_current_user in...")
        # print("get_current_user user_payload:", self.user_payload)

        if self.user_payload:
            if 'id' in self.user_payload:
                tm = self.user_payload['tm']
                ctm = get_now_ts()
                # print('payload:', self.user_payload, ctm, ctm - tm, LOGIN_TOKEN_TIMEOUT)
                if ctm - tm > LOGIN_TOKEN_TIMEOUT:
                    self.set_cookie('pan_site_force', str(1))
                    logger.info('token expired!!!')
                    return False
                setattr(self.request, 'user_id', self.user_payload['user_id'])
                return True

        if self.is_web:
            logger.info('set is_web is 1, path:{}'.format(self.request.path))
            self.set_cookie('pan_site_is_web', str(1))
            self.set_cookie('pan_site_ref', self.request.path)
        return False
        # return True

    def _handle_request_exception(self, e):
        logger.error("request err:{}".format(traceback.format_exception(*sys.exc_info())))
        t, v, tb = sys.exc_info()
        params = {"exc_info":  "[{}]{}".format(t, v), "state": -1, "err": "parameters error!"}
        # self.write_error(404, **params)
        # self.write(json.dumps(params))
        self.to_write_json(params)

    def send_error(self, status_code=500, **kwargs) -> None:
        # self.write_error(404, **kwargs)
        logger.error("service err", exc_info=True)
        t, v, tb = sys.exc_info()
        params = {"exc_info": "[{}]{}".format(t, v), "state": -1, "err": "service error!"}
        self.to_write_json(params)

    # def send_error(self, stat, **kw):
    #     self.write_error(404, **kw)

    def write_error(self, stat, **kw):
        error_trace_list = None
        if kw:
            error_trace_list = traceback.format_exception(*kw.get("exc_info"))
        if stat == 500:
            logger.error("server err:{}".format(error_trace_list))
        elif stat == 403:
            logger.error("request forbidden!")
        else:
            pass
            # if error_trace_list:
            #     traceback.print_exc()

        rs = {"status": -1, "error": error_trace_list}

        self.write(json.dumps(rs))

    def on_finish(self):
        # print("on_response request finish.")
        self.try_release_db_conn()

    def getRemoteIp(self):
        header = self.request.headers
        rip = self.request.remote_ip
        if 'X-Real-Ip' in header:
            rip = header['X-Real-Ip']
        return rip

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def try_release_db_conn(self):
        if self.release_db:
            logger.info('need to release conn!')
            try_release_conn()
        else:
            logger.info('not need to release conn!')

    def to_write_json(self, result):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(result, cls=CJsonEncoder))


class PanHandler(BaseHandler):

    @authenticated
    def get(self):
        path = self.request.path
        # print(path)
        if path.endswith("/list"):
            parent = self.get_argument("parent", default='55')
            item_list = DataDao.query_data_item_by_parent(int(parent), True)
            params = {"list": item_list}
            # print("params:", params)
            # for item in item_list:
            #     print(item.filename)
            self.render('list.html', **params)
        elif path.endswith("/fload"):
            source = self.get_argument("source", "")
            node_id = self.get_argument("id")
            # parent_path = self.get_argument("path")
            # if not parent_path.endswith("/"):
            #     parent_path = "%s/" % parent_path
            logger.info("fload node_id:{},source:{}".format(node_id, source))
            # parent_id = 55
            params = []
            if not '#' == node_id:
                # if "shared" == source:
                #     params = pan_service.query_shared_file_list(parent_id, self.request.user_id)
                if "assets" == source:
                    if 'assets_0' == node_id:
                        params = ProductDao.query_assets_by_ref_id_for_tree(self.ref_id)
                elif "free" == source:
                    if 'free_0' == node_id:
                        params = pan_service.query_root_list()
                elif "self" == source:
                    if 'self_0' == node_id:
                        if not self.default_pan_id:
                            pan_acc = auth_service.default_pan_account(self.user_id)
                            self.default_pan_id = pan_acc.id
                        if self.default_pan_id:
                            params = pan_service.query_client_root_list(self.default_pan_id)
                    else:
                        node_id_val = decrypt_id(node_id)
                        parent_id = int(node_id_val)
                        params = pan_service.query_client_sub_list(parent_id, self.ref_id)
                elif "empty" == source:
                    pass
                else:
                    node_id_val = decrypt_id(node_id)
                    parent_id = int(node_id_val)
                    params = pan_service.query_file_list(parent_id)
            else:
                # params = pan_service.query_root_list(self.request.user_id)
                params.append({"id": "free_0", "text": PAN_TREE_TXT['free_root'], "data": {"source": "free"},
                               "children": True, "icon": "folder"})
                params.append({"id": "assets_0", "text": PAN_TREE_TXT['buy_root'], "data": {"source": "assets"},
                               "children": True, "icon": "folder"})
                params.append({"id": "self_0", "text": PAN_TREE_TXT['self_root'], "data": {"source": "self"},
                               "children": True, "icon": "folder"})
                params.append({"id": "empty_0", "text": PAN_TREE_TXT['empty_root'], "data": {"source": "empty"},
                               "children": False, "icon": "file"})

            self.to_write_json(params)
        elif path.endswith("/search"):
            params = {}
            self.render('search.html', **params)
        elif path.endswith("/load"):
            kw = self.get_body_argument("kw")
            source = self.get_body_argument("source")
            print("kw:", kw)
            print("source:", source)
            kw = kw.replace(' ', '%')
            page = self.get_body_argument("page")
            size = 100
            offset = int(page) * size
            sp: SearchParams = SearchParams.build_params(offset, size)
            sp.add_must(value=kw)
            es_dao_fun = es_dao_local
            if source:
                sp.add_must(field='source', value=source)
                es_dao_fun = es_dao_share
                # es_dao_fun = es_dao_dir
            es_body = build_query_item_es_body(sp)
            print("es_body:", json.dumps(es_body))
            es_result = es_dao_fun().es_search_exec(es_body)
            hits_rs = es_result["hits"]
            total = hits_rs["total"]
            datas = [_s["_source"] for _s in hits_rs["hits"]]

            # print("es_result:", es_result)
            # item_list = DataDao.query_file_list_by_keyword(kw, offset=offset, limit=size)
            # objs = [object_to_dict(o, FIELDS) for o in item_list]
            # has_next = len(objs) == size
            has_next = offset + size < total
            rs = {"data": datas, "has_next": has_next}
            # print("rs:", rs)
            self.to_write_json(rs)
        elif path.endswith("/finfo"):
            # item_id = self.get_argument("id")
            item_fuzzy_id = self.get_argument("id")
            item_id = int(decrypt_id(item_fuzzy_id))
            params = pan_service.query_file(item_id)
            self.to_write_json(params)
        elif path.endswith("/readydownload"):
            fs_id = self.get_argument("fs_id")
            print("readydownload fs_id:", fs_id)
            params, share_log, data_item = pan_service.share_folder(fs_id)
            # sub_params = []
            min_size = 6000
            # min_size = 60
            if data_item.size > min_size:
                sub_params = pan_service.sub_account_transfer(share_log)
                result = {"subs": sub_params}
            else:
                result = {"master": params}
            # result = {"master": params, "subs": sub_params}
            self.to_write_json(result)
        elif path.endswith("/check_transfer"):
            transfer_log_id = self.get_argument("id")
            rs = {}
            print("transfer_log_id:", transfer_log_id)
            if transfer_log_id:
                t = pan_service.recheck_transfer_d_link(int(transfer_log_id))
                if t:
                    rs = t
            self.to_write_json(rs)
        elif path.endswith("/check_shared_log"):
            shared_log_id = self.get_argument("id")
            rs = {}
            print("shared_log_id:", shared_log_id)
            if shared_log_id:
                t = pan_service.recheck_shared_d_link(int(shared_log_id))
                if t:
                    rs = t
            self.to_write_json(rs)
        elif path.endswith("/sync_used"):
            pan_account_ids_str = self.get_argument("ids")
            used_str = self.get_argument("useds")
            if pan_account_ids_str and used_str:
                _ids = pan_account_ids_str.split(",")
                useds = used_str.split(",")
                params = []
                ul = len(useds)
                for i in range(len(_ids)):
                    _id = _ids[i]
                    if i < ul:
                        used = useds[i]
                        params.append({'id': int(_id), 'used': int(used)})

                if params:
                    DataDao.update_pan_account_used(params)

            self.to_write_json({})
        elif path.endswith("/dlink"):
            item_id = self.get_argument("id")
            params = pan_service.query_file(item_id)
            self.render('dlink.html', **params)
        elif path.endswith("/manage"):
            pan_id = self.get_argument("panid", "0")
            params = {'pan_id': pan_id}
            self.render('ftree.html', **params)
        elif path.endswith("/helptokens"):
            res = pan_service.pan_accounts_dict()
            self.to_write_json(res)
        elif path.endswith("/syncallnodes"):
            item_fuzzy_id = self.get_argument("id", None)
            item_id = int(decrypt_id(item_fuzzy_id))
            pan_id = self.get_argument('panid', "0")
            logger.info("syncallnodes pan_id:{}".format(pan_id))
            pan_id = int(pan_id)
            recursion = self.get_argument("recursion")
            if recursion == "1":
                recursion = True
            else:
                recursion = False
            if not item_id:
                if pan_id:
                    root_item: DataItem = sync_pan_service.fetch_root_item(pan_id)
                    logger.info('root_item:{}'.format(DataItem.to_dict(root_item)))
                    if root_item:
                        item_id = root_item.id
                    else:
                        item_id = sync_pan_service.new_root_item(self.request.user_id, pan_id)
                else:
                    item_id = 55
            item_id = int(item_id)
            rs = sync_pan_service.sync_from_root(item_id, recursion, pan_id, self.request.user_id)
            self.to_write_json(rs)
        elif path.endswith("/synccommunity"):
            # print("in...:")
            bd = self.request.body
            data_obj = json.loads(bd)
            print('/synccommunity payload:', self.request.user_id)
            open_service.sync_community_item_to_es(self.request.user_id, data_obj)
            self.to_write_json({'state': 0})
            pass
        elif path.endswith("/syncstate"):
            self.release_db = False
            pan_id = self.get_argument('panid', "0")
            dir_item_id = sync_pan_service.check_sync_state(pan_id, self.request.user_id)
            if dir_item_id:
                self.to_write_json({'state': 1, 'item': dir_item_id})
            else:
                self.to_write_json({'state': 0})

    def post(self):
        self.get()



