# -*- coding: utf-8 -*-
"""
Created by susy at 2020/1/6
"""
from controller.base_service import BaseService
from utils import singleton, log, guess_file_type
from dao.community_dao import CommunityDao
from dao.dao import DataDao
from utils.utils_es import SearchParams, build_query_item_es_body
from dao.es_dao import es_dao_share, es_dao_local
from dao.models import DataItem
from utils.constant import TOP_DIR_FILE_NAME, SHARE_ES_TOP_POS
from utils import scale_size
import sys
sys.setrecursionlimit(1000000)

@singleton
class MPanService(BaseService):

    def fetch_root_item_by_user(self, user_id):
        root_item_ms = DataDao.get_root_item_by_user_id(user_id)
        params = []
        for item in root_item_ms:
            _item_path = item.path
            pan = item.pan
            params.append({"id": item.id, "text": pan.name, "data": {"path": _item_path, "_id": item.id,
                                                                     "server_ctime": item.server_ctime, "isdir": 1,
                                                                     "source": 'local'}, "children": True,
                           "icon": "jstree-folder"})
        return params

    def query_file_list(self, parent_item_id):
        # item_list = CommunityDao.query_data_item_by_parent(parent_item_id, True, pan_id, limit=1000)
        params = []
        # for item in item_list:
        #     _item_path = item.path
        #     params.append({"id": item.id, "text": item.filename, "data": {"path": _item_path,
        #                                                                   "server_ctime": item.server_ctime,
        #                                                                   "isdir": item.isdir, "source": 'local'},
        #                    "children": True, "icon": "folder"})
        # print("dirs total:", len(params))

        sp: SearchParams = SearchParams.build_params(0, 1000)
        # sp.add_must(is_match=False, field="path", value=parent_path)

        sp.add_must(is_match=False, field="parent", value=parent_item_id)
        # sp.add_must(is_match=False, field="isdir", value=0)
        # if pan_id and pan_id > 0:
        #     sp.add_must(is_match=False, field="sourceid", value=pan_id)
        es_body = build_query_item_es_body(sp)
        print("local es_body:", es_body)
        es_result = es_dao_local().es_search_exec(es_body)
        hits_rs = es_result["hits"]
        total = hits_rs["total"]
        print("local files es total:", total)

        for _s in hits_rs["hits"]:
            icon_val = "jstree-file"
            fn_name = _s["_source"]["filename"]
            has_children = False
            a_attr = {}
            if _s["_source"]["pin"] == 1:
                a_attr = {'style': 'color:red'}
            if _s["_source"]["isdir"] == 1:
                icon_val = "jstree-folder"
                has_children = True
            else:
                f_type = guess_file_type(fn_name)
                if f_type:
                    icon_val = "jstree-file jstree-file-%s" % f_type
            node_text = _s["_source"]["filename"]
            format_size = scale_size(_s["_source"]["size"])
            if format_size:
                node_text = "{}({})".format(node_text, format_size)

            node_param = {"id": _s["_source"]["id"], "text": node_text,
                          "data": {"path": _s["_source"]["path"], "server_ctime": _s["_source"].get("server_ctime", 0),
                                   "isdir": _s["_source"]["isdir"], "source": _s["_source"]["source"],
                                   "pin": _s["_source"]["pin"], "_id": _s["_source"]["id"], "p_id": _s["_source"]["id"]}, "children": has_children, "icon": icon_val}
            if a_attr:
                node_param['a_attr'] = a_attr
            params.append(node_param)
        return params

    def query_share_list(self, parent_item_id):
        params = []
        sp: SearchParams = SearchParams.build_params(0, 1000)
        # sp.add_must(is_match=False, field="path", value=parent_path)
        if parent_item_id:
            sp.add_must(is_match=False, field="parent", value=parent_item_id)
        else:
            sp.add_must(is_match=False, field="pos", value=SHARE_ES_TOP_POS)
        # sp.add_must(is_match=False, field="isdir", value=0)
        es_body = build_query_item_es_body(sp)
        print("query_share_list es_body:", es_body)
        es_result = es_dao_share().es_search_exec(es_body)
        hits_rs = es_result["hits"]
        total = hits_rs["total"]
        print("query_share_list files es total:", total)
        for _s in hits_rs["hits"]:
            icon_val = "jstree-file"
            fn_name = _s["_source"]["filename"]
            has_children = False
            a_attr = {}
            if _s["_source"]["isdir"] == 1:
                icon_val = "jstree-folder"
                has_children = True
                if _s["_source"]["pin"] == 1:
                    a_attr = {'style': 'color:red'}
            else:
                f_type = guess_file_type(fn_name)
                if f_type:
                    icon_val = "jstree-file file-%s" % f_type
            node_text = _s["_source"]["filename"]
            format_size = scale_size(_s["_source"]["size"])
            if format_size:
                if _s["_source"]["isdir"] == 1:
                    node_text = "{}(shared)({})".format(node_text, format_size)
                else:
                    node_text = "{}({})".format(node_text, format_size)
            node_param = {"id": "s_%s" % _s["_source"]["id"], "text": node_text,
                          "data": {"path": _s["_source"]["path"], "fs_id": _s["_source"]["fs_id"],
                                   "server_ctime": _s["_source"].get("server_ctime", 0),
                                   "isdir": _s["_source"]["isdir"], "source": _s["_source"]["source"],
                                   "pin": _s["_source"]["pin"], "_id": _s["_source"]["id"], "p_id": _s["_source"]["fs_id"]},
                          "children": has_children, "icon": icon_val}
            if a_attr:
                node_param['a_attr'] = a_attr
            params.append(node_param)
        return params

    def update_local_item(self, doc_id, params):
        if doc_id:
            CommunityDao.new_local_visible(doc_id, params['pin'])
            es_dao_local().update_fields(doc_id, **params)

    def update_local_sub_dir(self, parent_id, params):
        if parent_id:
            print("local visible parent_id:",parent_id,",params:", params)
            CommunityDao.new_local_visible_by_parent(parent_id, params['pin'])
            sp: SearchParams = SearchParams.build_params(0, 1000)
            sp.add_must(is_match=False, field="parent", value=parent_id)
            # sp.add_must(is_match=False, field="isdir", value=1)
            es_body = build_query_item_es_body(sp)
            es_dao_local().update_by_query(es_body, params)

    def update_shared_item(self, doc_id, params):
        if doc_id:
            CommunityDao.new_community_visible(doc_id, params['pin'])
            es_dao_share().update_fields(doc_id, **params)

    def update_shared_sub_dir(self, parent_id, params):
        if parent_id:
            CommunityDao.new_community_visible_by_parent(parent_id, params['pin'])
            sp: SearchParams = SearchParams.build_params(0, 1000)
            sp.add_must(is_match=False, field="parent", value=parent_id)
            sp.add_must(is_match=False, field="isdir", value=1)
            es_body = build_query_item_es_body(sp)
            es_dao_share().update_by_query(es_body, params)

    def update_dir_size(self, data_item: DataItem, recursive=False, reset_sub_dir=True):
        if not data_item or data_item.filename == TOP_DIR_FILE_NAME or data_item.isdir == 0:
            return
        data_item_dict = DataItem.to_dict(data_item)
        rs = self.update_dir_size_by_dict(data_item_dict, recursive, reset_sub_dir)
        data_item.size = data_item_dict['size']
        data_item.sized = data_item_dict['sized']
        return rs

    def update_dir_size_by_dict(self, data_item: dict, recursive=False, reset_sub_dir=True):
        if data_item['filename'] == TOP_DIR_FILE_NAME or data_item['isdir'] == 0:
            return

        def recover_sized_zero(parent_id):
            DataDao.update_data_item_by_parent_id(parent_id, {'sized': 0})
            if recursive:
                size = 100
                offset = 0
                rs_len = 100
                while rs_len == size:
                    sub_dir_list = DataDao.query_data_item_by_parent(parent_id, offset=offset, limit=size)
                    rs_len = len(sub_dir_list)
                    for s_dir in sub_dir_list:
                        recover_sized_zero(s_dir.id)

        def recursive_check_dir_size(dir_list: list, pos, rs: dict):
            if pos >= len(dir_list):
                return rs
            p_dir_dict = dir_list[pos]
            p_dir_id = p_dir_dict['id']
            sub_dir: DataItem = DataDao.find_need_update_size_dir(parent_id=p_dir_dict['id'])
            if sub_dir:
                recursive_check_dir_size([DataItem.to_dict(sub_dir)], 0, rs)
                recursive_check_dir_size(dir_list, pos, rs)
            else:
                ori_size = p_dir_dict['size']
                s: int = DataDao.sum_size_dir(parent_id=p_dir_id)
                if not p_dir_dict['sized'] or s != ori_size:
                    rs['change'] = True
                    DataDao.update_data_item(p_dir_id, {'size': s, 'sized': 1})
                    p_dir_dict['size'] = s
                    p_dir_dict['sized'] = 1
                    print("changed:", True)
                print('dir id:', p_dir_dict['id'], ',size:', s, ',ori_size:', ori_size)
                recursive_check_dir_size(dir_list, pos+1, rs)
        if reset_sub_dir:
            recover_sized_zero(data_item['id'])
        _rs = {'change': False}
        recursive_check_dir_size([data_item], 0, _rs)
        print("_rs['change']:", _rs['change'], data_item['parent'])
        if _rs['change']:
            _data_item: dict = None
            _data_item = data_item
            while _data_item['parent']:
                p_data_item: DataItem = DataDao.get_data_item_by_id(_data_item['parent'])
                if p_data_item and p_data_item.filename != TOP_DIR_FILE_NAME:
                    _ori_size = p_data_item.size
                    _s: int = DataDao.sum_size_dir(parent_id=p_data_item.id)
                    print('upate parent dir id:', p_data_item.id, ',size:', _s, ',ori_size:', _ori_size)
                    if _s != _ori_size:
                        DataDao.update_data_item(p_data_item.id, {'size': _s, 'sized': 1})
                    else:
                        break
                    _data_item = DataItem.to_dict(p_data_item)
                else:
                    break
        return _rs['change']


mpan_service = MPanService()
