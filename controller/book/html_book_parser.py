# -*- coding: utf-8 -*-
"""
Created by susy at 2020/7/1
"""
from html.parser import HTMLParser
from utils import is_chinese
from pypinyin import lazy_pinyin, Style


class HTMLBookParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.data = dict()

    def handle_starttag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        pass

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_data(self, data):
        if data:
            _l = len(data)
            for i in range(_l):
                w = data[i]
                if w not in self.data and is_chinese(w):
                    self.data[w] = lazy_pinyin(w, style=Style.TONE)

    def handle_comment(self, data):
        pass

    def handle_entityref(self, name):
        pass

    def handle_charref(self, name):
        pass

    def error(self, message):
        print("parse err:", message)
