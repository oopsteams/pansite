# -*- coding: utf-8 -*-
"""
Created by susy at 2019/10/21
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), ".")))

from dao.models import db, DataItem, Accounts, CommunityDataItem, CommunityVisible
from dao.dao import DataDao
from dao.community_dao import CommunityDao
from dao.es_dao import es_dao_local, EsDao, es_dao_test, es_dao_share
from utils import utils_es
from controller.mpan_service import mpan_service
from peewee import ModelSelect


def sync_db_file_list_to_es():
    is_dir = True
    size = 100
    # size = 1
    offset = 0
    get_size = 0
    count = 0
    sql = "select * from dataitem where isdir=%s limit %s,%s" % (1, offset, size)
    print("sql:", sql)
    data_item_list = DataItem.raw(sql)

    if data_item_list:
        get_size = len(data_item_list)
        count = count + get_size
        for data_item in data_item_list:
            if data_item.sized == 0:
                mpan_service.update_dir_size(data_item, recursive=False, reset_sub_dir=False)
            DataDao.sync_data_item_to_es(data_item)
    dog = 100000
    while get_size == size and dog > 0:
        offset = offset + size
        sql = "select * from dataitem where isdir=%s limit %s,%s" % (1, offset, size)
        data_item_list = DataItem.raw(sql)
        get_size = 0
        if data_item_list:
            get_size = len(data_item_list)
            count = count + get_size
            for data_item in data_item_list:
                if data_item.sized == 0:
                    mpan_service.update_dir_size(data_item, recursive=False, reset_sub_dir=False)
                DataDao.sync_data_item_to_es(data_item)
        time.sleep(0.3)
        print("sync_dir_file_list did count:", count)
        dog = dog - 1


def test_save_item(es_obj: EsDao, data_item: DataItem):
    es_item_path = data_item.path

    if es_item_path.endswith(data_item.filename):
        # print("new path:", data_item.id)
        es_item_path = es_item_path[:-len(data_item.filename)]

    pos = data_item.id
    bd = utils_es.build_es_item_json_body(data_item.id, data_item.category, data_item.isdir, data_item.pin,
                                          data_item.fs_id, data_item.size, data_item.account_id, data_item.filename,
                                          es_item_path, data_item.server_ctime, data_item.updated_at,
                                          data_item.created_at, data_item.parent, data_item.panacc, extuid='#',
                                          source='local', pos=pos, tags=['0'])

    print("body:", bd)
    es_obj.index(data_item.id, bd)


def deal_item_list(item_list):
    cdi: CommunityDataItem = None
    print('deal len:', len(item_list))
    with db:
        for cdi in item_list:
            CommunityVisible(id=cdi.id, show=1).save(force_insert=True)
            # mpan_service.update_shared_item(cdi.id, {'pin': 1})


def update_es_community_by_visible():
    offset = 0
    size = 200
    cdi: CommunityVisible = None
    ln = size
    dog = 1000000
    while ln == size and dog > 0:
        dog = dog - 1
        ms: ModelSelect = CommunityVisible.select().offset(offset).limit(size)
        ln = len(ms)
        for cdi in ms:
            # mpan_service.update_shared_item(cdi.id, {'pin': 1})
            es_dao_share().update_fields(cdi.id, **{'pin': 1})
        print("dog:", dog, ",offset:", offset)
        offset = offset + size
        time.sleep(1)


def update_community_parent(udpate_params):
    with db:
        for p in udpate_params:
            CommunityDataItem.update(parent=p['parent']).where(CommunityDataItem.id == p['id']).execute()


def tag_es_item_show():
    offset = 0
    size = 500
    cdi: CommunityDataItem = None
    ln = size
    dog = 1000000
    while ln == size and dog > 0:
        dog = dog - 1
        ms: ModelSelect = CommunityDataItem.select().where(CommunityDataItem.isdir == 1).offset(offset).limit(size)
        ln = len(ms)
        item_list = []
        udpate_params = []
        for cdi in ms:
            # es_rs = es_dao_share().es_get(cdi.id, {"_source": 'id,fs_id,filename,parent'})
            # # print("es_rs:", es_rs)
            # if es_rs:
            #     sr = es_rs['_source']
            #     # print(sr['parent'], sr['id'])
            #     udpate_params.append({"id": cdi.id, "parent": sr['parent']})
        # if udpate_params:
        #     update_community_parent(udpate_params)
            rs = CommunityDataItem.select().where(CommunityDataItem.parent == cdi.fs_id).exists()
            if not rs:
                rs = CommunityVisible.select().where(CommunityVisible.id == cdi.id).exists()
                if not rs:
                    item_list.append(cdi)
        if item_list:
            deal_item_list(item_list)
        print("dog:", dog, ",offset:", offset)
        offset = offset + size
        time.sleep(1)


if __name__ == '__main__':
    import time
    """
    parent_id = 1986  # 06 少年艺术课【完结】
    es = es_dao_local()
    # es = es_dao_test()
    # query_data_item_by_parent(cls, parent_id, is_dir=True, offset=0, limit=100)
    items = DataDao.query_data_item_by_parent(parent_id, is_dir=False)
    print("items:", items)
    for it in items:
        print('item:', DataItem.to_dict(it))
        # test_save_item(es, it)
        es.update_field(it.id, 'tags', ['0', '%d' % it.id])
    """
    # acc = Accounts.select().get()
    # print(acc.name)
    # print(acc.id)
    # sync_db_file_list_to_es(acc)

    # sync_db_file_list_to_es()
    # tag_es_item_show()
    update_es_community_by_visible()
