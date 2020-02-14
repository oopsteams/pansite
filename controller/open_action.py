# -*- coding: utf-8 -*-
"""
Created by susy at 2019/12/16
"""
from controller.action import BaseHandler
from dao.community_dao import CommunityDao
from controller.open_service import open_service
from cfg import DEFAULT_CONTACT_QR_URI


class OpenHandler(BaseHandler):

    def post(self):
        self.get()

    def get(self):
        path = self.request.path
        if path.endswith("/init"):
            tag_list = CommunityDao.default_tags()
            rs = {'data': tag_list, 'contact': DEFAULT_CONTACT_QR_URI}
            self.to_write_json(rs)
        elif path.endswith("/loops"):
            rs = CommunityDao.loop_ad_tasks()
            self.to_write_json(rs)
        elif path.endswith("/se"):
            kw = self.get_argument("kw")
            tag = self.get_argument("tag", None)
            path_tag = self.get_argument("path_tag", None)
            source = self.get_argument("source", "")
            page = self.get_argument("page", 0)
            print("kw:", kw)
            print("source:", source)
            rs = open_service.search(path_tag, tag, kw, source, page)
            self.to_write_json(rs)
        elif path.endswith("/shared"):
            fs_id = self.get_argument("fs_id")
            rs = open_service.fetch_shared(fs_id)
            self.to_write_json(rs)
        else:
            self.to_write_json({})
