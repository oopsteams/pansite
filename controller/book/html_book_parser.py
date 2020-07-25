# -*- coding: utf-8 -*-
"""
Created by susy at 2020/7/1
"""
from html.parser import HTMLParser
from utils import is_chinese, log
from pypinyin import lazy_pinyin, Style, pinyin


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
        self.title = None
        self.current_tag = None
        self.find_docTitle = False
        self.find_meta = False

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        print("tag:", tag)
        if tag == "doctitle":
            self.find_docTitle = True
        elif tag == "meta":
            if "name" in attrs:
                key = attrs["name"]
                val = None
                if "content" in attrs:
                    val = attrs["content"]
                if val:
                    self.meta[key] = val
            self.find_meta = True
        pass

    def handle_endtag(self, tag):
        print("end tag:", tag)
        if self.find_docTitle and tag.lower() == "doctitle":
            self.find_docTitle = False
        elif self.find_meta and tag.lower() == "meta":
            self.find_meta = False
        pass

    def handle_startendtag(self, tag, attrs):
        print("handle_startendtag tag:", tag)
        if tag == "meta":
            print("meta attrs:", attrs)
            if "name" in attrs:
                key = attrs["name"]
                val = None
                if "content" in attrs:
                    val = attrs["content"]
                if val:
                    self.meta[key] = val
            self.find_meta = True
        pass

    def handle_data(self, data):
        if data:
            print("find_docTitle:", self.find_docTitle, ",data:", data)
            if self.find_docTitle:
                self.title = "".format(self.title, data)
        pass

    def handle_comment(self, data):
        pass

    def handle_entityref(self, name):
        pass

    def handle_charref(self, name):
        pass

    def error(self, message):
        log.error("parse err:{}".format(message))
