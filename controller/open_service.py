# -*- coding: utf-8 -*-
"""
Created by susy at 2019/12/18
"""
from controller.base_service import BaseService
from utils import singleton, log, compare_dt_by_now, get_now_datetime_format, scale_size
from dao.models import CommunityDataItem, DataItem, ShareLogs, ShareFr, ShareApp
from utils.utils_es import SearchParams, build_query_item_es_body
from dao.es_dao import es_dao_share, es_dao_local
from dao.community_dao import CommunityDao
from dao.dao import DataDao
from utils.constant import shared_format, SHARED_FR_MINUTES_CNT, SHARED_FR_HOURS_CNT, SHARED_FR_DAYS_CNT, \
    SHARED_FR_DAYS_ERR, SHARED_FR_HOURS_ERR, SHARED_FR_MINUTES_ERR, MAX_RESULT_WINDOW, SHARED_BAN_ERR
from controller.sync_service import sync_pan_service
from controller.service import pan_service
import time
import json


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

    def fetch_shared(self, fs_id):
        print('fs_id:', fs_id)
        item: DataItem = DataDao.query_data_item_by_fs_id(fs_id)
        if item:
            if not CommunityDao.local_check_free_by_id(item.id):
                return {'state': -1, 'err': SHARED_BAN_ERR}
        pan_id = item.panacc
        share_logs = CommunityDao.query_share_logs_by_fs_id(fs_id)
        rs = {}
        if share_logs:
            sl: ShareLogs = None
            for sl in share_logs:
                if not sl.link:
                    sync_pan_service.clear_share_log(sl.id)
                    continue
                if abs(compare_dt_by_now(sl.created_at)) < 24*60*60:
                    rs = {'state': 0, 'info': shared_format(sl.link, sl.password)}
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
                    rs = {'state': 0, 'info': shared_format(share_log.link, share_log.password)}
                    self.update_share_fr(m_val, h_val, d_val, pan_id, sharefr)

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
            print("to query app id!!!!!", app_id)
            sa = CommunityDao.query_app_info(app_id)
            if sa:
                self.apps_map[app_id] = sa.name
                print('sa name:', sa.name)
        if app_id in self.apps_map:
            return self.apps_map[app_id]

        return None

    def search(self, path_tag, tag, keyword, source, page):
        _app_map_cache = {}
        if not source:
            source = 'shared'
        # kw = keyword.replace(' ', '%')
        kw = keyword.replace(' ', ' AND ')
        size = 15
        offset = int(page) * size
        if offset > MAX_RESULT_WINDOW - size:
            offset = MAX_RESULT_WINDOW - size
        sp: SearchParams = SearchParams.build_params(offset, size)
        es_dao_fun = es_dao_local
        if kw:
            # sp.add_must(value=kw)
            # sp.add_must(False, field='query_string', value="\"%s\"" % kw)
            sp.add_must(False, field='query_string', value="%s" % kw)
        if source:
            if "local" == source:
                es_dao_fun = es_dao_local
                sp.add_must(is_match=False, field='isdir', value=0)
            else:
                sp.add_must(field='source', value=source)
                sp.add_must(field='pin', value=1)
                es_dao_fun = es_dao_share
        # if tag and "local" != source:
        #     sp.add_must(field='all', value=tag)
        if tag:
            # sp.add_must(False, field='query_string', value="\"%s\"" % tag)
            sp.add_must(False, field='query_string', value="%s" % tag)
        if path_tag:
            sp.add_must(field='path', value="%s" % path_tag)

        es_body = build_query_item_es_body(sp)
        print("es_body:", json.dumps(es_body))
        es_result = es_dao_fun().es_search_exec(es_body)
        hits_rs = es_result["hits"]
        total = hits_rs["total"]
        # datas = [_s["_source"] for _s in hits_rs["hits"]]
        datas = []
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
            item = {'filename': "%s(%s)" % (_s["_source"]["filename"], scale_size(_s["_source"]["size"])),
                    'path': _s["_source"]["path"], 'source': _s["_source"]["source"], 'isdir': _s["_source"]["isdir"],
                    'fs_id': _s["_source"]["fs_id"], 'pin': _s["_source"]["pin"],
                    'app_name': app_name}
            datas.append(item)
        has_next = offset + size < total
        rs = {"data": datas, "has_next": has_next, "total": total, "pagesize": size}
        return rs


open_service = OpenService()
