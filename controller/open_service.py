# -*- coding: utf-8 -*-
"""
Created by susy at 2019/12/18
"""
from controller.base_service import BaseService
from utils import singleton, log as logger, compare_dt_by_now, get_now_datetime_format, scale_size, split_filename, \
    obfuscate_id
from dao.models import Accounts, DataItem, ShareLogs, ShareFr, ShareApp, AppCfg, AuthUser, BASE_FIELDS
from utils.utils_es import SearchParams, build_query_item_es_body
from dao.es_dao import es_dao_share, es_dao_local
from dao.community_dao import CommunityDao
from dao.mdao import DataDao
from dao.auth_dao import AuthDao
from utils.caches import cache_data, cache_service
from utils.constant import shared_format, SHARED_FR_MINUTES_CNT, SHARED_FR_HOURS_CNT, SHARED_FR_DAYS_CNT, \
    SHARED_FR_DAYS_ERR, SHARED_FR_HOURS_ERR, SHARED_FR_MINUTES_ERR, MAX_RESULT_WINDOW, SHARED_BAN_ERR, \
    SHARED_NOT_EXISTS_ERR
from controller.sync_service import sync_pan_service
from controller.service import pan_service
from controller.auth_service import auth_service
import time
ONE_DAY_SECONDS_TOTAL = 24 * 60 * 60


@singleton
class OpenService(BaseService):

    apps_map = {}

    def sync_community_item_to_es(self, acc_id, datas):
        source = datas['source']
        sourceid = datas['sourceid']
        sourceuid = datas['sourceuid']
        dir_datas = datas['datas']
        for dir_data in dir_datas:
            CommunityDao.new_community_item(acc_id, source, sourceid, sourceuid, dir_data)
            # print("acc_id:{},source:{},sourceid:{},sourceuid:{},dir_data:{}".format(acc_id, source, sourceid, sourceuid, dir_data))
        # log.debug("datas:{}".format(datas))
        time.sleep(1)

    def build_shared_log(self, item: DataItem):
        fs_id = item.fs_id
        pan_id = item.panacc
        share_logs = CommunityDao.query_share_logs_by_fs_id(fs_id)
        rs = {}
        share_log: ShareLogs = None
        if share_logs:
            for sl in share_logs:
                if not sl.link:
                    sync_pan_service.clear_share_log(sl.id)
                    continue
                if abs(compare_dt_by_now(sl.created_at)) < ONE_DAY_SECONDS_TOTAL:
                    share_log = sl
                    rs = {'state': 0, 'sl': shared_format(sl.link, sl.password)}
                    break
                else:
                    sync_pan_service.clear_share_log(sl.id)
        if not rs:
            # check share fr
            sharefrs = CommunityDao.get_fr_by_pan_id(pan_id)
            permit = False
            sharefr: ShareFr = None
            if sharefrs:
                sharefr = sharefrs[0]
                if sharefr.dcnt < SHARED_FR_DAYS_CNT and sharefr.hcnt < SHARED_FR_HOURS_CNT and sharefr.mcnt < SHARED_FR_MINUTES_CNT:
                    permit = True
                else:
                    if sharefr.dcnt < SHARED_FR_DAYS_CNT:
                        rs = {'err': SHARED_FR_DAYS_ERR}
                    elif sharefr.hcnt < SHARED_FR_HOURS_CNT:
                        rs = {'err': SHARED_FR_HOURS_ERR}
                    elif sharefr.mcnt < SHARED_FR_MINUTES_CNT:
                        rs = {'err': SHARED_FR_MINUTES_ERR}
            else:
                permit = True
            if permit:
                m_val = int(get_now_datetime_format('MMDDHHmm'))
                h_val = int(get_now_datetime_format('MMDDHH'))
                d_val = int(get_now_datetime_format('MMDD'))
                dict_obj, share_log, data_item = pan_service.share_folder(fs_id)
                if share_log:
                    if share_log.is_black == 1:
                        rs = {'state': 0, 'info': share_log.err}
                    else:
                        rs = {'state': 0, 'info': shared_format(share_log.link, share_log.password)}
                        self.update_share_fr(m_val, h_val, d_val, pan_id, sharefr)

        return rs, share_log

    @cache_data("check_free_permit_{1}", timeout_seconds=ONE_DAY_SECONDS_TOTAL)
    def check_free_item_permit(self, fs_id):
        item: DataItem = DataDao.query_data_item_by_fs_id(fs_id)
        if item:
            if not CommunityDao.local_check_free_by_id(item):
                return {'state': -1, 'err': SHARED_BAN_ERR}
            else:
                rs = DataItem.to_dict(item, BASE_FIELDS + DataItem.field_names() -
                                      ["id", "fs_id", "parent", "account_id", "panacc"])
                rs['state'] = 0
                return rs
        else:
            return {'state': -1, 'err': SHARED_NOT_EXISTS_ERR}

    def fetch_shared(self, fs_id):
        # print('fs_id:', fs_id)
        # item: DataItem = DataDao.query_data_item_by_fs_id(fs_id)
        # if item:
        #     if not CommunityDao.local_check_free_by_id(item):
        #         return {'state': -1, 'err': SHARED_BAN_ERR}
        item_dict = self.check_free_item_permit(fs_id)
        if item_dict['state'] == 0:
            item = DataItem(id=item_dict['id'], fs_id=item_dict['fs_id'], panacc=item_dict['panacc'],
                            parent=item_dict['parent'], account_id=item_dict['account_id'])
            rs, share_log = self.build_shared_log(item)
        else:
            rs = item_dict
        return rs

    def fetch_shared_skip_visible(self, fs_id):
        # print('fs_id:', fs_id)
        item: DataItem = DataDao.query_data_item_by_fs_id(fs_id)
        if not item:
            return {'state': -1, 'err': SHARED_NOT_EXISTS_ERR}
        rs, _ = self.build_shared_log(item)
        return rs

    def update_share_fr(self, m_val, h_val, d_val, pan_id, sharefr):

        if sharefr:
            params = dict(minutes=m_val, mcnt=sharefr.mcnt, hours=h_val, hcnt=sharefr.hcnt, days=d_val,
                          dcnt=sharefr.dcnt)
            if sharefr.days == d_val:
                sharefr.dcnt = sharefr.mcnt + 1
                if sharefr.hours == h_val:
                    sharefr.hcnt = sharefr.hcnt + 1
                    if sharefr.minutes == m_val:
                        sharefr.mcnt = sharefr.mcnt + 1
                    else:
                        sharefr.mcnt = 1
                else:
                    sharefr.hcnt = 1
                    sharefr.mcnt = 1
            else:
                sharefr.dcnt = 1
                sharefr.hcnt = 1
                sharefr.mcnt = 1
            CommunityDao.update_share_fr_by_pk(sharefr.id, params)
        else:
            params = dict(minutes=m_val, mcnt=1, hours=h_val, hcnt=1, days=d_val, dcnt=1)
            CommunityDao.new_share_fr(pan_id, params)

    def get_app_by_id(self, app_id):
        if app_id not in self.apps_map:
            # print("to query app id!!!!!", app_id)
            sa = CommunityDao.query_app_info(app_id)
            if sa:
                self.apps_map[app_id] = sa.name
                # print('sa name:', sa.name)
        if app_id in self.apps_map:
            return self.apps_map[app_id]

        return None

    def search(self, path_tag, tag, keyword, source, pid, page, size=50, lvl_pos=2):
        _app_map_cache = {}
        if not source:
            source = 'shared'
        # kw = keyword.replace(' ', '%')
        l_kw = keyword.lower()
        pos = 0
        idx = l_kw.find("or", pos)
        _kw_secs = []
        while idx >= pos:
            s = keyword[pos:idx]
            _s = s.strip()
            _s_arr = _s.split(' ')
            _arr = [a for a in _s_arr if len(a) > 0]
            _s = " AND ".join(_arr)
            _kw_secs.append(_s)
            pos = idx + 2
            idx = l_kw.find("or", pos)
        if pos < len(l_kw):
            s = keyword[pos:]
            _s = s.strip()
            _s_arr = _s.split(' ')
            _arr = [a for a in _s_arr if len(a) > 0]
            _s = " AND ".join(_arr)
            _kw_secs.append(_s)
        # print("_kw_secs:", _kw_secs)
        if _kw_secs:
            new_keyword = " OR ".join(_kw_secs)
        else:
            new_keyword = keyword
        kw = new_keyword
        # print("kw:", kw)
        # size = 50
        offset = int(page) * size
        if offset > MAX_RESULT_WINDOW - size:
            offset = MAX_RESULT_WINDOW - size
        sp: SearchParams = SearchParams.build_params(offset, size)
        es_dao_fun = es_dao_local
        if kw:
            # sp.add_must(value=kw)
            # sp.add_must(False, field='query_string', value="\"%s\"" % kw)
            sp.add_must(False, field='query_string', value="%s" % kw)
        _sort_fields = None
        if source:
            if "local" == source:
                es_dao_fun = es_dao_local
                sp.add_must(is_match=False, field='isdir', value=0)
                _sort_fields = [{"pin": {"order": "desc"}}]
            else:
                sp.add_must(field='source', value=source)
                # sp.add_must(field='pin', value=1)
                if pid:
                    sp.add_must(field='parent', value=pid)
                    _sort_fields = [{"filename": {"order": "asc"}}]
                else:
                    if not path_tag and not kw:
                        if lvl_pos and lvl_pos > 0:
                            sp.add_must(field='pos', value=lvl_pos)
                        _sort_fields = [{"parent": {"order": "desc"}}, {"filename": {"order": "asc"}}]
                    else:
                        _sort_fields = [{"pos": {"order": "asc"}}, {"filename": {"order": "asc"}}]
                es_dao_fun = es_dao_share
        # if tag and "local" != source:
        #     sp.add_must(field='all', value=tag)
        if tag:
            # sp.add_must(False, field='query_string', value="\"%s\"" % tag)
            sp.add_must(False, field='query_string', value="%s" % tag)
        if path_tag:
            sp.add_must(field='path', value="%s" % path_tag)

        es_body = build_query_item_es_body(sp, sort_fields=_sort_fields)
        logger.info("es_body:{}".format(es_body))
        es_result = es_dao_fun().es_search_exec(es_body)
        total = 0
        # datas = [_s["_source"] for _s in hits_rs["hits"]]
        datas = []
        if es_result:
            hits_rs = es_result["hits"]
            total = hits_rs["total"]
            for _s in hits_rs["hits"]:
                app_name = '-'
                source = _s["_source"]["source"]
                if not "local" == source:
                    if 'extuid' in _s["_source"]:
                        app_id = _s["_source"]["extuid"]
                        if app_id in _app_map_cache:
                            app_name = _app_map_cache[app_id]
                        else:
                            _app_name = self.get_app_by_id(app_id)
                            if _app_name:
                                app_name = _app_name
                    _app_map_cache[app_id] = app_name
                else:
                    app_name = '#'
                fn_name = _s["_source"]["filename"]
                aliasname = None
                if "aliasname" in _s["_source"] and _s["_source"]["aliasname"]:
                    aliasname = _s["_source"]["aliasname"]
                if aliasname:
                    fn_name, extname = split_filename(fn_name)
                    alias_fn, alias_extname = split_filename(aliasname)
                    if not alias_extname:
                        alias_extname = extname
                    aliasname = "{}{}".format(alias_fn, "."+alias_extname if alias_extname.strip() else "")
                    fn_name = "[{}]{}".format(fn_name, aliasname)
                item = {'filename': "%s(%s)" % (fn_name, scale_size(_s["_source"]["size"])),
                        'path': _s["_source"]["path"], 'source': _s["_source"]["source"], 'isdir': _s["_source"]["isdir"],
                        'fs_id': _s["_source"]["fs_id"], 'pin': _s["_source"]["pin"],
                        'app_name': app_name}
                datas.append(item)
        has_next = offset + size < total
        rs = {"data": datas, "has_next": has_next, "total": total, "pagesize": size}
        return rs

    def sync_cfg(self):
        cfg_list = AppCfg.select().where(AppCfg.pin == 0)
        rs = []
        for sys_cfg in cfg_list:
            rs.append(AppCfg.to_dict(sys_cfg))
        # print("sync cfg:", rs)
        cache_service.replace('sys_cfg', rs)
        return rs

    def sync_tags(self):
        tag_list = CommunityDao.default_tags()
        cache_service.replace('sys_tags', tag_list)
        return tag_list

    def guest_user(self):
        guest: Accounts = CommunityDao.default_guest_account()
        if guest:
            if not guest.fuzzy_id or not guest.login_token:
                fuzzy_id = obfuscate_id(guest.id)
                guest.fuzzy_id = fuzzy_id
                login_token, _ = auth_service.build_user_payload(guest)
                guest.login_token = login_token
                DataDao.update_account_by_pk(guest.id, {"fuzzy_id": fuzzy_id, "login_token": login_token})
            au: AuthUser = AuthDao.query_account_auth(guest.id)
            guest.auth_user = au

        return guest

    def load_tags(self):
        tag_list = cache_service.get('sys_tags')
        if not tag_list:
            tag_list = self.sync_tags()
        return tag_list

    def checkout_app_cfg(self, platform):
        rs_key = "sys_cfg"
        val = cache_service.get(rs_key)
        # print('val from cache:', val)
        rs = []
        if val:
            for cfg in val:
                _platform = cfg.get('platform', None)
                if _platform:
                    if platform.find(_platform) >= 0:
                        rs.append(cfg)
                else:
                    rs.append(cfg)
        return rs


open_service = OpenService()
