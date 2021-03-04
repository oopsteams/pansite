# -*- coding: utf-8 -*-
"""
Created by susy at 2019/12/24
"""
from controller.action import BaseHandler
from dao.community_dao import CommunityDao
from dao.mdao import DataDao
from tornado.web import authenticated
from utils import compare_dt_by_now, decrypt_id, log as logger
from controller.mpan_service import mpan_service
from controller.sync_service import sync_pan_service
from controller.service import pan_service
from dao.models import DataItem


class ManageHandler(BaseHandler):

    @authenticated
    def get(self):
        path = self.request.path
        logger.debug("ManageHandler deal path:{}".format(path))
        if path.endswith("/init"):
            pan_acc_list = CommunityDao.pan_account_list(self.request.user_id)
            for pan in pan_acc_list:
                if compare_dt_by_now(pan['expires_at']) <= 0:
                    pan['expired'] = 1
                else:
                    pan['expired'] = 0
            params = {'items': pan_acc_list}
            # print("params:", params)
            self.render('panmanage.html', **params)
        elif path.endswith("/ftree"):
            pan_id = self.get_argument("panid", "0")
            params = {'pan_id': pan_id}
            self.render('mantree.html', **params)
        elif path.endswith("/fload"):
            # pan_id = self.get_argument("panid", "0")
            source = self.get_argument("source", "")
            node_id = self.get_argument("id")
            parent_path = self.get_argument("path")
            # if not parent_path.endswith("/"):
            #     parent_path = "%s/" % parent_path

            # print("user_payload:", self.user_payload)
            params = []
            if not source or "local" == source:
                # print("fload node_id:", node_id, ", pan_id:", pan_id, ", source:", source)
                if not '#' == node_id:
                    node_id_val = decrypt_id(node_id)
                    parent_id = int(node_id_val)
                    params, _ = mpan_service.query_file_list(parent_id)
                else:
                    params = mpan_service.fetch_root_item_by_user(self.user_id)

                # pan_id = int(pan_id)
                # print("parent_id, pan_id:", parent_id, pan_id)
                # params = mpan_service.query_file_list(parent_id, pan_id)
            if not source or "shared" == source:
                # print("fload node_id:", node_id, ",fs_id:", self.get_argument("fs_id", "0"), ", source:", source)
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
                                           "pin": 0}, "children": True, "icon": "folder"}

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
            node_id = int(self.get_argument("id"))
            logger.info("source:{},parent:{},node_id:{}".format(source, parent, node_id))
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
            # node_fuzzy_id = self.get_argument("id")
            # node_id = decrypt_id(node_fuzzy_id)
            node_id = int(self.get_argument("id"))
            logger.info("hide source:{},parent:{},node_id:{}".format(source, parent, node_id))
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
            item_fuzzy_id = self.get_argument("id", None)
            item_id = int(decrypt_id(item_fuzzy_id))
            # pan_id = int(self.get_argument("panid", "0"))
            source = self.get_argument("source", "")
            rs = sync_pan_service.clear(item_id, source)
            self.to_write_json(rs)
        elif path.endswith("/clearbyid"):
            item_id = int(self.get_argument("id", "0"))
            # pan_id = int(self.get_argument("panid", "0"))
            source = self.get_argument("source", "")
            logger.info("clearbyid item_id:{}, source:{}".format(item_id, source))
            rs = sync_pan_service.clear(item_id, source)
            logger.info("clearbyid rs:{}".format(rs))
            self.to_write_json(rs)
        elif path.endswith("/rename"):
            item_fuzzy_id = self.get_argument("itemid", None)
            item_id = int(decrypt_id(item_fuzzy_id))
            old_name = self.get_argument("old_name", "")
            alias_name = self.get_argument("alias_name", "")
            source = self.get_argument("source", "")
            result = sync_pan_service.rename(item_id, old_name, alias_name, source)
            self.to_write_json(result)

        elif path.endswith("/free"):
            item_fuzzy_id = self.get_argument("itemid", None)
            item_id = int(decrypt_id(item_fuzzy_id))
            source = self.get_argument("source", "")
            desc = self.get_argument("desc", "")
            tags = self.get_argument("tags", "")
            if tags:
                tags = tags.split(',')
            else:
                tags = []
            if "local" != source:
                self.to_write_json({"state": -1})
            else:
                rs = mpan_service.free(self.user_id, item_id, desc, tags)
                self.to_write_json(rs)
        elif path.endswith("/unfree"):
            item_fuzzy_id = self.get_argument("itemid", None)
            item_id = int(decrypt_id(item_fuzzy_id))
            fs_id = self.get_argument("fs_id", "")
            source = self.get_argument("source", "")
            tags = self.get_argument("tags", "")
            if tags:
                tags = tags.split(',')
            else:
                tags = []
            if "local" != source:
                self.to_write_json({"state": -1})
            else:
                rs = mpan_service.unfree(self.user_id, item_id, fs_id, tags)
                self.to_write_json(rs)

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
        elif path.endswith("/pan_acc_list"):
            need_renew_pan_acc = pan_service.all_pan_acc_list_by_user(self.user_id)
            result = {"result": "ok", "pan_acc_list": need_renew_pan_acc}
            # print("result:", result)
            self.to_write_json(result)
        elif path.endswith("/batchupdate"):
            pan_id = self.get_argument("panid", "0")
            pan_acc = pan_service.get_pan_account(pan_id, self.user_id)
            # "server_ctime",
            #                                              "account_id", "panacc", "sized", "synced", "thumb"
            cls = [fn for fn in DataItem.field_names() if fn not in ["id", "created_at",
                                                                     "updated_at", "pan_acc",
                                                                     "account_id", "dlink_updated_at",
                                                                     "server_ctime", "account_id",
                                                                     "panacc"]]
            params = {"pan_id": int(pan_id), "name": pan_acc.name, "columns": cls, "tablename": ""}

            self.render('batchupdate.html', **params)
        elif path.endswith("/batchupdatedo"):
            pan_id = self.get_argument("panid", "0")
            cname = self.get_argument("cname")
            datas = self.get_argument("datas", "")
            lines = datas.split("\n")
            kv = {}
            cnt = 0
            for line in lines:
                vals = line.split("\t")
                if len(vals) == 2:
                    cnt = cnt + 1
                    kv[vals[0]] = vals[1]
                    DataDao.update_data_item(int(vals[0]), {cname: vals[1].strip()})
                    # print("update id:", vals[0], ",", cname, "=", vals[1])
            rs = {"state": 0, "cnt": cnt, "lines_cnt": len(lines), "cname": cname}
            # print("kv:", kv)
            # print("cnt:", cnt, ",lines cnt:", len(lines), "cname:", cname, "pan_id:", pan_id)
            self.to_write_json(rs)
        elif path.endswith("/updateitem"):
            fs_id = self.get_argument("fs_id", "")
            source = self.get_argument("source", "")
            cname = self.get_argument("cname")
            value = self.get_argument("value")
            _params = {cname: value}
            rs = mpan_service.update_item_fields(source, fs_id, _params)
            rs["params"] = _params
            rs["source"] = source
            rs["fs_id"] = fs_id
            self.to_write_json(rs)
        elif path.endswith("/newessay"):
            rs = {"state": 0}
            title = self.get_argument("title", "")
            authors = self.get_argument("authors", "")
            info = self.get_argument("info", "")
            idx = self.get_argument("idx", "0")
            tag = self.get_argument("tag", "")
            description = self.get_argument("description", "")
            txt = self.get_argument("txt", "")
            py = self.get_argument("py", "")
            cap = self.get_argument("cap", "")
            bs = self.get_argument("bs", "")
            sds = self.get_argument("sds", "")
            num = self.get_argument("num", "0")
            struct = self.get_argument("struct", "")
            demo = self.get_argument("demo", "")
            worder = self.get_argument("worder", "")
            zc = self.get_argument("zc", "")
            zy = self.get_argument("zy", "")
            gif_file = None
            # print("files:", self.request.files)
            if self.request.files:
                gif_file_metas = self.request.files["gif"]
                if gif_file_metas:
                    for meta in gif_file_metas:
                        file_name = meta['filename']
                        print("file_name:", file_name)
                        gif_file = meta['body']

            #  title, authors, info, idx, tag, description, txt, py, cap, bs, sds, num, struct, demo, worder, zc, zy, txt_gif
            if txt and title:
                mpan_service.newessay(title, authors, info, idx, tag, description, txt, py, cap, bs, sds, num, struct, demo, worder, zc, zy, gif_file, self.context)
            else:
                rs['errmsg'] = "txt:{},title:{}".format(txt, title)
                rs['state'] = -1
            self.to_write_json(rs)
        else:
            self.to_write_json({})

    def post(self):
        self.get()

