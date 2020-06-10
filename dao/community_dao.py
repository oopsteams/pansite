# -*- coding: utf-8 -*-
"""
Created by susy at 2019/12/17
"""
from dao.models import db, Accounts, DataItem, PanAccounts, AuthUser, CommunityDataItem, UserTags, Tags, ShareLogs, \
    TransferLogs, query_wrap_db, ShareFr, LoopAdTask, AdSource, CommunityVisible, LocalVisible, ShareApp
from utils import utils_es, get_now_datetime, obfuscate_id
from dao.es_dao import es_dao_share
from cfg import CDN


class CommunityDao(object):

    # query data
    @classmethod
    @query_wrap_db
    def pan_account_list(cls, account_id=None, transfer_to_dict=True):
        if account_id:
            _pan_account_list = PanAccounts.select().where(PanAccounts.user_id == account_id)
        else:
            _pan_account_list = PanAccounts.select().order_by(PanAccounts.use_count)[0:50]
        pan_acc_list = []
        # print("pan_account_list:", _pan_account_list)
        for acc in _pan_account_list:
            if transfer_to_dict:
                pan_acc_list.append(PanAccounts.to_dict(acc))
            else:
                pan_acc_list.append(acc)
        return pan_acc_list

    @classmethod
    @query_wrap_db
    def query_data_item_by_parent(cls, parent_id, is_dir=True, panacc=0, offset=0, limit=100):
        return DataItem.select().where(DataItem.isdir == (1 if is_dir else 0), DataItem.parent == parent_id, DataItem.panacc == panacc).limit(
            limit).offset(offset)

    @classmethod
    @query_wrap_db
    def get_data_item_by_id(cls, pk_id):
        return CommunityDataItem.get_by_id(pk=pk_id)

    @classmethod
    @query_wrap_db
    def get_community_item_by_fs_id(cls, fs_id):
        return CommunityDataItem.select().where(CommunityDataItem.fs_id == fs_id).first()

    @classmethod
    @query_wrap_db
    def query_community_item_by_parent_all(cls, parent_id, offset=0, limit=100):
        return CommunityDataItem.select().where(CommunityDataItem.parent == parent_id).limit(limit).offset(offset)

    @classmethod
    @query_wrap_db
    def query_share_logs_by_hours(cls, hours, offset=0, limit=100):
        return ShareLogs.select().where(ShareLogs.updated_at < get_now_datetime(hours*60*60)).limit(limit).offset(offset)

    @classmethod
    @query_wrap_db
    def query_share_logs_by_fs_id(cls, fs_id):
        return ShareLogs.select().where(ShareLogs.fs_id == fs_id)

    @classmethod
    @query_wrap_db
    def local_check_free_by_id(cls, item: DataItem):
        permit = LocalVisible.select().where(LocalVisible.id == item.id).exists()
        dog = 20
        while item and not permit and item.parent and dog > 0:
            item = DataItem.select().where(DataItem.id == item.parent).first()
            permit = LocalVisible.select().where(LocalVisible.id == item.id).exists()
            dog = dog - 1
        return permit

    @classmethod
    @query_wrap_db
    def get_share_log_by_id(cls, pk_id):
        return ShareLogs.get_by_id(pk=pk_id)

    @classmethod
    @query_wrap_db
    def get_fr_by_pan_id(cls, pan_id):
        return ShareFr.select().where(ShareFr.pan_account_id == pan_id)

    @classmethod
    @query_wrap_db
    def query_transfer_logs_by_share_log_id(cls, share_log_id, offset=0, limit=100):
        return TransferLogs.select().where(TransferLogs.share_log_id == share_log_id).limit(limit).offset(offset)

    @classmethod
    @query_wrap_db
    def default_tags(cls, transfer_to_dict=True):
        acc_id = 1
        tag_list = UserTags.select(UserTags, Tags).join(Tags, on=(UserTags.id == Tags.id), attr='tag').where(
            UserTags.user_id == acc_id, UserTags.pin == 0).order_by(UserTags.tag_idx)

        if transfer_to_dict:
            tag_dict_list = []
            for ut in tag_list:
                ut_dict = UserTags.to_dict(ut)
                ut_dict['tag'] = Tags.to_dict(ut.tag)
                tag_dict_list.append(ut_dict)
            return tag_dict_list
        return tag_list

    @classmethod
    @query_wrap_db
    def default_guest_account(cls):
        guest: Accounts = Accounts.select().where(Accounts.name == "guest").first()
        return guest

    @classmethod
    @query_wrap_db
    def loop_ad_tasks(cls):
        rs = {}
        task: LoopAdTask = LoopAdTask.select().where(LoopAdTask.started_at <= get_now_datetime(), (LoopAdTask.ended_at.is_null()) | (LoopAdTask.ended_at > get_now_datetime()), LoopAdTask.pin == 0).first()
        if task:
            rs = LoopAdTask.to_dict(task)
            srcs = AdSource.select().where(AdSource.task_id == task.id, AdSource.pin == 0).order_by(AdSource.idx)
            if srcs:
                rs['sources'] = []
                for s in srcs:
                    s_dict = AdSource.to_dict(s)
                    rs['sources'].append(s_dict)
        rs["hosts"] = CDN["hosts"]
        return rs

    @classmethod
    @query_wrap_db
    def query_app_info(cls, app_id):
        ms: ShareApp = ShareApp.select().where(ShareApp.app_id == app_id)
        # print('ms:', ms)
        return ms.first()

    # Update
    @classmethod
    def update_share_fr_by_pk(cls, pk_id, params):
        """
        :param pk_id:
        :param params:
        :return:
        """
        _params = {p: params[p] for p in params if p in ShareFr.field_names()}
        # print("update_share_fr_by_pk _params:", _params)
        with db:
            ShareFr.update(**_params).where(ShareFr.id == pk_id).execute()

    # Del
    @classmethod
    def del_transfer_log_by_id(cls, pk_id):
        with db:
            TransferLogs.delete().where(TransferLogs.id == pk_id).execute()

    @classmethod
    def del_share_log_by_id(cls, pk_id):
        with db:
            ShareLogs.delete().where(ShareLogs.id == pk_id).execute()

    @classmethod
    def del_community_item_by_id(cls, pk_id):
        with db:
            CommunityDataItem.delete().where(CommunityDataItem.id == pk_id).execute()

    @classmethod
    def del_save_community_list(cls, item_list, show):
        if show == 1:
            with db:
                if show == 1:
                    for cdi in item_list:
                        CommunityVisible(id=cdi.id, show=1).save(force_insert=True)
                else:
                    for cdi in item_list:
                        CommunityVisible.delete().where(CommunityVisible.id == cdi.id)

    @classmethod
    def del_save_local_list(cls, item_list, show):
        if show == 1:
            with db:
                if show == 1:
                    for cdi in item_list:
                        LocalVisible(id=cdi.id, show=1).save(force_insert=True)
                else:
                    for cdi in item_list:
                        LocalVisible.delete().where(LocalVisible.id == cdi.id)

    # new data
    @classmethod
    def new_share_fr(cls, pan_id, params):
        """
        :param pan_id:
        :param params:
        :return:
        """
        sharefr = ShareFr(minutes=params['minutes'], mcnt=params['mcnt'], hours=params['hours'], hcnt=params['hcnt'],
                          days=params['days'], dcnt=params['dcnt'], pan_account_id=pan_id)
        with db:
            sharefr.save(force_insert=True)
        return sharefr

    @classmethod
    def new_community_item(cls, acc_id, source, sourceid, sourceuid, params):
        if not CommunityDataItem.select().where(CommunityDataItem.fs_id == params['id']).exists():
            data_item = CommunityDataItem(category=params['category'], isdir=params['isdir'], filename=params['filename'],
                                          fs_id=params['id'], path=params['path'], size=params['size'], account_id=acc_id,
                                          parent=params.get('parent', ''), server_ctime=params.get('server_ctime', 0),
                                          sourceid=sourceid, sourceuid=sourceuid, md5_val="",
                                          sized=params.get("sized", 1), pin=params.get("pin", 0))
            with db:
                data_item.save(force_insert=True)
                if data_item.pin == 1:
                    CommunityVisible(id=data_item.id, show=1)
            cls.sync_community_item_to_es(data_item, source)
        else:
            # print("new_community_item will update item:", params)
            data_item: CommunityDataItem = CommunityDataItem.select().where(CommunityDataItem.fs_id == params['id']).first()
            # print("data_item parent:", data_item.parent, ",size:", data_item.size)
            if data_item.parent != params.get('parent', '') or data_item.size != params.get('size', 0):
                with db:
                    CommunityDataItem.update(parent=params.get('parent', ''), size=params.get('size', 0)).where(
                        CommunityDataItem.id == data_item.id).execute()
                cls.update_es_by_community_item(data_item.id, {'parent': params.get('parent', ''),
                                                               'size': params.get('size', 0)})

    @classmethod
    def update_data_item(cls, pk_id, params):
        _params = {p: params[p] for p in params if p in CommunityDataItem.field_names()}
        with db:
            CommunityDataItem.update(**_params).where(CommunityDataItem.id == pk_id).execute()
            es_up_params = es_dao_share().filter_update_params(_params)
            if es_up_params:
                es_dao_share().update_fields(pk_id, **es_up_params)

    @classmethod
    def sync_community_item_to_es(cls, data_item: CommunityDataItem, source):
        es_item_path = data_item.path
        pos = 0
        if es_item_path.endswith(data_item.filename):
            # print("new path:", data_item.id)
            es_item_path = es_item_path[:-len(data_item.filename)]
            _p = data_item.path.strip('/')
            if _p:
                pos = len(_p.split('/'))
        body = utils_es.build_es_item_json_body(data_item.id, data_item.category, data_item.isdir, data_item.pin,
                                              data_item.fs_id, data_item.size, data_item.account_id, data_item.filename,
                                              es_item_path, data_item.server_ctime, data_item.updated_at,
                                              data_item.created_at, data_item.parent, data_item.sourceid,
                                             data_item.sourceuid, source, pos=pos)
        # es = es_dao_dir()
        es = es_dao_share()
        # print("body:", body)
        es.index(data_item.id, body)

    @classmethod
    def update_es_by_community_item(cls, doc_id, params):
        es = es_dao_share()
        es.update_fields(doc_id, **params)

    @classmethod
    def new_community_visible(cls, _id, show):
        if not CommunityVisible.select().where(CommunityVisible.id == _id).exists():
            if show == 1:
                data_item = CommunityVisible(id=_id, show=1)
                with db:
                    data_item.save(force_insert=True)
        else:
            if show == 0:
                CommunityVisible.delete().where(CommunityVisible.id == _id)

    @classmethod
    def new_community_visible_by_parent(cls, parent_id, show):
        offset = 0
        size = 500
        cdi: CommunityDataItem = None
        ln = size
        dog = 1000000
        while ln == size and dog > 0:
            dog = dog - 1
            ms = CommunityDataItem.select().where(CommunityDataItem.isdir == 1,
                                                  CommunityDataItem.parent == parent_id).offset(offset).limit(size)
            ln = len(ms)
            item_list = []
            for cdi in ms:
                rs = CommunityVisible.select().where(CommunityVisible.id == cdi.id).exists()
                if not rs:
                    if show == 1:
                        item_list.append(cdi)
                else:
                    if show == 0:
                        item_list.append(cdi)

            if item_list:
                cls.del_save_community_list(item_list, show)
            # print("dog:", dog, ",offset:", offset)
            offset = offset + size

    @classmethod
    def new_local_visible(cls, _id, show):
        if not LocalVisible.select().where(LocalVisible.id == _id).exists():
            if show == 1:
                data_item = LocalVisible(id=_id, show=1)
                with db:
                    data_item.save(force_insert=True)
        else:
            if show == 0:
                LocalVisible.delete().where(LocalVisible.id == _id)

    @classmethod
    def new_local_visible_by_parent(cls, parent_id, show):
        offset = 0
        size = 500
        cdi: DataItem = None
        ln = size
        dog = 1000000
        while ln == size and dog > 0:
            dog = dog - 1
            ms = DataItem.select().where(DataItem.parent == parent_id, DataItem.isdir == 0).offset(offset).limit(size)
            ln = len(ms)
            item_list = []
            for cdi in ms:
                rs = LocalVisible.select().where(LocalVisible.id == cdi.id).exists()
                if not rs:
                    if show == 1:
                        item_list.append(cdi)
                else:
                    if show == 0:
                        item_list.append(cdi)

            if item_list:
                cls.del_save_local_list(item_list, show)
            # print("dog:", dog, ",offset:", offset)
            offset = offset + size
