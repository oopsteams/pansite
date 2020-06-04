# -*- coding: utf-8 -*-
"""
Created by susy at 2019/10/17
"""
import datetime
from peewee import *
# from playhouse.pool import PooledMySQLDatabase
# from playhouse.shortcuts import ReconnectMixin
# from cfg import mysql_worker_config as config
from utils import object_to_dict, log
from functools import wraps
from dao.base import db, BaseModel, BASE_FIELDS, db_update_field_sql
from dao.goods_models import *
from dao.payment_models import *
# BATCH_DB_USER = config["user"]  # 'market'
# BATCH_DB_PASSWORD = config["password"]  # 'market'
# # BATCH_DB_HOST='172.31.140.249'
# BATCH_DB_HOST = config["host"]  # '127.0.0.1'
# BATCH_DB_PORT = config["port"]  # '3306'
# BATCH_DB_NAME = config["db"]  # 'liquidity'
#
# BATCH_DB_URL = 'mysql://%s:%s@%s:%s/%s' % (BATCH_DB_USER, BATCH_DB_PASSWORD, BATCH_DB_HOST, BATCH_DB_PORT, BATCH_DB_NAME)
# BASE_FIELDS = ["created_at", "updated_at"]
#
#
# def db_connect(url):
#     print("Use database : %s" % (url))
#     from playhouse.db_url import connect
#     db = connect(url, False, **{"sql_mode": "traditional"})
#     return db
#
#
# class RetryMySQLDatabase(ReconnectMixin, PooledMySQLDatabase):
#     _instance = None
#
#     @staticmethod
#     def db_instance():
#         if not RetryMySQLDatabase._instance:
#             RetryMySQLDatabase._instance = RetryMySQLDatabase(
#                 BATCH_DB_NAME, max_connections=5, stale_timeout=300, host=BATCH_DB_HOST, user=BATCH_DB_USER,
#                 password=BATCH_DB_PASSWORD, port=BATCH_DB_PORT
#             )
#         return RetryMySQLDatabase._instance
#         pass
#
#     def sequence_exists(self, seq):
#         pass
#
#
# try:
#     db_exist = 'db' in locals() or 'db' in globals()
#     if not db_exist:
#         # db = db_connect(BATCH_DB_URL)
#         db = RetryMySQLDatabase.db_instance()
#         print("db not exist.")
# except Exception:
#     # db = db_connect(BATCH_DB_URL)
#     db = RetryMySQLDatabase.db_instance()


def try_release_conn():
    if not db.is_closed():
        try:
            db.manual_close()
            # db._close(db.connection())
        except Exception:
            log.error("exe action failed.", exc_info=True)
    else:
        print("db is closed!")


def query_wrap_db(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if db.is_closed():
            db.connect()
        return func(*args, **kwargs)
    return wrapper


def new_guest_account(org_id, role_id, type, name="guest", mobile_no="0000000000", password="654321"):
    acc: Accounts = Accounts(name=name, mobile_no=mobile_no, nickname=name, password=password)
    acc.save(force_insert=True)
    acc_id = acc.id
    ur: UReference = UReference()
    ur.save(force_insert=True)
    au: AuthUser = AuthUser(acc_id=acc_id, org_id=org_id, role_id=role_id, ref_id=ur.id, type=type)
    au.save(force_insert=True)


def new_sub_category(pc: Category):
    if pc:
        if not Category.select().where(Category.name == '好芳法').exists():
            sc: Category = Category(**{"name": "好芳法"})
            sc.save(force_insert=True)
            CateCate.insert_many({"cid": sc.cid, "pcid": pc.cid, "lvl": 1}).execute()
            CateCate.insert_many({"cid": sc.cid, "pcid": sc.cid, "lvl": 2}).execute()
        if not Category.select().where(Category.name == '诸葛学堂').exists():
            sc: Category = Category(**{"name": "诸葛学堂"})
            sc.save(force_insert=True)
            CateCate.insert_many({"cid": sc.cid, "pcid": pc.cid, "lvl": 1}).execute()
            CateCate.insert_many({"cid": sc.cid, "pcid": sc.cid, "lvl": 2}).execute()


def init_db():
    db.create_tables([Accounts, DataItem, WorkerLoadMap, ShareLogs, Tags, UserTags, PanAccounts, TransferLogs,
                      AccountExt, CommunityDataItem, UserRootCfg, ShareFr, LoopAdTask, AdSource, AuthUser, UReference,
                      Fun, Role, RoleExtend, Org, OrgOrg, UserRefExtend, UserRoleExtend, UserOrgExtend, Product, Order,
                      OrderItem, Assets, LocalVisible, CommunityVisible, ShareApp, DataItemExt, ClientDataItem,
                      AppCfg, AccountWxExt, Category, CateCate, SPUStruct, Brand, NetWeight, SweetNess, Pack,
                      CourseProduct, ProductSpu, ProductImg, Goods, Subjects, PaymentAccount, CreditRecord], safe=True)

    with db:
        if not Org.select().where(Org.id == 1).exists():
            Org.insert_many({"id": 1, "name": "root"}).execute()
            Org.insert_many({"id": 2, "name": "内部顶级", "parent": 1}).execute()
            Org.insert_many({"id": 3, "name": "外部顶级", "parent": 1}).execute()
            Org.insert_many({"id": 4, "name": "内部人员", "parent": 2}).execute()
            Org.insert_many({"id": 5, "name": "普通客户组", "parent": 3}).execute()
            OrgOrg.insert_many({"org_id": 2, "parent": 1}).execute()
            OrgOrg.insert_many({"org_id": 3, "parent": 1}).execute()
            OrgOrg.insert_many({"org_id": 4, "parent": 1}).execute()
            OrgOrg.insert_many({"org_id": 4, "parent": 2}).execute()
            OrgOrg.insert_many({"org_id": 5, "parent": 1}).execute()
            OrgOrg.insert_many({"org_id": 5, "parent": 3}).execute()
        if not Fun.select().where(Fun.id == 1).exists():
            base_fun_list = [{"id": 1, "code": 1, "desc": "query"},
                             {"id": 2, "code": 2, "desc": "new"},
                             {"id": 3, "code": 4, "desc": "update"},
                             {"id": 4, "code": 8, "desc": "del"},
                             {"id": 5, "code": 16, "desc": "menu"},
                             {"id": 6, "code": 32, "desc": "-"},
                             {"id": 7, "code": 64, "desc": "-"},
                             {"id": 8, "code": 128, "desc": "-"},
                             {"id": 9, "code": 256, "desc": "-"},
                             {"id": 10, "code": 512, "desc": "-"},
                             {"id": 11, "code": 1024, "desc": "-"},
                             ]
            for bf in base_fun_list:
                Fun.insert_many(bf).execute()
        if not Role.select().where(Role.id == 1).exists():
            Role.insert_many({"id": 1, "desc": "base", "base_fun": 1, "default_path": "/index.html"}).execute()
        if not Accounts.select().where(Accounts.id == 1).exists():
            Accounts.insert_many({"id": 1, "name": "root", "nickname": "root", "password": "000000",
                                  "mobile_no": "18511338714"}).execute()
        if not UReference.select().where(UReference.id == 1).exists():
            UReference.insert_many({"id": 1}).execute()
        if not AuthUser.select().where(AuthUser.acc_id == 1).exists():
            AuthUser.insert_many({"acc_id": 1, "org_id": 1, "role_id": 1, "type": 4}).execute()
        if not Accounts.select().where(Accounts.name == 'guest').exists():
            org_id = 5
            role_id = 1
            single = 1
            new_guest_account(org_id, role_id, single)
        if not Category.select().where(Category.name == '教育平台').exists():
            Category.insert_many({"name": "教育平台", "pin": 2}).execute()
        c: Category = Category.select().where(Category.name == '教育平台').first()
        if c:
            new_sub_category(c)

    print("Init database ok")


class AccountWxExt(BaseModel):
    id = AutoField()
    openid = CharField(null=False, max_length=48, unique=True)
    nickname = CharField(null=True, max_length=64)
    session_key = CharField(null=True, max_length=64)
    avatar = CharField(null=True, max_length=1024)  # 用户的头像
    birthday = CharField(null=True, max_length=64)  # 生日
    marriage = CharField(null=True, max_length=16)  # 婚姻状况
    gender = SmallIntegerField(null=True, default=0)  # 性别 0：未知、1：男、2：女
    language = CharField(null=True, max_length=16)  # 语言
    country = CharField(null=True, max_length=16)  # 国家
    province = CharField(null=True, max_length=16)  # 省
    city = CharField(null=True, max_length=16)  # 城市
    job = CharField(null=True, max_length=16)  # 职位
    unionid = CharField(null=True, max_length=128)  # wx跨服务唯一标识
    is_realname = IntegerField(null=False, default=0)  # 是否实名制
    account_id = IntegerField(null=False, default=0, index=True)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "openid", "nickname", "session_key", "avatar", "birthday", "marriage", "gender",
                              "language", "country", "province", "city", "job", "is_realname", "account_id", "unionid"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class AccountExt(BaseModel):
    id = AutoField()
    user_id = BigIntegerField(null=False, default=0)
    username = CharField(null=True, max_length=64)
    realname = CharField(null=True, max_length=64)
    portrait = CharField(null=True, max_length=1024)  # 用户的头像
    userdetail = CharField(null=True, max_length=512)  # 自我简介
    birthday = CharField(null=True, max_length=64)  # 生日
    marriage = CharField(null=True, max_length=16)  # 婚姻状况
    sex = CharField(null=True, max_length=16)  # 性别
    blood = CharField(null=True, max_length=16)  # 血型
    figure = CharField(null=True, max_length=16)  # 体型
    constellation = CharField(null=True, max_length=16)  # 星座
    education = CharField(null=True, max_length=16)  # 学历
    trade = CharField(null=True, max_length=16)  # 当前职业
    job = CharField(null=True, max_length=16)  # 职位
    is_realname = IntegerField(null=False, default=0)  # 是否实名制
    account_id = IntegerField(null=False, default=0, index=True)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "user_id", "username", "realname", "portrait", "userdetail", "birthday",
                              "marriage", "sex", "blood", "figure", "constellation", "education", "trade", "job",
                              "is_realname", "account_id"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class PanAccounts(BaseModel):
    id = AutoField()
    user_id = IntegerField(null=False, default=0, index=True)
    name = CharField(null=True, max_length=64)
    password = CharField(null=True, max_length=64)
    client_id = CharField(null=True, max_length=64)
    client_secret = CharField(null=True, max_length=64)
    access_token = CharField(null=True, max_length=256)
    refresh_token = CharField(null=True, max_length=256)
    token_updated_at = DateTimeField(null=True)
    expires_at = DateTimeField(null=True)
    use_count = IntegerField(null=False, default=0)
    pin = IntegerField(null=False, default=0)
    bd_uid = BigIntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "user_id", "name", "password", "client_id", "client_secret", "access_token",
                              "token_updated_at", "pin", "refresh_token", "expires_at", "use_count", "bd_uid"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class Accounts(BaseModel):
    id = AutoField()
    name = CharField(null=False, max_length=64, unique=True)
    nickname = CharField(max_length=128)
    password = CharField(null=False, max_length=64)
    # client_id = CharField(null=True, max_length=64)
    # client_secret = CharField(null=True, max_length=64)
    # access_token = CharField(null=True, max_length=256)
    login_token = CharField(null=True, max_length=512)
    # token_updated_at = DateTimeField(null=True)
    login_updated_at = DateTimeField(null=True)
    mobile_no = CharField(null=False, max_length=16)
    fuzzy_id = CharField(null=True, max_length=16, index=True)
    pin = IntegerField(null=False, default=0)
    last_login_at = DateTimeField(null=True)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "nickname", "name", "password", "mobile_no", "fuzzy_id", "login_token",
                              "login_updated_at", "pin", "last_login_at"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class DataItemExt(Model):
    id = IntegerField(null=False, default=0)
    fs_id = CharField(null=False, max_length=64)
    mlink = CharField(null=True, max_length=1024)
    start_at_time = IntegerField(null=False, default=0)

    class Meta:
        database = db
        primary_key = CompositeKey('id')

    @classmethod
    def field_names(cls):
        return ["id", "fs_id", "mlink", "start_at_time"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class DataItem(BaseModel):
    id = AutoField()
    category = IntegerField(null=False, default=0)
    isdir = IntegerField(null=False, default=0)
    filename = CharField(null=True, max_length=256)
    aliasname = CharField(null=True, max_length=256)
    dlink = CharField(null=True, max_length=1024)
    thumb = CharField(null=True, max_length=1024)
    fs_id = CharField(null=False, max_length=64)
    path = CharField(null=True, max_length=1024)
    size = BigIntegerField(null=False, default=0)
    md5_val = CharField(null=False, max_length=64)
    parent = IntegerField(null=False, default=0, index=True)
    dlink_updated_at = DateTimeField(null=True)
    pin = IntegerField(null=False, default=0)
    sized = IntegerField(null=False, default=0)
    synced = IntegerField(null=False, default=0)
    server_ctime = IntegerField(null=False, default=0)
    account_id = IntegerField(null=False, default=0)
    panacc = IntegerField(null=False, default=0)

    def equals(self, dataitem):
        if dataitem:
            return self.md5_val == dataitem.md5_val
        return False

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "category", "isdir", "filename", "aliasname", "dlink", "fs_id", "path", "size",
                                             "md5_val", "parent", "dlink_updated_at", "pin", "server_ctime",
                                             "account_id", "panacc", "sized", "synced", "thumb"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class ClientDataItem(BaseModel):
    id = AutoField()
    category = IntegerField(null=False, default=0)
    isdir = IntegerField(null=False, default=0)
    filename = CharField(null=True, max_length=256)
    aliasname = CharField(null=True, max_length=256)
    dlink = CharField(null=True, max_length=1024)
    thumb = CharField(null=True, max_length=1024)
    fs_id = CharField(null=False, max_length=64)
    path = CharField(null=True, max_length=1024)
    size = BigIntegerField(null=False, default=0)
    md5_val = CharField(null=False, max_length=64)
    parent = IntegerField(null=False, default=0, index=True)
    dlink_updated_at = DateTimeField(null=True)
    pin = IntegerField(null=False, default=0)
    sized = IntegerField(null=False, default=0)
    synced = IntegerField(null=False, default=0)
    server_ctime = IntegerField(null=False, default=0)
    ref_id = IntegerField(null=False, default=0, index=True)
    source_fs_id = CharField(null=False, max_length=64, index=True)
    panacc = IntegerField(null=False, default=0)

    def equals(self, dataitem):
        if dataitem:
            return self.md5_val == dataitem.md5_val
        return False

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "category", "isdir", "filename", "aliasname", "dlink", "fs_id", "path", "size",
                                             "md5_val", "parent", "dlink_updated_at", "pin", "server_ctime",
                                             "ref_id", "panacc", "sized", "synced", "thumb", "source_fs_id"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class LocalVisible(Model):
    id = IntegerField(null=False, default=0)
    show = IntegerField(null=False, default=1)

    class Meta:
        database = db
        primary_key = CompositeKey('id')

    @classmethod
    def field_names(cls):
        return ["id", "show"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class CommunityDataItem(BaseModel):
    id = AutoField()
    category = IntegerField(null=False, default=0)
    isdir = IntegerField(null=False, default=0)
    filename = CharField(null=True, max_length=256)
    aliasname = CharField(null=True, max_length=256)
    fs_id = CharField(null=False, max_length=64, index=True)
    path = CharField(null=True, max_length=1024)
    size = BigIntegerField(null=False, default=0)
    sized = IntegerField(null=False, default=0)
    md5_val = CharField(null=False, max_length=64)
    parent = CharField(null=False, max_length=64, index=True)
    pin = IntegerField(null=False, default=0)
    server_ctime = IntegerField(null=False, default=0)
    account_id = IntegerField(null=False, default=0)
    sourceid = IntegerField(null=True, default=0)
    sourceuid = CharField(null=True, max_length=64)

    def equals(self, communitydataitem):
        if communitydataitem:
            return self.category == communitydataitem.category and self.filename == communitydataitem.filename and \
                   self.path == communitydataitem.path
        return False

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "category", "isdir", "filename", "aliasname", "fs_id", "path", "size",
                                             "md5_val", "parent", "pin", "server_ctime",
                                             "account_id", "sourceid", "sourceuid"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class CommunityVisible(Model):
    id = IntegerField(null=False, default=0)
    show = IntegerField(null=False, default=1)

    class Meta:
        database = db
        primary_key = CompositeKey('id')

    @classmethod
    def field_names(cls):
        return ["id", "show"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class Tags(BaseModel):
    id = AutoField()
    name = CharField(null=False, max_length=64)
    parent = IntegerField(null=False, default=0)
    rule = CharField(null=False, max_length=256, default='')

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["name", "parent", "rule"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class UserTags(BaseModel):
    id = AutoField()
    user_id = IntegerField(null=False, default=0)
    tag_id = IntegerField(null=False, default=0)
    tag_idx = IntegerField(null=False, default=0)
    pin = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "user_id", "tag_id", "tag_idx", "pin", "name", "parent"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class ShareFr(BaseModel):
    id = AutoField()
    minutes = IntegerField(null=False, default=0)
    mcnt = IntegerField(null=False, default=0)
    hours = IntegerField(null=False, default=0)
    hcnt = IntegerField(null=False, default=0)
    days = IntegerField(null=False, default=0)
    dcnt = IntegerField(null=False, default=0)
    pan_account_id = IntegerField(null=False)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "minutes", "mcnt", "hours", "hcnt", "days", "dcnt", "pan_account_id"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class ShareLogs(BaseModel):
    id = AutoField()
    fs_id = CharField(null=False, max_length=64)
    filename = CharField(null=True, max_length=256)
    password = CharField(null=False, max_length=8)
    period = IntegerField(null=False, default=1)
    share_id = CharField(null=True, max_length=64)
    link = CharField(null=True, max_length=1024)
    dlink = CharField(null=True, max_length=1024)
    err = CharField(null=True, max_length=1024)
    shorturl = CharField(null=True, max_length=128)
    randsk = CharField(null=True, max_length=128)
    uk = CharField(null=True, max_length=32)
    md5_val = CharField(null=True, max_length=64)
    pin = IntegerField(null=False, default=0)
    account_id = IntegerField(null=False, default=0)
    is_black = IntegerField(null=False, default=0)
    is_failed = IntegerField(null=False, default=0)
    pan_account_id = IntegerField(null=False)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "fs_id", "filename", "password", "share_id", "period", "link", "pin", "dlink", "account_id",
                              "uk", "randsk", "is_black", "pan_account_id", "err", "is_failed"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())

    def common_short_url(self):
        surl = str(self.shorturl) if self.shorturl else str(self.link)
        idx = surl.rfind("/s/1")
        if idx > 0:
            return surl[idx+4:]
        return self.shorturl

    def special_short_url(self):
        surl = str(self.shorturl) if self.shorturl else str(self.link)
        idx = surl.rfind("/s/")
        if idx > 0:
            return surl[idx+3:]
        return self.shorturl


class TransferLogs(BaseModel):
    id = AutoField()
    share_log_id = IntegerField(null=False)
    pan_account_id = IntegerField(null=False)
    fs_id = CharField(null=False, max_length=64)
    path = CharField(null=True, max_length=1024)
    dlink = CharField(null=True, max_length=1024)
    filename = CharField(null=True, max_length=256)
    size = BigIntegerField(null=False, default=0)
    category = IntegerField(null=False, default=0)
    md5_val = CharField(null=True, max_length=64)
    pin = IntegerField(null=False, default=0)
    account_id = IntegerField(null=False, default=0)
    expired_at = DateTimeField(null=True)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "fs_id", "share_log_id", "path", "size", "category", "md5_val", "pin", "dlink",
                              "filename", 'expired_at', "pan_account_id"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class WorkerLoadMap(Model):
    id = AutoField()

    ip = CharField(null=False,max_length=64)
    exchange = CharField(null=False,max_length=16)
    default_quota_cnt = IntegerField(null=False,default=10)
    accountname = CharField(null=False,max_length=32)
    constraint_params = CharField(null=False,max_length=128)
    grain = IntegerField(null=False,default=1)
    ismaster = IntegerField(null=False,default=0)
    status = IntegerField(null=False,default=0)
    cmd = IntegerField(null=False,default=0)
    updated_at = DateTimeField(default=datetime.datetime.now, constraints=db_update_field_sql())

    class Meta:
        db_table = 'worker_load_map'
        database = db

    def equals(self, wlm):
        if wlm:
            return (wlm.ip == self.ip and self.exchange == wlm.exchange
                    and self.default_quota_cnt == wlm.default_quota_cnt and self.accountname == wlm.accountname
                    and self.constraint_params == wlm.constraint_params and self.grain == wlm.grain
                    and self.ismaster == wlm.ismaster)
        return False


class UserRootCfg(BaseModel):
    id = AutoField()
    fs_id = CharField(null=True, max_length=64, index=True)
    filename = CharField(null=True, max_length=256)
    account_id = IntegerField(null=False, default=0)
    panacc = IntegerField(null=True, default=0)
    pin = IntegerField(null=False, default=0, index=0)
    source = CharField(null=True, max_length=16, index=True)
    desc = CharField(null=True, max_length=256)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "fs_id", "filename", "account_id", "pin", "panacc", "source", "desc"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class LoopAdTask(BaseModel):
    id = AutoField()
    started_at = DateTimeField(null=True)
    ended_at = DateTimeField(null=True)
    fr = IntegerField(null=False, default=0)
    pin = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "started_at", "ended_at", "fr", "pin"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class AdSource(BaseModel):
    id = AutoField()
    task_id = IntegerField(null=False)
    idx = IntegerField(null=False, default=0)
    srcurl = CharField(null=True, max_length=512)
    type = IntegerField(null=False, default=0)
    pin = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "task_id", "idx", "srcurl", "type", "pin"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


# 权限部分
class AuthUser(BaseModel):
    acc_id = IntegerField(null=False, default=0)
    org_id = IntegerField(null=False, default=0, index=True)
    ref_id = IntegerField(null=False, default=0, index=True)
    role_id = IntegerField(null=False, default=0)
    type = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["acc_id", "org_id", "ref_id", "role_id", "type"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)

    class Meta:
        database = db
        primary_key = CompositeKey('acc_id')


class UReference(BaseModel):
    id = AutoField()
    pin = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "pin"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class Fun(BaseModel):
    id = AutoField()
    code = IntegerField(null=False, unique=True)
    desc = CharField(null=True, max_length=128)
    type = IntegerField(null=False, default=0)
    pin = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "code", "desc", "type", "pin"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class Role(BaseModel):
    id = AutoField()
    parent = IntegerField(null=False, default=0)
    base_fun = IntegerField(null=False, default=0)
    default_path = CharField(null=True, max_length=256)
    ext_fun = CharField(null=True, max_length=256)
    desc = CharField(null=True, max_length=128)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "parent", "base_fun", "default_path", "ext_fun", "desc"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class RoleExtend(Model):
    role_id = IntegerField(null=False, default=0)
    parent = IntegerField(null=False, default=0)

    class Meta:
        database = db
        primary_key = CompositeKey('role_id', 'parent')

    @classmethod
    def field_names(cls):
        return ["role_id", "parent"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class Org(BaseModel):
    id = AutoField()
    parent = IntegerField(null=False, default=0)
    name = CharField(null=True, max_length=128)
    pin = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "parent", "name", "pin"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class OrgOrg(Model):
    org_id = IntegerField(null=False, default=0)
    parent = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return ["org_id", "parent"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())

    class Meta:
        database = db
        primary_key = CompositeKey('org_id', 'parent')


class UserRefExtend(Model):
    acc_id = IntegerField(null=False, default=0)
    ref_id = IntegerField(null=False, default=0)

    class Meta:
        database = db
        primary_key = CompositeKey('acc_id', 'ref_id')

    @classmethod
    def field_names(cls):
        return ["acc_id", "ref_id"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class UserRoleExtend(Model):
    acc_id = IntegerField(null=False, default=0)
    role_id = IntegerField(null=False, default=0)

    class Meta:
        database = db
        primary_key = CompositeKey('acc_id', 'role_id')

    @classmethod
    def field_names(cls):
        return ["acc_id", "role_id"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


class UserOrgExtend(Model):
    acc_id = IntegerField(null=False, default=0)
    org_id = IntegerField(null=False, default=0)

    class Meta:
        database = db
        primary_key = CompositeKey('acc_id', 'org_id')

    @classmethod
    def field_names(cls):
        return ["acc_id", "org_id"]

    @classmethod
    def to_dict(cls, instance):
        return object_to_dict(instance, cls.field_names())


# 商品部分
class Product(BaseModel):
    id = AutoField()
    pro_no = CharField(null=False, max_length=64, unique=True)
    isdir = IntegerField(null=False, default=0)
    name = CharField(null=True, max_length=256)
    fs_id = CharField(null=False, max_length=64)
    ref_id = IntegerField(null=False, default=0)
    data_id = IntegerField(null=False, default=0)
    price = IntegerField(null=False, default=0)  # 分
    size = BigIntegerField(null=False, default=0)
    pin = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "pro_no", "isdir", "name", "fs_id", "ref_id", "data_id", "price", "size", "pin"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class Order(BaseModel):
    id = AutoField()
    ord_no = CharField(null=False, max_length=64, unique=True)
    state = IntegerField(null=False, default=0)
    total = IntegerField(null=False, default=0)  # 分
    ref_id = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "ord_no", "state", "ref_id", "total"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class OrderItem(BaseModel):
    id = AutoField()
    ord_id = IntegerField(null=False, default=0)
    pro_no = CharField(null=False, max_length=64)
    price = IntegerField(null=False, default=0)  # 分

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "ord_id", "pro_no", "price"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class Assets(BaseModel):
    id = AutoField()
    ord_no = CharField(null=False, max_length=64)
    pro_no = CharField(null=False, max_length=64)
    fs_id = CharField(null=False, max_length=64)
    isdir = IntegerField(null=False, default=0)
    ref_id = IntegerField(null=False, default=0)
    price = IntegerField(null=False, default=0)  # 分
    desc = CharField(null=True, max_length=256)
    format_size = CharField(null=False, max_length=64)
    pin = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return BASE_FIELDS + ["id", "ord_no", "pro_no", "fs_id", "isdir", "ref_id", "desc", "format_size", "price", "pin"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


class ShareApp(Model):
    app_id = CharField(null=False, max_length=64)
    name = CharField(null=True, max_length=128)

    @classmethod
    def field_names(cls):
        return ["app_id", "name"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)

    class Meta:
        database = db
        primary_key = CompositeKey('app_id')


class AppCfg(BaseModel):
    id = AutoField()
    key = CharField(null=False, max_length=20, index=True)
    name = CharField(null=True, max_length=64)
    val = CharField(null=True, max_length=2014)
    type = CharField(null=True, max_length=10)
    platform = CharField(null=True, max_length=32)
    pin = IntegerField(null=False, default=0)

    @classmethod
    def field_names(cls):
        return ["key", "name", "val", "type", "platform"]

    @classmethod
    def to_dict(cls, instance, excludes=[]):
        return object_to_dict(instance, cls.field_names(), excludes)


if '__main__' == __name__:
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "../")))
    init_db()
