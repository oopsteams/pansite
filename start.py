# -*- coding: utf-8 -*-
"""
Created by susy at 2019/10/17
"""
import os

from apscheduler.schedulers.tornado import TornadoScheduler
from tornado.ioloop import IOLoop
from tornado.web import Application, StaticFileHandler
from tornado.httpserver import HTTPServer
from cfg import service
from controller.action import *
from controller.open_action import *
from controller.pan_manage_action import *
from controller.user_action import *
from controller.pro_action import ProductHandler
from controller.middle_ware import get_middleware
from controller.async_action import AsyncHandler
from controller.main_action import MainHandler

scheduler = TornadoScheduler()
scheduler.start()


def update_sys_cfg(release=True):
    try:
        open_service.sync_cfg()
        open_service.sync_tags()
        if release:
            try_release_conn()
    except Exception:
        pass


# @scheduler.scheduled_job('cron',hour=16,minute=9,second=20)
def scheduler_clear_all_expired_share_log():
    try:
        print("will exec clear_all_expired_share_log!!!")
        sync_pan_service.clear_all_expired_share_log()
        update_sys_cfg(False)
        try_release_conn()
    except Exception:
        pass


def update_access_token():
    try:
        from dao.models import PanAccounts
        print("will exec update_access_token!!!")
        # sync_pan_service.clear_all_expired_share_log()
        pan_acc_list = PanAccounts.select().where(PanAccounts.user_id == 1)
        for pan_acc in pan_acc_list:
            print("will validation pan acc:", pan_acc.id, ",name;", pan_acc.name)
            auth_service.check_pan_token_validation(pan_acc)

        try_release_conn()
    except Exception:
        pass


scheduler.add_job(scheduler_clear_all_expired_share_log, 'interval', minutes=120,
                  id='scheduler_clear_all_expired_share_log')
scheduler.add_job(update_access_token, 'interval', minutes=10, id='update_access_token')

update_sys_cfg()


if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    settings = {
        "static_path": os.path.join(base_dir, "static"),
        "static_url_prefix": r"/static/",
        "source": os.path.join(base_dir, "source"),
        "cookie_secret": "4c917b5d90a5732cf34e7e5545138f9c",
        "xsrf_cookies": False,
        "login_url": "/ready_login/",
        "template_path": os.path.join(os.path.dirname(__file__), "templates")
    }
    middle_list = get_middleware()
    application = Application([
        # (r"/source/list", PanHandler, {'basepath': base_dir}),
        (r"/source/[^/]+", PanHandler, dict(middleware=middle_list)),
        (r"/product/[^/]+", ProductHandler, dict(middleware=middle_list)),
        (r"/man/[^/]+", ManageHandler, dict(middleware=middle_list)),
        (r"/open/[^/]+", OpenHandler, dict(middleware=middle_list)),
        (r"/async/[^/]+", AsyncHandler, dict(middleware=middle_list)),
        (r"/user/[^/]+", UserHandler, dict(middleware=middle_list)),
        (r"/login/", MainHandler, dict(middleware=middle_list)),
        (r"/bdlogin/", MainHandler, dict(middleware=middle_list)),
        (r"/register/", MainHandler, dict(middleware=middle_list)),
        (r"/access_code/", MainHandler, dict(middleware=middle_list)),
        (r"/ready_login/", MainHandler, dict(middleware=middle_list)),
        (r"/authlogin/", MainHandler, dict(middleware=middle_list)),
        (r"/fresh_token/", MainHandler, dict(middleware=middle_list)),
        (r"/save/", MainHandler, dict(middleware=middle_list)),
        (r"/.*\.html", MainHandler, dict(middleware=middle_list)),
        (r"/(.*\.txt)", StaticFileHandler, dict(url=settings['source'])),
        # (r"/(apple-touch-icon\.png)",StaticFileHandler,dict(path=settings['static_path'])),
    ], **settings)

    port = service['port']
    # server = HTTPServer(application, ssl_options=ssl_ctx)
    server = HTTPServer(application)
    server.listen(port)
    # application.listen(port)
    print("Listen HTTP @ %s" % port)
    IOLoop.instance().start()
