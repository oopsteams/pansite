# -*- coding: utf-8 -*-
"""
Created by susy at 2019/10/17
"""
import os
import sys
import json
import traceback
from utils import CJsonEncoder, get_payload_from_token, decrypt_user_id, get_now_ts, url_encode
from typing import Optional, Awaitable, Any
from dao.dao import DataDao
from dao.models import DataItem, try_release_conn
from dao.es_dao import es_dao_share, es_dao_local
from tornado.web import RequestHandler, authenticated
from utils.utils_es import SearchParams, build_query_item_es_body
from utils.constant import LOGIN_TOKEN_TIMEOUT, USER_TYPE
from controller.service import pan_service
from controller.open_service import open_service
from controller.sync_service import sync_pan_service
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
        self.is_web = False
        self.query_path = ''
        self.token = None
        super(BaseHandler, self).__init__(application, request, **kwargs)

    def initialize(self, middleware) -> None:
        self.middleware = middleware

    def prepare(self):
        for middleware in self.middleware:
            middleware.process_request(self)

    def get_current_user(self):
        # headers = self.request.headers
        # print("get_current_user headers:", headers)
        # print("get_current_user in...")
        # print("user_payload:", self.user_payload)

        if self.user_payload:
            if 'id' in self.user_payload:
                tm = self.user_payload['tm']
                ctm = get_now_ts()
                # print('payload:', self.user_payload, ctm, ctm - tm, LOGIN_TOKEN_TIMEOUT)
                if ctm - tm > LOGIN_TOKEN_TIMEOUT:
                    self.set_cookie('pan_site_force', str(1))
                    print('token expired!!!')
                    return False
                setattr(self.request, 'user_id', self.user_payload['user_id'])
                return True

        if self.is_web:
            print('set is_web is 1, path:', self.request.path)
            self.set_cookie('pan_site_is_web', str(1))
            self.set_cookie('pan_site_ref', self.request.path)
        return False
        # return True

    def _handle_request_exception(self, e):
        params = {"exc_info": sys.exc_info()}
        self.write_error(404, **params)

    def send_error(self, status_code=500, **kwargs) -> None:
        self.write_error(404, **kwargs)

    # def send_error(self, stat, **kw):
    #     self.write_error(404, **kw)

    def write_error(self, stat, **kw):
        error_trace_list = None
        if kw:
            error_trace_list = traceback.format_exception(*kw.get("exc_info"))
        if stat == 500:
            print("server err:", error_trace_list)
        elif stat == 403:
            print("request forbidden!")
        else:
            if error_trace_list:
                traceback.print_exc()

        rs = {"status": -1, "error": error_trace_list}

        self.write(json.dumps(rs))

    def on_finish(self):
        # print("on_response request finish.")
        if self.release_db:
            print('need to release conn!')
            try_release_conn()
        else:
            print('not need to release conn!')

    def getRemoteIp(self):
        header = self.request.headers
        rip = self.request.remote_ip
        if 'X-Real-Ip' in header:
            rip = header['X-Real-Ip']
        return rip

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def to_write_json(self, result):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(result, cls=CJsonEncoder))


class PanHandler(BaseHandler):

    @authenticated
    def get(self):
        path = self.request.path
        print(path)
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
            parent_path = self.get_argument("path")
            if not parent_path.endswith("/"):
                parent_path = "%s/" % parent_path
            print("node_id:", node_id)
            parent_id = 55
            if not '#' == node_id:
                parent_id = int(node_id)
                if "shared" == source:
                    params = pan_service.query_shared_file_list(parent_id, self.request.user_id)
                else:
                    params = pan_service.query_file_list(parent_id)
            else:
                params = pan_service.query_root_list(self.request.user_id)

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
            item_id = self.get_argument("id")
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
            item_id = self.get_argument("id", None)
            pan_id = self.get_argument('panid', "0")
            pan_id = int(pan_id)
            recursion = self.get_argument("recursion")
            if recursion == "1":
                recursion = True
            else:
                recursion = False
            if not item_id:
                if pan_id:
                    root_item: DataItem = sync_pan_service.fetch_root_item(pan_id)
                    print('root_item:', DataItem.to_dict(root_item))
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


class MainHandler(BaseHandler):

    def get(self):
        path = self.request.path
        if path.endswith("/login/"):
            print("login body:", self.request.body)
            # self.get_argument("mobile_no")
            user_name = self.get_body_argument("mobile_no")
            user_passwd = self.get_body_argument("password")
            is_single = self.get_body_argument('single', '0', True) == '1'
            result = pan_service.check_user(user_name, user_passwd)
            print("result:", result)
            if is_single and 'token' in result:
                result = {'token': result['token']}
            self.write(json.dumps(result))
        elif path.endswith("/authlogin/"):
            result = {'tag': 'authlogin'}
            for f in self.request.query_arguments:
                print("{}:{}".format(f, self.get_argument(f)))
            self.write(json.dumps(result))
        elif path.endswith("/register/"):
            self.render('register.html')
        elif path.endswith("/access_code/"):
            print("login body:", self.request.body)
            token = self.get_body_argument("token")
            code = self.get_body_argument("code")
            pan_name = self.get_body_argument("pan_name")
            refresh_str = self.get_body_argument("refresh")
            print('refresh_str:', refresh_str)
            can_refresh = True
            if refresh_str == '0':
                can_refresh = False
            payload = get_payload_from_token(token)
            user_id = decrypt_user_id(payload['id'], )
            print("payload:", payload)
            print("can_refresh:", can_refresh)
            access_token, pan_acc_id, err = pan_service.get_pan_user_access_token(user_id, code, pan_name, can_refresh)
            need_renew_pan_acc = pan_service.load_pan_acc_list_by_user(user_id)
            result = {"result": "ok", "access_token": access_token, "pan_acc_id": pan_acc_id, "token": self.token}
            if need_renew_pan_acc:
                result['pan_acc_list'] = need_renew_pan_acc
            if err:
                result = {"result": "fail", "error": err}
            print("result:", result)
            self.to_write_json(result)
        elif path.endswith("/save/"):
            mobile_no = self.get_body_argument("mobile_no")
            passwd = self.get_body_argument("password")
            token, fuzzy_id, err = pan_service.save_user(mobile_no, passwd)
            result = {"result": "ok", "token": token, "fuzzy_id": fuzzy_id}
            if err:
                result = {"result": "fail", "error": err}
            print("result:", result)
            self.write(json.dumps(result))
        elif path.endswith("/ready_login/"):
            v = self.get_cookie('pan_site_is_web')
            ref = self.get_cookie('pan_site_ref')
            _force = self.get_cookie('pan_site_force')
            self.set_cookie('pan_site_force', '')
            print('v:', v)
            print('ref:', ref)
            # uri = url_encode('https://www.oopsteam.site/authlogin/')
            uri = 'https://www.oopsteam.site/authlogin/'
            # uri = 'http://localhost:8080/authlogin'
            if '1' == v:
                # self.render('index.html', **{'ref': ref, 'force': _force})
                self.set_header("Referer", "https://www.oopsteam.site/index.html")
                self.redirect(get_bd_auth_uri(uri, display='page'))
            else:
                self.to_write_json({"result": "fail", "state": -1, 'force': _force,
                                    "lg": self.redirect(get_bd_auth_uri(uri))})
        elif path.endswith("/fresh_token/"):
            pan_id = self.get_argument('panid')
            pan_service.fresh_token(pan_id)
            self.to_write_json({"result": "ok"})
        else:
            if path and len(path) > 1 and path[0] == '/':
                path = path[1:]
                self.render(path, **{'ref': '', 'force': ''})
            else:
                self.render('index.html', **{'ref': '', 'force': ''})

    def post(self):
        self.get()

