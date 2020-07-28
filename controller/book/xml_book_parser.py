# -*- coding: utf-8 -*-
"""
Created by susy at 2020/7/28
"""
from xml.dom import minidom


def read_xml(in_path):
    dom = minidom.parse(in_path)
    return dom

