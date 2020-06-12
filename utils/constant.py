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
    (-6, "身份验证失败"),
    (100, "客户端通用降级错误码，客户端收到此错误码不会重试"),
    (31034, "命中接口频控"),
    (42000, "访问过于频繁"),
    (42001, "rand校验失败"),
    (42999, "功能下线"),
    (9100, "一级封禁"),
    (9200, "二级封禁"),
    (9300, "三级封禁"),
    (9400, "四级封禁"),
    (9500, "五级封禁"),
])

LOGIN_TOKEN_TIMEOUT = 10 * 24 * 60 * 60  # seconds
PAN_ACCESS_TOKEN_TIMEOUT = 29 * 24 * 60 * 60  # seconds
DLINK_TIMEOUT = 7  # hour
SHARED_FR_MINUTES_CNT = 19
SHARED_FR_HOURS_CNT = 299
SHARED_FR_DAYS_CNT = 9999

SHARED_FR_DAYS_ERR = "今日以至上限,明日再试!"
SHARED_FR_HOURS_ERR = "请过一小时再试!"
SHARED_FR_MINUTES_ERR = "请过一会儿再试!"
SHARED_BAN_ERR = "该文件不能提供分享!"
SHARED_NOT_EXISTS_ERR = "该文件不存在了!"

MAX_RESULT_WINDOW = 10000

FUN_TYPE = dict(BASE=0, EXT=1)
USER_TYPE = dict(SINGLE=1, GROUP=2, ALL=4)
FUN_BASE = dict(QUERY=1, NEW=2, UPDATE=4, DEL=8, MENU=16)

TOP_DIR_FILE_NAME = 'root'
SHARE_ES_TOP_POS = 0

ES_TAG_MAP = dict(PRODUCT='P',
                  FREE='F'
                  )

PRODUCT_TAG = ES_TAG_MAP['PRODUCT']

LOGIC_ERR_TXT = dict(
    unknown="未知问题,联系客服",
    ill_data="异常数据",
    not_exists="文件已不存在",
    need_access="需要先获取权限",
    rename_fail="文件迁出失败,稍后再试",
    mk_top_fail="目录创建失败",
    sys_lvl_down="出发系统降级",
    need_pann_acc="需要绑定Baidu盘账号"
)

PAN_TREE_TXT = dict(
    buy_root="众筹目录",
    free_root="福利目录",
    self_root="已获取目录",
    empty_root="到底了",
)
PAYMENT_ACC_SOURCE = dict(
    CREDIT="credit"
)
CREDIT_SOURCE = dict(
    LOGIN="login",
    LOGIN_EXTRA="login_extra",
    INVITE="invite",
    SHARE_PLAN="share_plan",
)
CREDIT_INITED_REWARD = 1
CREDIT_SIGNED_REWARD = 1
CREDIT_INVITE_REWARD = 10
CREDIT_SIGNED_LEVEL = [
    [3, 0],
    [6, 1],
    [29, 2],
    [30, 15],
    [31, -1, 3, 1]
]


def shared_format(link, code):
    return """链接: {} 提取码: {} 复制这段内容后打开百度网盘手机App，操作更方便哦""".format(link, code)


def buy_success_format(desc, price):
    return """购买: {} 成功！价格：{} .""".format(desc, "{:.2f}元".format(float(price/100)))
