# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/29
"""
from peewee import SQL, Model, DateTimeField
from playhouse.pool import PooledMySQLDatabase
from playhouse.shortcuts import ReconnectMixin
from cfg import mysql_worker_config as config
import datetime

BATCH_DB_USER = config["user"]  # 'market'
BATCH_DB_PASSWORD = config["password"]  # 'market'
# BATCH_DB_HOST='172.31.140.249'
BATCH_DB_HOST = config["host"]  # '127.0.0.1'
BATCH_DB_PORT = config["port"]  # '3306'
BATCH_DB_NAME = config["db"]  # 'liquidity'

BATCH_DB_URL = 'mysql://%s:%s@%s:%s/%s' % (BATCH_DB_USER, BATCH_DB_PASSWORD, BATCH_DB_HOST, BATCH_DB_PORT, BATCH_DB_NAME)
BASE_FIELDS = ["created_at", "updated_at"]


def db_connect(url):
    print("Use database : %s" % (url))
    from playhouse.db_url import connect
    db = connect(url, False, **{"sql_mode": "traditional"})
    return db


class RetryMySQLDatabase(ReconnectMixin, PooledMySQLDatabase):
    _instance = None

    @staticmethod
    def db_instance():
        if not RetryMySQLDatabase._instance:
            RetryMySQLDatabase._instance = RetryMySQLDatabase(
                BATCH_DB_NAME, max_connections=5, stale_timeout=300, host=BATCH_DB_HOST, user=BATCH_DB_USER,
                password=BATCH_DB_PASSWORD, port=BATCH_DB_PORT
            )
        return RetryMySQLDatabase._instance
        pass

    def sequence_exists(self, seq):
        pass


try:
    db_exist = 'db' in locals() or 'db' in globals()
    if not db_exist:
        # db = db_connect(BATCH_DB_URL)
        db = RetryMySQLDatabase.db_instance()
        print("db not exist.")
except Exception:
    # db = db_connect(BATCH_DB_URL)
    db = RetryMySQLDatabase.db_instance()


def db_create_field_sql():
    if BATCH_DB_URL.find("mysql")>=0:
        return [SQL("DEFAULT current_timestamp")]
    else:
        return [SQL("DEFAULT (datetime('now'))")]


def db_update_field_sql():
    if BATCH_DB_URL.find("mysql") >= 0:
        return [SQL("DEFAULT current_timestamp ON UPDATE CURRENT_TIMESTAMP")]
    else:
        return [SQL("DEFAULT (datetime('now'))")]


class BaseModel(Model):
    class Meta:
        # print("db=%s" % db)
        database = db

    created_at = DateTimeField(index=True, constraints=db_create_field_sql())
    updated_at = DateTimeField(default=datetime.datetime.now, constraints=db_update_field_sql())
