# -*- coding: utf-8 -*-
"""
Created by susy at 2019/12/24
"""
from controller.action import BaseHandler
from dao.community_dao import CommunityDao
from tornado.web import authenticated
from utils import compare_dt_by_now
from controller.mpan_service import mpan_service
from controller.sync_service import sync_pan_service
from utils.constant import USER_TYPE


class ManageHandler(BaseHandler):

    def post(self):
        self.get()

    @authenticated
    def get(self):
        path = self.request.path
        if path.endswith("/init"):
            pan_acc_list = CommunityDao.pan_account_list(self.request.user_id)
            for pan in pan_acc_list:
                if compare_dt_by_now(pan['expires_at']) <= 0:
                    pan['expired'] = 1
                else:
                    pan['expired'] = 0
            params = {'items': pan_acc_list}
            print("params:", params)
            self.render('panmanage.html', **params)
        elif path.endswith("/ftree"):
            pan_id = self.get_argument("panid", "0")
            params = {'pan_id': pan_id}
            self.render('mantree.html', **params)
        elif path.endswith("/fload"):
            pan_id = self.get_argument("panid", "0")
            source = self.get_argument("source", "")
            node_id = self.get_argument("id")
            parent_path = self.get_argument("path")
            # if not parent_path.endswith("/"):
            #     parent_path = "%s/" % parent_path

            # print("user_payload:", self.user_payload)
            params = []
            if not source or "local" == source:
                print("fload node_id:", node_id, ", pan_id:", pan_id, ", source:", source)
                if not '#' == node_id:
                    parent_id = int(node_id)
                    params = mpan_service.query_file_list(parent_id)
                else:
                    params = mpan_service.fetch_root_item_by_user(self.user_id)

                # pan_id = int(pan_id)
                # print("parent_id, pan_id:", parent_id, pan_id)
                # params = mpan_service.query_file_list(parent_id, pan_id)
            if not source or "shared" == source:
                print("fload node_id:", node_id, ",fs_id:", self.get_argument("fs_id", "0"), ", source:", source)
                shared_params = []
                if not '#' == node_id:
                    parent_id = int(self.get_argument("fs_id", "0"))
                    if parent_id == 0:
                        shared_params = mpan_service.query_share_list(None)
                    else:
                        shared_params = mpan_service.query_share_list(parent_id)
                else:
                    node_param = {"id": "s_0", "text": "外部分享(shared)",
                                  "data": {"path": "/", "fs_id": 0,
                                           "server_ctime": 0,
                                           "isdir": 1, "source": "shared", "_id": 0,
                                           "pin": 0}, "children": True, "icon": "jstree-folder"}

                    shared_params = [node_param]
                if shared_params:
                    if not params:
                        params = shared_params
                    else:
                        params = params + shared_params

            self.to_write_json(params)
        elif path.endswith("/show"):
            source = self.get_argument("source", "")
            parent = self.get_argument("parent", "")
            node_id = self.get_argument("id")
            print("source:", source, ",parent:", parent, ",node_id:", node_id)
            if "local" == source:
                if parent:
                    mpan_service.update_local_sub_dir(parent, {'pin': 1})
                else:
                    mpan_service.update_local_item(node_id, {'pin': 1})
            else:
                if parent:
                    mpan_service.update_shared_sub_dir(parent, {'pin': 1})
                else:
                    mpan_service.update_shared_item(node_id, {'pin': 1})
            self.to_write_json({})
        elif path.endswith("/hide"):
            source = self.get_argument("source", "")
            parent = self.get_argument("parent", "")
            node_id = self.get_argument("id")
            print("source:", source, ",parent:", parent, ",node_id:", node_id)
            if "local" == source:
                if parent:
                    mpan_service.update_local_sub_dir(parent, {'pin': 0})
                else:
                    mpan_service.update_local_item(node_id, {'pin': 0})
            else:
                if parent:
                    mpan_service.update_shared_sub_dir(parent, {'pin': 0})
                else:
                    mpan_service.update_shared_item(node_id, {'pin': 0})

            self.to_write_json({})
        elif path.endswith("/clear"):
            item_id = int(self.get_argument("id", "0"))
            pan_id = int(self.get_argument("panid", "0"))
            sync_pan_service.clear(item_id, pan_id)
            self.to_write_json({'state': 0})
        elif path.endswith("/fparts"):
            # pan_id = self.get_argument("id", "0")
            # print("hello fparts!")
            item_list = CommunityDao.query_share_logs_by_hours(-24, 0, 100)
            # print("item_list:", item_list)
            # for item in item_list:
            #     print("item:", item.filename)
            params = {"list": item_list}
            # print("params:", params)
            self.render('fparts.html', **params)
        elif path.endswith("/clearshare"):
            share_item_id = int(self.get_argument("id", "0"))
            sync_pan_service.clear_share_log(share_item_id)
            self.to_write_json({'state': 0})
        else:
            self.to_write_json({})
