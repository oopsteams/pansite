# -*- coding: utf-8 -*-
"""
Created by susy at 2020/7/1
"""
from html.parser import HTMLParser
import html
from utils import is_chinese, log
from pypinyin import lazy_pinyin, Style, pinyin
import arrow
import json


class HTMLBookParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.data = dict()
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        pass

    def handle_endtag(self, tag):
        pass

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_data(self, data):
        if data:
            find_chinese = False
            _l = len(data)
            for i in range(_l):
                w = data[i]
                if is_chinese(w):
                    find_chinese = True
                    break
            if find_chinese:
                if self.current_tag not in self.data:
                    self.data[self.current_tag] = []
                self.data[self.current_tag].append(lazy_pinyin(data, style=Style.TONE, errors="ignore"))

    def handle_comment(self, data):
        pass

    def handle_entityref(self, name):
        pass

    def handle_charref(self, name):
        pass

    def error(self, message):
        # print("parse err:", message)
        log.error("parse err:{}".format(message))


class BookNcxParser(HTMLParser):
    def __init__(self):
        # HTMLParser.__init__(self)
        super().__init__()
        self.meta = dict()
        self.find_meta = False
        self.params = {}
        self.read_datas = False
        self.cd = ""

    def handle_starttag(self, tag, attrs):
        if tag == "metadata":
            self.find_meta = True
        elif self.find_meta:
            self.read_datas = True
            self.cd = ""

    def handle_endtag(self, tag):
        if self.find_meta and tag == "metadata":
            self.find_meta = False
        elif self.find_meta:
            if tag.endswith("title"):
                self.params["title"] = self.cd
            elif tag.endswith("creator"):
                self.params["authors"] = self.cd
            elif tag.endswith("publisher"):
                self.params["publisher"] = self.cd
            elif tag.endswith("date"):
                pubdate = None
                try:
                    pubdate = arrow.get(self.cd).datetime
                except Exception:
                    pass
                self.params["pubdate"] = pubdate
            elif tag.endswith("subject"):
                if "tags" not in self.params:
                    self.params["tags"] = []
                _cd = self.cd.strip(" ")
                cd_tags = [_cd]
                idx = _cd.rfind("，")
                if idx > 0:
                    cd_tags = _cd.split("，")
                for cdt in cd_tags:
                    self.params["tags"].append(cdt)

            self.read_datas = False
        pass

    def handle_startendtag(self, tag, attrs):
        if tag == "meta":
            _attrs_map = {k: v for k, v in attrs}
            if "name" in _attrs_map:
                key = _attrs_map["name"]
                val = None
                if "content" in _attrs_map:
                    val = _attrs_map["content"]
                if val:
                    s_key = key
                    idx = key.rfind(":")
                    if idx > 0:
                        s_key = key[idx+1:]
                        if s_key[0] == '#':
                            s_key = s_key[1:]
                            val_json_str = html.unescape(val)
                            try:
                                val_json = json.loads(val_json_str)
                                if "#value#" in val_json:
                                    val = val_json["#value#"]
                                if "label" in val_json:
                                    s_key = val_json["label"]
                            except:
                                val = ""
                                pass
                    self.meta[s_key] = val
            self.find_meta = True
        pass

    def handle_data(self, data):
        if data and self.read_datas:
            # print("find_docTitle:", self.find_docTitle, ",data:", data)
            _d = data.replace('\n', '').replace('\r', '').replace(' ', '')
            if self.cd:
                self.cd = "{}{}".format(self.cd, _d)
            else:
                self.cd = _d

    def handle_comment(self, data):
        pass

    def handle_entityref(self, name):
        pass

    def handle_charref(self, name):
        pass

    def error(self, message):
        log.error("parse err:{}".format(message))
