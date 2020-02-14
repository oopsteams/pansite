# -*- coding: utf-8 -*-
"""
Created by susy at 2019/10/17
"""
import os
from tornado.ioloop import IOLoop
from tornado.web import Application, StaticFileHandler
from tornado.httpserver import HTTPServer
from cfg import redis_config, service
from controller.action import *
from controller.open_action import *
from controller.pan_manage_action import *
from controller.user_action import *
from controller.middle_ware import get_middleware

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
        (r"/man/[^/]+", ManageHandler, dict(middleware=middle_list)),
        (r"/open/[^/]+", OpenHandler, dict(middleware=middle_list)),
        (r"/user/[^/]+", UserHandler, dict(middleware=middle_list)),
        (r"/login/", MainHandler, dict(middleware=middle_list)),
        (r"/register/", MainHandler, dict(middleware=middle_list)),
        (r"/access_code/", MainHandler, dict(middleware=middle_list)),
        (r"/ready_login/", MainHandler, dict(middleware=middle_list)),
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
