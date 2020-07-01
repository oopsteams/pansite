# -*- coding: utf-8 -*-
"""
Created by susy at 2020/7/1
"""
from html.parser import HTMLParser
from utils import is_chinese
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
        print("parse err:", message)
