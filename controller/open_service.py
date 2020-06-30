# -*- coding: utf-8 -*-
"""
Created by susy at 2019/12/18
"""
from controller.base_service import BaseService
from controller.async_service import async_service
from utils import singleton, log as logger, compare_dt_by_now, get_now_datetime_format, scale_size, split_filename, \
    obfuscate_id
from dao.models import Accounts, DataItem, ShareLogs, ShareFr, ShareApp, AppCfg, AuthUser, BASE_FIELDS, StudyBook
from utils.utils_es import SearchParams, build_query_item_es_body
from dao.es_dao import es_dao_share, es_dao_local
from dao.community_dao import CommunityDao
from dao.mdao import DataDao
from dao.auth_dao import AuthDao
from dao.study_dao import StudyDao
from utils.caches import cache_data, cache_service
from utils.constant import shared_format, SHARED_FR_MINUTES_CNT, SHARED_FR_HOURS_CNT, SHARED_FR_DAYS_CNT, \
    SHARED_FR_DAYS_ERR, SHARED_FR_HOURS_ERR, SHARED_FR_MINUTES_ERR, MAX_RESULT_WINDOW, SHARED_BAN_ERR, \
    SHARED_NOT_EXISTS_ERR
from controller.sync_service import sync_pan_service
from controller.service import pan_service
from controller.auth_service import auth_service
from cfg import EPUB
import time
import zipfile
import traceback

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
                    if share_log.is_black == 1:
                        rs = {'state': -9, 'info': share_log.err}
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
                    # if not path_tag and not kw:
                    if not path_tag:
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
        if kw:
            es_body = build_query_item_es_body(sp)
        else:
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
                    aliasname = "{}{}".format(alias_fn, "." + alias_extname if alias_extname.strip() else "")
                    fn_name = "[{}]{}".format(fn_name, aliasname)
                item = {'filename': "%s(%s)" % (fn_name, scale_size(_s["_source"]["size"])),
                        'path': _s["_source"]["path"], 'source': _s["_source"]["source"],
                        'isdir': _s["_source"]["isdir"],
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

    def unzip_single(self, src_file, dest_dir):
        zf = None
        try:
            zf = zipfile.ZipFile(src_file)
            zf.extractall(path=dest_dir)
        except zipfile.BadZipFile as e:
            if str(e).startswith("Bad CRC-32 for file"):
                print("Bad CRC-32 for file, so ignore this error![{}]".format(src_file))
            else:
                raise e
        except Exception as e:
            # traceback.print_exc()
            raise e
        finally:
            if zf:
                zf.close()

    def find_file(self, file_starts, root_dir):
        import os
        cover_file_path = None
        if os.path.exists(root_dir):
            find = False
            for root, sub_dirs, files in os.walk(root_dir):
                for special_file in files:
                    for _start in file_starts:
                        if special_file.startswith(_start):
                            cover_file_path = os.path.join(root_dir, special_file)
                            find = True
                            break
                    if find:
                        break
                if find:
                    break
        return cover_file_path

    def find_file_by_end(self, file_end, root_dir):
        import os
        cover_file_path = None
        if os.path.exists(root_dir):
            find = False
            for root, sub_dirs, files in os.walk(root_dir):
                for special_file in files:
                    if special_file.endswith(file_end):
                        cover_file_path = os.path.join(root_dir, special_file)
                        find = True
                        break
                if find:
                    break
        return cover_file_path

    def unzip_epub(self, ctx, books: list):
        import os
        epub_dir = EPUB["dir"]
        base_dir = ctx["basepath"]
        if base_dir:
            dest_dir = os.path.join(base_dir, EPUB["dest"])
        else:
            dest_dir = EPUB["dest"]
        print("unzip epub in...")
        if books:
            sb: StudyBook = None
            need_up_unziped = []
            for sb in books:
                file_name = sb.name  # "{}{}".format(sb.name, ".epub")
                file_path = os.path.join(epub_dir, file_name)

                if os.path.exists(file_path):
                    # print("exist file_path:", file_path)
                    current_dest_dir = os.path.join(dest_dir, sb.code)
                    if not os.path.exists(current_dest_dir):
                        os.makedirs(current_dest_dir)

                        try:
                            self.unzip_single(file_path, current_dest_dir)
                            ops_dir = os.path.join(current_dest_dir, "OPS/")
                            if not os.path.exists(ops_dir):
                                ops_dir = os.path.join(current_dest_dir, "OEBPS/")
                            if os.path.exists(ops_dir):

                                cover_dir = os.path.join(ops_dir, "images/")
                                cover_file_path = self.find_file(["cover.j", "cover.png"], cover_dir)
                                if not cover_file_path:
                                    cover_file_path = self.find_file(["cover.j", "cover.png"], ops_dir)
                                    if not cover_file_path:
                                        cover_file_path = self.find_file(["cover.j", "cover.png"], current_dest_dir)
                                opf_file_path = self.find_file_by_end(".opf", ops_dir)
                                if not opf_file_path:
                                    opf_file_path = self.find_file_by_end(".opf", current_dest_dir)
                                params = {"pin": 1, "unziped": 1}
                                if cover_file_path:
                                    params["cover"] = cover_file_path
                                if opf_file_path:
                                    params["opf"] = opf_file_path
                                print("unzip ok, name:", sb.name)
                                StudyDao.update_books_by_id(params, sb.id)
                                print("update pin=1 unziped=1 ok, name:", sb.name)
                                # del file
                                # os.remove(file_path)
                            else:
                                StudyDao.update_books_by_id({"pin": 3}, sb.id)
                        except Exception:
                            need_up_unziped.append(sb.code)
                            # os.remove(file_path)
                            try:
                                if os.path.exists(current_dest_dir):
                                    # os.removedirs(current_dest_dir)
                                    os.rmdir(current_dest_dir)
                            except Exception:
                                logger.error("remove err epud extract dir [{}] failed!".format(current_dest_dir))
                else:
                    print("not exist !!! file_path:", file_path)
            if need_up_unziped:
                print("will batch_update_books_by_codes:", need_up_unziped)
                StudyDao.batch_update_books_by_codes({"pin": 2, "unziped": 1}, need_up_unziped)

    def scan_epub(self, ctx, guest: Accounts):
        def final_do():
            pass

        def unzip_epub(books: list):
            self.unzip_epub(ctx, books)

        def to_do(key, rs_key):
            import os
            import random
            import time
            from pypinyin import lazy_pinyin, Style
            _result = {'state': 0}
            default_price = 2
            epub_dir = EPUB["dir"]
            au: AuthUser = guest.auth_user

            code_map = {}
            code_list = []
            for root, sub_dirs, files in os.walk(epub_dir):
                for special_file in files:
                    if special_file.lower().endswith(".epub"):
                        # check
                        nm = special_file[:-5]
                        gen_code_nm = nm
                        if len(gen_code_nm) > 25:
                            gen_code_nm = gen_code_nm[-25:]
                        code = "".join(lazy_pinyin(gen_code_nm, style=Style.TONE3))
                        code_map[code] = {"code": code, "name": special_file, "price": default_price, "pin": 0,
                                          "account_id": guest.id, "ref_id": au.ref_id, "unziped": 0}
                        code_list.append(code)

            if code_list:
                print("insert new book start time:", time.time())
                tl = len(code_list)
                size = 50
                page = 0
                offset = page * size
                while offset < tl:
                    sub_codes = code_list[offset: offset + size]
                    sb_list = StudyDao.check_out_study_books(sub_codes)
                    sub_new_books = []
                    db_sb_list_map = {}
                    if sb_list:
                        for sb in sb_list:
                            db_sb_list_map[sb.code] = sb
                    for code in sub_codes:
                        sb_dict = code_map[code]
                        sb = None
                        if code in db_sb_list_map:
                            sb = db_sb_list_map[code]
                            nm = sb_dict['name']
                            if sb.name == nm:
                                continue
                            else:
                                dog = 10
                                code = "{}_{}".format(code, random.randint(1, 10))
                                _sb = StudyDao.check_out_study_book(code)
                                while _sb and not (_sb.name == nm) and dog > 0:
                                    dog = dog - 1
                                    code = "{}_{}".format(code, random.randint(1, 10))
                                    _sb = StudyDao.check_out_study_book(code)
                                if not _sb:
                                    sb_dict["code"] = code
                                    sub_new_books.append(sb_dict)
                        else:
                            sub_new_books.append(sb_dict)
                    if sub_new_books:
                        StudyDao.batch_insert_books(sub_new_books)
                    page = page + 1
                    offset = page * size
                print("insert new book end time:", time.time())
            # check_ziped_books
            StudyDao.check_ziped_books(0, 0, callback=unzip_epub)
            # print("epub_new_books:", epub_new_books)
            return _result

        # to_do()
        key_prefix = "epud:ready:"
        async_service.init_state(key_prefix, guest.id, {"state": 0, "pos": 0})
        async_rs = async_service.async_checkout_thread_todo(key_prefix, guest.id, to_do, final_do)
        return async_rs


open_service = OpenService()
