# -*- coding: utf-8 -*-
"""
Created by susy at 2019/12/16
"""
from controller.action import BaseHandler
from dao.community_dao import CommunityDao
from controller.open_service import open_service
from cfg import DEFAULT_CONTACT_QR_URI, bd_auth_path, PAN_SERVICE
from utils import log as logger, url_decode


class OpenHandler(BaseHandler):

    def post(self):
        self.get()

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
            tag = url_decode(tag)
            path_tag = self.get_argument("path_tag", None)
            source = self.get_argument("source", "")
            page = self.get_argument("page", "0")
            size = self.get_argument("size", "50")
            # print("kw:", kw)
            # print("source:", source)
            rs = open_service.search(path_tag, tag, kw, source, pid, page, int(size))
            self.to_write_json(rs)
        elif path.endswith("/shared"):
            fs_id = self.get_argument("fs_id")
            rs = open_service.fetch_shared(fs_id)
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
        else:
            self.to_write_json({})
