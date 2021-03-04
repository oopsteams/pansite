# -*- coding: utf-8 -*-
"""
Created by susy at 2020/1/6
"""
from controller.base_service import BaseService
from utils import singleton, log, guess_file_type, obfuscate_id
from dao.community_dao import CommunityDao
from dao.mdao import DataDao
from dao.man_dao import ManDao
from utils.utils_es import SearchParams, build_query_item_es_body
from dao.es_dao import es_dao_share, es_dao_local
from dao.models import DataItem, UserRootCfg, PanAccounts, CommunityDataItem
from utils.constant import TOP_DIR_FILE_NAME, SHARE_ES_TOP_POS, PRODUCT_TAG, ES_TAG_MAP
from utils import scale_size, split_filename
from cfg import MASTER_ACCOUNT_ID
import traceback
import sys
sys.setrecursionlimit(1000000)

@singleton
class MPanService(BaseService):

    def fetch_root_item_by_user(self, user_id):
        pan_acc_map = {}
        if MASTER_ACCOUNT_ID == user_id:
            _pan_acc_list = DataDao.pan_account_list(user_id, 100)
            pa: PanAccounts = None
            for pa in _pan_acc_list:
                pan_acc_map[pa.id] = pa
        root_item_ms = DataDao.get_root_item_by_user_id(user_id)
        params = []
        for item in root_item_ms:
            _item_path = item.path
            pan = item.pan
            if pan.id in pan_acc_map:
                pan_acc_map.pop(pan.id)
            params.append({"id": obfuscate_id(item.id), "text": pan.name, "data": {
                "path": _item_path, "_id": obfuscate_id(item.id), "server_ctime": item.server_ctime, "isdir": 1,
                "source": 'local', "fn": "", "alias": "", "pos": 0
            }, "children": True, "icon": "folder"})
        if pan_acc_map:
            for pan_id in pan_acc_map:
                _pan = pan_acc_map[pan_id]
                _, root_item = DataDao.new_root_item(user_id, pan_id)
                params.append({"id": obfuscate_id(root_item.id), "text": _pan.name, "data": {
                    "path": root_item.path, "_id": obfuscate_id(root_item.id), "server_ctime": root_item.server_ctime, "isdir": 1,
                    "source": 'local', "fn": "", "alias": "", "pos": 0
                }, "children": True, "icon": "folder"})
        return params

    def parse_price(self, format_size, times):
        min = 0.02
        v = min
        if not times:
            times = 1
        if format_size:
            bit_list = ['B', 'K', 'M', 'G', 'T']
            bit = format_size[-1]
            v = 0
            if bit_list.index(bit) > 1:
                v = float(format_size[:-1])
                # print("v:", v, ", format_size:", format_size)
                if bit == 'M':
                    v = v / 1000
                elif bit == 'G':
                    v = v
                elif bit == 'T':
                    v = v * 1000
            if v < min:
                v = min
            v = v / times
        return "{:.2f}".format(v)

    def query_file_list(self, parent_item_id):
        # item_list = CommunityDao.query_data_item_by_parent(parent_item_id, True, pan_id, limit=1000)
        params = []
        offset = 0
        size = 1000
        sp: SearchParams = SearchParams.build_params(offset, size)
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
            ori_fn_name = _s["_source"]["filename"]
            ori_aliasname = ''
            if "aliasname" in _s["_source"] and _s["_source"]["aliasname"]:
                ori_aliasname = _s["_source"]["aliasname"]
            aliasname = ori_aliasname
            fn_name = ori_fn_name
            txt = fn_name
            if aliasname:
                fn_name, extname = split_filename(fn_name)
                alias_fn, alias_extname = split_filename(aliasname)
                if not alias_extname:
                    alias_extname = extname
                aliasname = "{}{}".format(alias_fn, "." + alias_extname if alias_extname.strip() else "")
                txt = "[{}]{}".format(fn_name, aliasname)
            is_dir = _s["_source"]["isdir"] == 1
            t_tag = ES_TAG_MAP['FREE']
            is_free = False
            tags = _s["_source"]["tags"]
            if not tags:
                tags = []
            isp = False
            has_children = False
            a_attr = {}

            if not is_dir and _s["_source"]["pin"] == 1:
                a_attr = {'style': 'color:red'}
            if PRODUCT_TAG in tags:
                if not a_attr:
                    a_attr = {'style': 'color:green'}
                isp = True
            if t_tag in tags:
                is_free = True
            if is_dir:
                # icon_val = "jstree-folder"
                icon_val = "folder"
                has_children = True
            else:
                f_type = guess_file_type(txt)
                if f_type:
                    icon_val = "jstree-file file-%s" % f_type
            node_text = txt
            format_size = scale_size(_s["_source"]["size"])
            price = self.parse_price(format_size, 2)
            if format_size:
                node_text = "{}({})".format(node_text, format_size)
            if is_free:
                node_text = "[{}]{}".format(t_tag, node_text)
                if not a_attr:
                    a_attr = {'style': 'color:green'}
            if isp:
                node_text = "[{}]{}".format(PRODUCT_TAG, node_text)
            fs_id = _s["_source"]["fs_id"]
            item_id = _s["_source"]["id"]
            item_fuzzy_id = obfuscate_id(item_id)
            node_param = {"id": item_fuzzy_id, "text": node_text,
                          "data": {"path": _s["_source"]["path"], "server_ctime": _s["_source"].get("server_ctime", 0),
                                   "isdir": _s["_source"]["isdir"], "source": _s["_source"]["source"], "fs_id": fs_id,
                                   "pin": _s["_source"]["pin"], "_id": item_fuzzy_id, "isp": isp, "tags": tags,
                                   "sourceid": _s["_source"]["sourceid"], "p_id": _s["_source"]["id"], "price": price,
                                   "fn": ori_fn_name, "alias": ori_aliasname
                                   },
                          "children": has_children, "icon": icon_val}
            if a_attr:
                node_param['a_attr'] = a_attr
            params.append(node_param)
        has_next = offset + size < total
        meta = {"has_next": has_next, "total": total, "pagesize": size}
        return params, meta

    def query_share_list(self, parent_item_id):
        params = []
        sp: SearchParams = SearchParams.build_params(0, 1000)
        # sp.add_must(is_match=False, field="path", value=parent_path)
        if parent_item_id:
            sp.add_must(is_match=False, field="parent", value=parent_item_id)
        else:
            sp.add_must(is_match=False, field="pos", value=SHARE_ES_TOP_POS)
            sp.add_must(is_match=False, field="parent", value=0)
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
            txt = fn_name
            aliasname = ''
            if "aliasname" in _s["_source"] and _s["_source"]["aliasname"]:
                aliasname = _s["_source"]["aliasname"]
            if aliasname:
                fn_name, extname = split_filename(fn_name)
                alias_fn, alias_extname = split_filename(aliasname)
                if not alias_extname:
                    alias_extname = extname
                aliasname = "{}{}".format(alias_fn, "." + alias_extname if alias_extname.strip() else "")
                txt = "[{}]{}".format(fn_name, aliasname)

            has_children = False
            a_attr = {}
            if _s["_source"]["isdir"] == 1:
                # icon_val = "jstree-folder"
                icon_val = "folder"
                has_children = True
                if _s["_source"]["pin"] == 1:
                    a_attr = {'style': 'color:red'}
            else:
                f_type = guess_file_type(txt)
                if f_type:
                    icon_val = "jstree-file file-%s" % f_type
            node_text = txt
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
                                   "pin": _s["_source"]["pin"], "_id": _s["_source"]["id"],
                                   "sourceid": _s["_source"]["sourceid"],
                                   "p_id": _s["_source"]["fs_id"]},
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
            print("local visible parent_id:", parent_id, ",params:", params)
            CommunityDao.new_local_visible_by_parent(parent_id, params['pin'])
            sp: SearchParams = SearchParams.build_params(0, 1000)
            sp.add_must(is_match=False, field="parent", value=parent_id)
            sp.add_must(is_match=False, field="isdir", value=0)
            es_body = build_query_item_es_body(sp)
            es_dao_local().update_by_query(es_body, params)

    def update_shared_item(self, doc_id, params):
        if doc_id:
            CommunityDao.new_community_visible(doc_id, params['pin'])
            es_dao_share().update_fields(doc_id, **params)

    def update_item_fields(self, source, fs_id, params):
        rs = {"state": 0}
        if "local" == source:
            di: DataItem = DataDao.query_data_item_by_fs_id(fs_id)
            if di:
                DataDao.update_data_item(di.id, params)
        elif "shared" == source:
            cdi: CommunityDataItem = CommunityDao.get_community_item_by_fs_id(fs_id)
            if cdi:
                CommunityDao.update_data_item(cdi.id, params)
        else:
            rs["err"] = "not found fs_id:{}".format(fs_id)
        return rs

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

    def unfree(self, user_id, item_id, fs_id, es_tags):
        result = {'state': 0}
        f_tag = ES_TAG_MAP['FREE']
        item_id_str = str(item_id)
        urc: UserRootCfg = ManDao.check_root_cfg_fetch(fs_id=item_id_str)
        if urc and urc.pin == 0:
            ManDao.update_root_cfg_by_id(urc.id, {'pin': 1})

        if es_tags:
            n_tags = [et for et in es_tags if et != f_tag]
            if len(n_tags) != len(es_tags):
                _params = {'tags': n_tags}
                isok = es_dao_local().update_fields(item_id, **_params)
                if not isok:
                    result['state'] = -2
                    result['errmsg'] = "索引更新失败!"
        return result

    def free(self, user_id, item_id, desc, es_tags):
        result = {'state': 0}
        f_tag = ES_TAG_MAP['FREE']
        data_item: DataItem = DataDao.get_data_item_by_id(item_id)
        item_id_str = str(item_id)
        urc: UserRootCfg = ManDao.check_root_cfg_fetch(fs_id=item_id_str)
        if urc:
            if urc.pin != 0:
                ManDao.update_root_cfg_by_id(urc.id, {'pin': 0})
                # tag free
        else:
            urc_id = ManDao.new_root_cfg(item_id_str, data_item.filename, user_id, data_item.panacc, desc)
            if not urc_id:
                result['state'] = -3
                result['errmsg'] = "新建免费资源根目录失败!"
        if es_tags:
            es_tags.append(f_tag)
        else:
            es_tags = [f_tag]
        if result['state'] == 0:
            _params = {'tags': es_tags}
            es_up_params = es_dao_local().filter_update_params(_params)
            if es_up_params:
                isok = es_dao_local().update_fields(item_id, **es_up_params)
                if not isok:
                    result['state'] = -2
                    result['errmsg'] = "索引更新失败!"
        return result

    def newessay(self, title, authors, info, idx, tag, description, txt, py, cap, bs, sds, num, struct, demo, worder, zc, zy, gif_file, ctx):

        from dao.study_dao import StudyDao
        # txt_gif = None
        try:
            essay_dict = StudyDao.query_study_essay_by_title(title)
            if essay_dict:
                # new hz
                essay_id = essay_dict['id']
                hz_idx = StudyDao.query_study_essay_hz_count(essay_id)
                txt_gif = "gif_{}_{}_{}.gif".format(essay_dict['tag'], essay_dict['idx'], hz_idx)
                hz_params = dict(txt=txt, py=py, cap=cap, bs=bs, sds=sds, num=int(num), struct=struct, demo=demo,
                                 worder=worder, zc=zc, zy=zy, txt_gif=txt_gif, idx=hz_idx)
                log.debug("hz_params:{}".format(hz_params))
                shz = StudyDao.new_study_hanzi(hz_params)
                StudyDao.new_essay_hanzi(essay_id, shz.id)
            else:
                hz_idx = 0
                # "txt", "py", "cap", "bs", "sds", "num", "struct", "demo", "worder", "zc", "zy", "txt_gif", "idx"
                txt_gif = "gif_{}_{}_{}.gif".format(tag, idx, hz_idx)
                hz_params = dict(txt=txt, py=py, cap=cap, bs=bs, sds=sds, num=int(num), struct=struct, demo=demo, worder=worder, zc=zc, zy=zy, txt_gif=txt_gif, idx=hz_idx)
                shz = StudyDao.new_study_hanzi(hz_params)
                log.debug("new eesay hz_params:{}".format(hz_params))
                # "title", "authors", "info", "hanzi", "idx", "pin", "tag", "description"
                essay_params = dict(title=title, authors=authors, info=info, idx=idx, tag=tag, description=description, hanzi=shz.id)
                log.debug("essay_params:{}".format(essay_params))
                study_essay = StudyDao.new_study_essay(essay_params)
                StudyDao.new_essay_hanzi(study_essay.id, shz.id)
            if gif_file and txt_gif:
                import os
                base_dir = ctx["basepath"]
                dest_dir = os.path.join(base_dir, "static/hz/")
                dest_file = os.path.join(dest_dir, txt_gif)
                with open(dest_file, 'wb') as up:
                    up.write(gif_file)

        except Exception:
            traceback.print_exc()
            pass


mpan_service = MPanService()
