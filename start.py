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
from controller.wx.wxget import WXAppGet
from controller.wx.wxput import WXAppPut
from controller.wx.wxpush import WXAppPush
from controller.wx.wxkf import WXAppKf
from controller.wx.wxupload import WXAppUpload
from utils import log as logger
scheduler = TornadoScheduler()
scheduler.start()


guest_user = None
base_dir = os.path.dirname(__file__)
context = dict(guest=None, basepath=base_dir)


def update_sys_cfg(release=True):
    try:
        open_service.sync_cfg()
        open_service.sync_tags()
        context['guest'] = open_service.guest_user()
    except Exception as e:
        print("update_sys_cfg err:", e)
        pass
    finally:
        if release:
            try_release_conn()


# @scheduler.scheduled_job('cron',hour=16,minute=9,second=20)
def scheduler_clear_all_expired_share_log():
    try:
        sync_pan_service.clear_all_expired_share_log()
        update_sys_cfg(False)
    except Exception as e:
        print("scheduler_clear_all_expired_share_log err:", e)
        pass
    finally:
        try_release_conn()


def update_access_token():
    try:
        # from dao.models import PanAccounts
        # sync_pan_service.clear_all_expired_share_log()
        # pan_acc_list = PanAccounts.select().where(PanAccounts.user_id == 1)
        # for pan_acc in pan_acc_list:
        #     logger.info("will validation pan acc id:{}, name:{}".format(pan_acc.id, pan_acc.name))
            # auth_service.check_pan_token_validation(pan_acc)
        logger.info("bj service will ignore [update_access_token] task.")
        # from controller.wx.wx_service import wx_service
        # wx_service.get_valid_access_token()
    except Exception as e:
        traceback.print_exc()
        print("update_access_token err:", e)
        pass
    finally:
        try_release_conn()


scheduler.add_job(scheduler_clear_all_expired_share_log, 'interval', minutes=120,
                  id='scheduler_clear_all_expired_share_log')
scheduler.add_job(update_access_token, 'interval', minutes=10, id='update_access_token')

update_sys_cfg()


if __name__ == "__main__":
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
        (r"/source/[^/]+", PanHandler, dict(middleware=middle_list, context=context)),
        (r"/product/[^/]+", ProductHandler, dict(middleware=middle_list, context=context)),
        (r"/man/[^/]+", ManageHandler, dict(middleware=middle_list, context=context)),
        (r"/open/[^/]+", OpenHandler, dict(middleware=middle_list, context=context)),
        (r"/rpc/[^/]+", OpenHandler, dict(middleware=middle_list, context=context)),
        (r"/async/[^/]+", AsyncHandler, dict(middleware=middle_list, context=context)),
        (r"/user/[^/]+", UserHandler, dict(middleware=middle_list, context=context)),
        (r"/login/", MainHandler, dict(middleware=middle_list, context=context)),
        (r"/bdlogin/", MainHandler, dict(middleware=middle_list, context=context)),
        (r"/register/", MainHandler, dict(middleware=middle_list, context=context)),
        (r"/access_code/", MainHandler, dict(middleware=middle_list, context=context)),
        (r"/ready_login/", MainHandler, dict(middleware=middle_list, context=context)),
        (r"/authlogin/", MainHandler, dict(middleware=middle_list, context=context)),
        (r"/fresh_token/", MainHandler, dict(middleware=middle_list, context=context)),
        (r"/save/", MainHandler, dict(middleware=middle_list, context=context)),

        (r"/wx/put", WXAppPut, dict(middleware=middle_list, context=context)),
        (r"/wx/get", WXAppGet, dict(middleware=middle_list, context=context)),
        (r"/wx/push", WXAppPush, dict(middleware=middle_list, context=context)),
        (r"/wx/kf", WXAppKf, dict(middleware=middle_list, context=context)),
        (r"/wx/upload", WXAppUpload, dict(middleware=middle_list, context=context)),
        # (r"/wx/push", WXAppPush),

        (r"/.*\.html", MainHandler, dict(middleware=middle_list)),
        (r"/(.*\.txt)", StaticFileHandler, dict(url=settings['source'])),
        # (r"/(apple-touch-icon\.png)",StaticFileHandler,dict(path=settings['static_path'])),
    ], **settings)

    port = service['port']

    # server = HTTPServer(application, ssl_options=ssl_ctx)
    server = HTTPServer(application)
    server.listen(port)
    # server.listen(port, '127.0.0.1')
    # application.listen(port)
    logger.info("Listen HTTP @ %s" % port)
    IOLoop.instance().start()
