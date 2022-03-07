# -*- coding: utf-8 -*-
"""
Created by susy at 2019/10/21
"""
from cfg import ES
from elasticsearch import Elasticsearch, helpers, exceptions
from utils import log as logger, get_now_ts
import datetime
import arrow

_settings = {"number_of_shards": 3, "number_of_replicas": 0, "analysis": {"analyzer": {"slash": {"type": "pattern",
                                                                                                 "pattern": "/"}}}}
_tag_prop = {"type": "keyword"}
_path_prop = {"type": "text", "analyzer": "slash"}
date_time_prop = {"type": "date", "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis"}
_all_prop = {"type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_smart", "position_increment_gap": 100
             }
__keyword_text_prop = {"type": "text",
             "analyzer": "ik_max_word",
             "search_analyzer":
                 "ik_smart",
             "fields": {
                 "keyword": {
                     "type": "keyword",
                     "ignore_above": 128
                 }
             }
             }
_props = {
    "id": {"type": "long"},
    "category": {"type": "integer"},
    "isdir": {"type": "integer"},
    "pin": {"type": "integer"},
    "pos": {"type": "integer"},
    "fs_id": {"type": "keyword"},
    "size": {"type": "long"},
    "account": {"type": "long"},
    "tags": _tag_prop,
    "filename": {"type": "keyword", "copy_to": "all"},
    "aliasname": {"type": "keyword", "copy_to": "all"},
    "path": _path_prop,
    "parent": {"type": "keyword"},
    "server_ctime": {"type": "long"},
    "updated_at": date_time_prop,
    "created_at": date_time_prop,
    "source": {"type": "keyword"},
    "sourceid": {"type": "long"},
    "extuid": {"type": "keyword"},
    "payload": {"type": "keyword"},
    "all": _all_prop}

# "code", "account_id", "ref_id", "price", "name", "unziped", "idx", "cover", "pin", "opf", "ncx"
# "authors", "rating", "series", "publisher", "pubdate"
_book = {
    "id": {"type": "keyword"},
    "ref_id": {"type": "long"},
    "price": {"type": "long"},
    "name": __keyword_text_prop,
    "idx": {"type": "integer"},
    "cover": {"type": "keyword"},
    "opf": {"type": "keyword"},
    "ncx": {"type": "keyword"},
    "pin": {"type": "integer"},
    "ftype": {"type": "integer"},
    "lh": {"type": "keyword"},
    "ftsize": {"type": "integer"},
    "authors": __keyword_text_prop,
    "rating": {"type": "integer"},
    "series": __keyword_text_prop,
    "publisher": __keyword_text_prop,
    "pubdate": date_time_prop,
    "tags": _tag_prop,
    "created_at": date_time_prop,
    "source": {"type": "keyword"},
    "desc": {"type": "text",
             "analyzer": "ik_max_word",
             "search_analyzer":
                 "ik_smart"
             },
    "pack_id": {"type": "long"},
    "is_pack": {"type": "integer"},
    "data_id": {"type": "long"}
}


#  "ftype", "lh", "ftsize"

class EsConnections(object):

    def __init__(self, hosts=None):
        self.index_doc_cache = {}
        if not hosts:
            hosts = ES["hosts"]
        # print("elastic search hosts:", hosts)
        # self.es = Elasticsearch(hosts, sniff_on_start=True, sniff_on_connection_fail=True, sniffer_timeout=60,
        #                         sniff_timeout=10, retry_on_timeout=True)
        self.es = Elasticsearch(hosts, sniff_on_start=False, sniff_on_connection_fail=False,
                                sniff_timeout=10, retry_on_timeout=True)
        logger.info("EsConnections es init hosts=%s" % hosts)
        # print("elastic search es:", self.es)

        props = _props

        _cfg = ES["share"]
        # _index_body = {"settings": _settings,
        #                "mappings": {
        #                    "dataitem": {"properties": props}
        #                }}
        _index_body = {"settings": _settings,
                       "mappings": {
                           "properties": props
                       }}
        self.es_index(_cfg["index_name"], _cfg["doctype"], _index_body, props)
        _cfg = ES["local"]

        _index_body = {"settings": _settings,
                       "mappings": {
                           "properties": props
                       }}
        self.es_index(_cfg["index_name"], _cfg["doctype"], _index_body, props)
        # _cfg = ES["test"]
        # _index_body = {"settings": self._settings,
        #                "mappings": {
        #                    "dataitem": {"properties": props}
        #                }}
        # self.es_index(_cfg["index_name"], _cfg["doctype"], _index_body, props)

        _cfg = ES["book"]

        # _index_body = {"settings": _settings,
        #                "mappings": {
        #                    _cfg["doctype"]: {
        #                        "properties": _book
        #                    }
        #                }}
        _index_body = {"settings": _settings,
                       "mappings": {
                           "properties": _book
                       }}
        self.es_index(_cfg["index_name"], _cfg["doctype"], _index_body, _book)

    def es_index(self, index_name, doc_type, index_body, props):
        key = "%s_%s" % (index_name, doc_type)
        if not self.index_doc_cache.get(key):
            if not self.get_es().indices.exists(index=index_name):
                try:
                    self.get_es().indices.create(index=index_name, **index_body)
                except Exception as e:
                    logger.error("put mapping err!", exc_info=True)
            self.index_doc_cache[key] = EsDao(self.get_es(), index_name, doc_type, props)

    def get_es(self):
        return self.es

    def reload_mapping(self):
        self.index_doc_cache = {}
        self.__init__()

    def dao(self, index_name, doc_type):
        key = "%s_%s" % (index_name, doc_type)
        return self.index_doc_cache[key]


class EsDao(object):
    def __init__(self, es: Elasticsearch, index_name, doc_type, props):
        self.es = es
        self.index_name = index_name
        self.doc_type = doc_type
        self.props = props
        # self.key = "%s_%s" % (index_name, doc_type)

    def reload_mapping(self):
        if self.es:
            EsConnections().reload_mapping()

    def get_es(self):
        return self.es

    def filter_update_params(self, params):
        _params = {}
        for k in params:
            if k == "id":
                continue
            if k in self.props:
                p = self.props[k]
                if p['type'] == 'date' and params[k] and isinstance(params[k], datetime.datetime):
                    _params[k] = arrow.get(params[k]).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    _params[k] = params[k]
        return _params

    def index(self, doc_id, doc):
        try:
            if 'doc' in doc:
                doc["doc"]['@ts'] = get_now_ts()
                doc["doc"]['@is_removed'] = 0
            else:
                doc['@ts'] = get_now_ts()
                doc['@is_removed'] = 0
        except Exception as e:
            logger.error("index=%s" % e, exc_info=True)

        # logger.debug("ES:index=%s" % doc)
        # print("index_name:%s,%s" % (self.index_name, self.doc_type))
        # return self.es.index(index=self.index_name, id=doc_id, doc_type=self.doc_type, body=doc)
        return self.es.index(index=self.index_name, id=doc_id, document=doc)
        # return self.es.index(index=self.index_name, id=doc_id, body=doc)

    def update_field(self, doc_id, field, value):
        try:
            ret = self.update(doc_id, {"doc": {field: value}})
        except Exception as e:
            logger.warn("update_field, doc_id: %s, field: %s, value: %s, error: %s" % (doc_id, field, value, e),
                        exc_info=True)
            return None

        return ret

    def update_fields(self, doc_id, **kwargs):
        try:
            ret = self.update(doc_id, {"doc": kwargs})
        except Exception as e:
            logger.warn("update_fields:%s,%s,%s" % (doc_id, kwargs, e), exc_info=True)
            return None
        return ret

    def update_by_query(self, es_body, params):
        if not params:
            return None
        _es_body = {}
        try:
            inf = ["ctx._source.%s = params.%s" % (f, f) for f in params]
            _es_body['query'] = es_body['query']
            _es_body['script'] = {
                'lang': 'painless',
                'params': params,
                'inline': ';'.join(inf)
            }
            print("_es_body:", _es_body)
            ret = self.es.update_by_query(index=self.index_name, body=_es_body)
        except Exception as e:
            logger.warn("update_fields:%s,%s,%s" % (_es_body, params, e), exc_info=True)
            return None
        return ret

    def update(self, doc_id, body, params=None):
        try:
            logger.debug("ES:%s,update=%s,=%s" % (self.doc_type, doc_id, body))

            try:
                body["doc"]['@ts'] = get_now_ts()
            except Exception as e:
                logger.error("update error=%s" % e, exc_info=True)

            # VersionConflictEngineException
            if params is None:
                params = {}
            params['retry_on_conflict'] = 5

            ret = self.es.update(index=self.index_name, id=doc_id, doc_type=self.doc_type, body=body, params=params)
            # ret = self.es.update(index=self.index_name, id=doc_id, body=body, params=params)
        except Exception as e:
            logger.warn("update:%s,%s,%s,%s" % (doc_id, body, params, e), exc_info=True)
            return None
        return ret

    def delete(self, doc_id):
        try:
            logger.debug("ES:%s,delete=%s" % (self.doc_type, doc_id))
            ret = self.es.delete(index=self.index_name, id=doc_id, doc_type=self.doc_type)
            # ret = self.es.delete(index=self.index_name, id=doc_id)
        except exceptions.NotFoundError:
            logger.warn("not found doc:{}".format(doc_id))
            ret = None
        except Exception as e:
            logger.warn("delete:%s,%s" % (doc_id, e), exc_info=True)
            ret = None
        return ret

    def bulk_delete(self, doc_ids):
        try:
            logger.debug("ES:%s,delete=%s" % (self.doc_type, doc_ids))
            actions = []
            for _id in doc_ids:
                actions.append({"_op_type": "delete", "_id": _id, "_index": self.index_name, "_type": self.doc_type})
                # actions.append({"_op_type": "delete", "_id": _id, "_index": self.index_name})
            success, errors = helpers.bulk(client=self.es, actions=actions)
            logger.info("success count:{}, errors:{}".format(success, errors))
            ret = {"success": success, "errors": errors}
        except exceptions.NotFoundError:
            logger.warn("not found doc:{}".format(doc_ids))
            ret = None
        except Exception as e:
            logger.warn("delete:%s,%s" % (doc_ids, e), exc_info=True)
            ret = None
        return ret

    def exists(self, doc_id):
        return self.es.exists(index=self.index_name, doc_type=self.doc_type, id=doc_id)
        # return self.es.exists(index=self.index_name, id=doc_id)

    def refresh(self):
        self.es.indices.refresh(self.index_name)

    def es_get(self, doc_id, conditions=None):
        if doc_id:
            if conditions:
                result = self.es.get(index=self.index_name, id=doc_id, doc_type=self.doc_type, params=conditions)
            else:
                result = self.es.get(index=self.index_name, id=doc_id, doc_type=self.doc_type)
            return result
        return None

    def es_search_exec(self, es_body, fields=None, exact_total=False):
        # logger.debug("utils.is_not_production()=%s" % utils.is_not_production())
        # logger.debug("es_search_exec=%s" % ("%s" % es_body).replace("'", "\""))
        result = {}
        try:
            if fields:
                if exact_total:
                    result = self.es.search(index=self.index_name, **es_body, fields=fields, track_total_hits=True)
                else:
                    result = self.es.search(index=self.index_name, **es_body, fields=fields)
            else:
                if exact_total:
                    result = self.es.search(index=self.index_name, **es_body, track_total_hits=True)
                else:
                    result = self.es.search(index=self.index_name, **es_body)
        except Exception as e:
            logger.warn("es_search_exec:%s,%s" % (es_body, e), exc_info=True)
        return result


__EC = EsConnections()


# __EC = None

def es_dao_share() -> EsDao:
    _cfg = ES["share"]
    index_name = _cfg["index_name"]
    doc_type = _cfg["doctype"]
    return __EC.dao(index_name, doc_type)


def es_dao_local() -> EsDao:
    _cfg = ES["local"]
    index_name = _cfg["index_name"]
    doc_type = _cfg["doctype"]
    return __EC.dao(index_name, doc_type)


def es_dao_test() -> EsDao:
    _cfg = ES["test"]
    index_name = _cfg["index_name"]
    doc_type = _cfg["doctype"]
    return __EC.dao(index_name, doc_type)


def es_dao_book() -> EsDao:
    _cfg = ES["book"]
    index_name = _cfg["index_name"]
    doc_type = _cfg["doctype"]
    return __EC.dao(index_name, doc_type)


if __name__ == '__main__':
    import json

    props = {
        "id": {"type": "long"},
        "category": {"type": "integer"},
        "isdir": {"type": "integer"},
        "pin": {"type": "integer"},
        "pos": {"type": "integer"},
        "fs_id": {"type": "keyword"},
        "size": {"type": "long"},
        "account": {"type": "long"},
        "tags": _tag_prop,
        "filename": {"type": "keyword", "copy_to": "all"},
        "aliasname": {"type": "keyword", "copy_to": "all"},
        "path": _path_prop,
        "parent": {"type": "keyword"},
        "server_ctime": {"type": "long"},
        "updated_at": date_time_prop,
        "created_at": date_time_prop,
        "source": {"type": "keyword"},
        "sourceid": {"type": "long"},
        "extuid": {"type": "keyword"},
        "payload": {"type": "keyword"},
        "all": _all_prop}
    _index_body = {"settings": _settings,
                   "mappings": {
                       "dataitem": {"properties": props}
                   }}
    print(json.dumps(_index_body))
