# -*- coding: utf-8 -*-
"""
Created by susy at 2019/12/16
"""
from controller.action import BaseHandler
from dao.community_dao import CommunityDao
from controller.open_service import open_service
from controller.service import pan_service
from cfg import DEFAULT_CONTACT_QR_URI, bd_auth_path, PAN_SERVICE
from utils import log as logger, url_decode, decrypt_id, constant


class OpenHandler(BaseHandler):

    def post(self):
        self.get()

    def load_file_list(self, source, node_id, page, size):
        params = []
        meta = {
            "has_next": False, "pagesize": size
        }
        if not '#' == node_id:
            if "free" == source:
                if 'free_0' == node_id:
                    params = pan_service.query_root_list()
            else:
                node_id_val = decrypt_id(node_id)
                parent_id = int(node_id_val)
                params, meta = pan_service.query_file_list(parent_id, int(page), int(size))
        else:
            # params = pan_service.query_root_list(self.request.user_id)
            params.append({"id": "free_0", "text": constant.PAN_TREE_TXT['free_root'], "data": {"source": "free"},
                           "children": True, "icon": "folder"})
        if "total" not in meta:
            meta["total"] = len(params)
        return params, meta

    def get(self):
        path = self.request.path
        if path.endswith("/init"):
            tag_list = open_service.load_tags()
            # print('headers:', self.request.headers)
            bd_auth_query_path = bd_auth_path(skip_login=True)
            auth_dns_domain = "{}://{}".format(PAN_SERVICE['protocol'], PAN_SERVICE['auth_dns_domain'])
            bd_user_point = "/rest/2.0/passport/users/getInfo"
            pan_url = "/oauth/2.0/token"
            auth_point = "/oauth/2.0/{}".format(bd_auth_query_path)
            auth_params = {'grant_type': 'authorization_code', 'client_id': PAN_SERVICE["client_id"],
                           'redirect_uri': 'oob', 'client_secret': PAN_SERVICE["client_secret"]}
            rs = {'data': tag_list, 'contact': DEFAULT_CONTACT_QR_URI, 'auth': {
                'auth_dns_domain': auth_dns_domain,
                'bd_user_point': bd_user_point, 'bdauth': auth_point,
                  'auth_params': auth_params, 'auth_point': pan_url}}
            self.to_write_json(rs)
        elif path.endswith("/loops"):
            rs = CommunityDao.loop_ad_tasks()
            self.to_write_json(rs)
        elif path.endswith("/se"):
            kw = self.get_argument("kw")
            pid = self.get_argument("pid", None)
            tag = self.get_argument("tag", None)
            rg = self.get_argument("range", "dir")
            tag = url_decode(tag)
            path_tag = self.get_argument("path_tag", None)
            source = self.get_argument("source", "")
            page = self.get_argument("page", "0")
            size = self.get_argument("size", "20")
            pos = int(self.get_argument("pos", "2"))
            # print("kw:", kw)
            # print("source:", source)
            rs = open_service.search(path_tag, tag, kw, source, pid, rg, page, int(size), pos)
            self.to_write_json(rs)
        elif path.endswith("/shared"):
            fs_id = self.get_argument("fs_id")
            # rs = open_service.fetch_shared(fs_id)
            rs = open_service.fetch_shared_skip_visible(fs_id)

            self.to_write_json(rs)
        elif path.endswith("/cfg"):
            platform = self.get_argument("platform", "win32")
            logger.info("cfg platform:{}".format(platform))
            if platform.lower().find("darwin") < 0:
                platform = "win32"
            self.release_db = False
            rs = open_service.checkout_app_cfg(platform)
            self.to_write_json(rs)
        elif path.endswith("/update_cfg"):
            rs = open_service.sync_cfg()
            self.to_write_json(rs)
        elif path.endswith("/update_tags"):
            rs = open_service.sync_tags()
            self.to_write_json(rs)
        elif path.endswith("/wxfload"):
            source = self.get_argument("source", "")
            node_id = self.get_argument("id")
            page = self.get_argument("page", "0")
            size = self.get_argument("size", "100")
            params, meta = self.load_file_list(source, node_id, page, size)
            rs = meta
            rs['data'] = params
            self.to_write_json(rs)
        elif path.endswith("/scanepub"):
            # scan
            rs = open_service.scan_epub(self.context, self.guest)
            self.to_write_json(rs)
        elif path.endswith("/ali/callback"):
            params = self.wrap_request_dict()
            open_service.ali_callback(params, self.context, self.guest)
            self.to_write_json({})
        elif path.endswith("/ali/put"):
            params = self.wrap_request_dict()
            open_service.ali_post(params)
            self.to_write_json({})
        else:
            self.to_write_json({})
