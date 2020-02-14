# -*- coding: utf-8 -*-
"""
Created by susy at 2019/11/7
"""

PAN_ERROR_CODES = dict([
    (2, "参数错误"),
    (-3, "fs_id不存在"),
    (-70, "分享文件存在病毒"),
    (108, "文件命中反作弊策略"),
    (110, "文件命中频控策略"),
    (115, "文件命中黑名单禁止分享"),
    (105, "外链地址错误"),
    (-12, "参数错误"),
    (-9, "pwd/spd错误"),
    (-7, "share_id不存在"),
    (111, "有其他转存任务在进行"),
    (120, "非会员用户达到转存文件数目上限"),
    (130, "达到高级会员转存上限"),
    (-33, "达到转存文件数目上限"),
    (12, "批量操作失败"),
    (-8, "文件或目录已存在"),
])

LOGIN_TOKEN_TIMEOUT = 10 * 24 * 60 * 60  # seconds
PAN_ACCESS_TOKEN_TIMEOUT = 29 * 24 * 60 * 60  # seconds
DLINK_TIMEOUT = 5  # hour
SHARED_FR_MINUTES_CNT = 19
SHARED_FR_HOURS_CNT = 299
SHARED_FR_DAYS_CNT = 9999

SHARED_FR_DAYS_ERR = "今日以至上限,明日再试!"
SHARED_FR_HOURS_ERR = "请过一小时再试!"
SHARED_FR_MINUTES_ERR = "请过一会儿再试!"
SHARED_BAN_ERR = "该文件不能提供分享!"

MAX_RESULT_WINDOW = 10000

FUN_TYPE = dict(BASE=0, EXT=1)
USER_TYPE = dict(SINGLE=1, GROUP=2, ALL=4)
FUN_BASE = dict(QUERY=1, NEW=2, UPDATE=4, DEL=8, MENU=16)

TOP_DIR_FILE_NAME = 'root'
SHARE_ES_TOP_POS = 1


def shared_format(link, code):
    return """链接: {} 提取码: {} 复制这段内容后打开百度网盘手机App，操作更方便哦""".format(link, code)
