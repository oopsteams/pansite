# -*- coding: utf-8 -*-
"""
Created by susy at 2020/7/1
"""
from html.parser import HTMLParser


class MyHTMLParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.data = []  # 定义data数组用来存储html中的数据
        self.links = []

    def handle_starttag(self, tag, attrs):
        print('<%s>' % tag)
        if tag == "a":
            if len(attrs) == 0:
                pass
            else:
                for (variable, value) in attrs:
                    if variable == "href":
                        self.links.append(value)

    def handle_endtag(self, tag):
        print('</%s>' % tag)

    def handle_startendtag(self, tag, attrs):
        print('<%s/>' % tag)

    def handle_data(self, data):
        print('data===>', data)

    def handle_comment(self, data):
        print('<!--', data, '-->')

    def handle_entityref(self, name):
        print('&%s;' % name)

    def handle_charref(self, name):
        print('&#%s;' % name)

    def error(self, message):
        print("parse err:", message)
        pass
