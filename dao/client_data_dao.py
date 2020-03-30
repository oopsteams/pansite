# -*- coding: utf-8 -*-
"""
Created by susy at 2020/3/15
"""
from dao.models import db, query_wrap_db, ClientDataItem
from utils.constant import TOP_DIR_FILE_NAME
from cfg import PAN_ROOT_DIR


class ClientDataDao(object):

    # query
    @classmethod
    @query_wrap_db
    def check_data_item_exists_by_ref_id_id(cls, ref_id, item_id):
        return ClientDataItem.select().where(ClientDataItem.id == item_id, ClientDataItem.ref_id == ref_id).exists()

    @classmethod
    @query_wrap_db
    def get_data_item_by_source_fs_id(cls, source_fs_id, ref_id):
        return ClientDataItem.select().where(ClientDataItem.source_fs_id == source_fs_id, ClientDataItem.ref_id == ref_id).first()

    @classmethod
    @query_wrap_db
    def get_data_item_by_id(cls, pk_id, ref_id):
        return ClientDataItem.select().where(ClientDataItem.id == pk_id, ClientDataItem.ref_id == ref_id).first()

    @classmethod
    @query_wrap_db
    def get_root_item_by_pan_id(cls, pan_id):
        return ClientDataItem.select().where(ClientDataItem.source_fs_id == TOP_DIR_FILE_NAME,
                                             ClientDataItem.panacc == pan_id).first()

    @classmethod
    @query_wrap_db
    def get_top_dir_item_by_pan_id(cls, pan_id, top_dir_name=PAN_ROOT_DIR['name']):
        return ClientDataItem.select().where(ClientDataItem.source_fs_id == top_dir_name,
                                             ClientDataItem.panacc == pan_id).first()

    @classmethod
    @query_wrap_db
    def query_root_files_by_user_id(cls, ref_id):
        return ClientDataItem.select().where(ClientDataItem.ref_id == ref_id,
                                      ClientDataItem.source_fs_id == TOP_DIR_FILE_NAME).first()

    @classmethod
    @query_wrap_db
    def query_client_item_list_by_parent(cls, parent_id, ref_id, offset=0, limit=500):
        return ClientDataItem.select().where(ClientDataItem.parent == parent_id,
                                             ClientDataItem.ref_id == ref_id).offset(offset).limit(limit)

    # update
    @classmethod
    def update_client_item(cls, pk_id, params):
        _params = {p: params[p] for p in params if p in ClientDataItem.field_names()}
        # print("update_client_item _params:", _params)
        with db:
            ClientDataItem.update(**_params).where(ClientDataItem.id == pk_id).execute()

    # new
    @classmethod
    def new_root_item(cls, ref_id, pan_id):
        data_item = ClientDataItem(category=6, isdir=1, filename=TOP_DIR_FILE_NAME, fs_id='0', path='/', size=0,
                                   md5_val='', ref_id=ref_id, parent=0, panacc=pan_id, source_fs_id=TOP_DIR_FILE_NAME)
        with db:
            data_item.save(force_insert=True)
        return data_item

    @classmethod
    def new_top_dir_item(cls, ref_id, pan_id, fs_id, server_ctime, top_dir_name):
        data_item = ClientDataItem(category=6, isdir=1, filename=top_dir_name, fs_id=fs_id, path='/%s' % top_dir_name,
                                   size=0, md5_val='', ref_id=ref_id, parent=0, panacc=pan_id, server_ctime=server_ctime
                                   , source_fs_id=top_dir_name)
        with db:
            data_item.save(force_insert=True)
        return data_item

    @classmethod
    def new_data_item(cls, params):
        """
        :param params:
        :return:
        """
        data_item = ClientDataItem(category=params['category'],
                                   isdir=params['isdir'],
                                   filename=params['filename'],
                                   aliasname=params['aliasname'],
                                   fs_id=params['fs_id'],
                                   path=params['path'],
                                   size=params['size'],
                                   md5_val=params.get('md5_val', ''),
                                   ref_id=params.get('ref_id'),
                                   source_fs_id=params.get('source_fs_id'),
                                   pin=params.get('pin'),
                                   parent=params.get('parent', 0),
                                   panacc=params.get('panacc', 0)
                                   )
        with db:
            data_item.save(force_insert=True)
        return data_item
