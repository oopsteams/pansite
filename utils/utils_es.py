# -*- coding: utf-8 -*-
"""
Created by susy at 2019/10/21
"""
import arrow
from utils import log as logger


def build_query_string(q):
    if q:
        idx = q.find(":")
        if idx >= 0:
            return {"query_string": {"query": q}}
        else:
            return {"query_string": {"default_field": "all", "query": q}}
    pass


class ShouldParams(object):

    def __init__(self, is_match=True, field=None, value=None):
        self.is_match = is_match
        self.field = field
        self.value = value

    def to_es_params(self, bool_body: dict):
        must_body = bool_body.get("must", list())
        if must_body:
            must_bool = None
            for item in must_body:
                if "bool" in item:
                    must_bool = item['bool']
                    break
            if not must_bool:
                must_bool = dict()
                must_body.append({"bool": must_bool})
            bool_body = must_bool
        should_body = list()
        if "should" in bool_body and bool_body.get("should"):
            should_body = bool_body.get("should")
        else:
            bool_body["should"] = should_body
        if self.is_match:
            if self.field and self.value:
                should_body.append({"match": {self.field: self.value}})
            elif self.value:
                should_body.append({"match": {"all": self.value}})
            else:
                return
        else:
            if self.field and self.value:
                if "query_string" == self.field:
                    should_body.append(build_query_string(self.value))
                else:
                    should_body.append({"term": {self.field: self.value}})
            else:
                return


class MustParams(ShouldParams):

    def __init__(self, is_match=True, field=None, value=None):
        super().__init__(is_match, field, value)

    def to_es_params(self, bool_body: dict):
        must_body = bool_body.get("must", list())
        print("MustParams to_es_params must_body:", must_body)
        if self.is_match:
            if self.field and self.value:
                must_body.append({"match": {self.field: self.value}})
            elif self.value:
                must_body.append({"match": {"all": self.value}})
            else:
                must_body.append({"match_all": {}})
        else:
            print("MustParams to_es_params field:", self.field, self.value)
            if self.field and self.value is not None:
                if "query_string" == self.field:
                    must_body.append(build_query_string(self.value))
                else:
                    must_body.append({"term": {self.field: self.value}})
            else:
                return
        bool_body['must'] = must_body


class MustNotParams(ShouldParams):

    def __init__(self, is_match=True, field=None, value=None):
        super().__init__(is_match, field, value)

    def to_es_params(self, bool_body: dict):
        must_not_body = bool_body.get("must_not", list())
        if self.is_match:
            if self.field and self.value:
                must_not_body.append({"match": {self.field: self.value}})
            elif self.value:
                must_not_body.append({"match": {"all": self.value}})
            else:
                return
        else:
            if self.field and self.value:
                if "query_string" == self.field:
                    must_not_body.append(build_query_string(self.value))
                else:
                    must_not_body.append({"term": {self.field: self.value}})
            else:
                return
        bool_body['must_not'] = must_not_body


class SearchParams(object):

    def __init__(self, offset=0, size=10):
        self.tags = None
        self.offset = offset
        self.size = size
        self.fields = {}
        self.musts: list = None
        self.not_musts: list = None
        self.should: list = None

    @classmethod
    def build_params(cls, offset=0, size=10):
        return SearchParams(offset, size)

    def add_must(self, is_match=True, field=None, value=None):
        if not self.musts:
            self.musts = []
        self.musts.append(MustParams(is_match, field, value))

    def add_must_not(self, is_match=True, field=None, value=None):
        if not value:
            return
        if not self.not_musts:
            self.not_musts = []
        self.not_musts.append(MustNotParams(is_match, field, value))

    def add_should(self, is_match=True, field=None, value=None):
        if not value:
            return
        if not self.should:
            self.should = []
        self.should.append(MustNotParams(is_match, field, value))


def build_es_item_json_body(data_item_id, category, isdir, pin, fs_id, size, account, filename, path, server_ctime,
                            updated_at, created_at, parent, sourceid, extuid='#', source='local', pos=0, tags=['0']):
    """
    :param data_item_id:
    :param category:
    :param isdir:
    :param pin:
    :param fs_id:
    :param size:
    :param account:
    :param filename:
    :param path:
    :param server_ctime:
    :param updated_at:
    :param created_at:
    :param parent:
    :param sourceid:存储外部来源关联ID或者内部pan_id
    :param extuid: 存储外部对应ID
    :param source: 分享(需要转存后可下载)/本地(直接下载)
    :param pos:
    :param tags: 多值标签字段
    :return:
    """

    updated_at_str = arrow.get(updated_at).strftime('%Y-%m-%d %H:%M:%S')
    created_at_str = arrow.get(created_at).strftime('%Y-%m-%d %H:%M:%S')
    es_json_bd = dict(id=data_item_id, category=category, isdir=isdir, pin=pin, pos=pos, fs_id=fs_id, size=size,
                      account=account, tags=tags, filename=filename, path=path, parent=parent,
                      server_ctime=server_ctime, updated_at=updated_at_str, created_at=created_at_str, source=source,
                      sourceid=sourceid, extuid=extuid)
    return es_json_bd


def build_es_book_json_body(code, price, name, cover, opf, ncx, ftype, lh, ftsize, desc, idx, created_at, pin=0,
                            ref_id=0,
                            source='', tags=['0']):
    created_at_str = arrow.get(created_at).strftime('%Y-%m-%d %H:%M:%S')
    es_json_bd = dict(code=code, price=price, name=name, cover=cover, opf=opf, ncx=ncx, ftype=ftype,
                      lh=lh, ftsize=ftsize, desc=desc, idx=idx, created_at=created_at_str, pin=pin, ref_id=ref_id,
                      source=source, tags=tags)
    return es_json_bd


def build_aggs_body(es_body, field):
    # 聚合参数
    es_body['aggs'] = {"group_by_%s" % field: {"terms": {"size": 100, "field": field}}}


def size_sort_func(es_body, asc=True):
    if asc:
        es_body['sort'].insert(0, {"size": {"order": "asc"}})
    else:
        es_body['sort'].insert(0, {"size": {"order": "desc"}})


def pos_sort_func(es_body, asc=True):
    if asc:
        es_body['sort'].insert(0, {"pos": {"order": "asc"}})
    else:
        es_body['sort'].insert(0, {"pos": {"order": "desc"}})


def tags_filter(search_params: SearchParams, and_arr):
    if search_params.tags:
        tags = search_params.tags
        and_arr.append({"terms": {"tags": tags}})


def build_query_item_es_body(search_params: SearchParams, sort_fields=None, fields=None):
    offset = search_params.offset
    limit = search_params.size
    logger.debug("search_params.limit: %s", limit)
    _default_sort = ["_score"]
    if sort_fields:
        _default_sort = sort_fields
    es_body = {"sort": _default_sort,
               "query": {'bool': {}},
               "from": offset, "size": limit}
    # "query":{'function_score': {}}
    and_arr = []
    if fields:
        es_body['_source'] = fields
    elif search_params.fields:
        es_body['_source'] = search_params.fields
    tags_filter(search_params, and_arr)
    if and_arr:
        es_body["filter"] = {"and": and_arr}
    query_body: dict = es_body["query"]
    bool_body: dict = query_body.get("bool", dict())
    if search_params.musts:
        print("has musts!!!!")
        for m in search_params.musts:
            m.to_es_params(bool_body)
    if search_params.not_musts:
        for nm in search_params.not_musts:
            nm.to_es_params(bool_body)
    if search_params.should:
        for s in search_params.should:
            s.to_es_params(bool_body)
    print("build_query_item_es_body bool_body:", bool_body)
    query_body["bool"] = bool_body
    return es_body
