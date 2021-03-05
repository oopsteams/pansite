# -*- coding: utf-8 -*-
"""
Created by susy at 2020/3/24
"""
import json
from controller.action import BaseHandler
from controller.service import pan_service
from controller.auth_service import auth_service
from utils import CJsonEncoder, get_payload_from_token, decrypt_user_id, get_now_ts, decrypt_id, log as logger
from cfg import get_bd_auth_uri


class MainHandler(BaseHandler):

    def get(self):
        path = self.request.path
        if path.endswith("/login/"):
            logger.info("login body:{}".format(self.request.body))
            # self.get_argument("mobile_no")
            user_name = self.get_body_argument("mobile_no")
            user_passwd = self.get_body_argument("password")
            is_single = self.get_body_argument('single', '0', True) == '1'
            result = pan_service.check_user(user_name, user_passwd)
            logger.info("result:{}".format(result))
            if is_single and 'token' in result:
                result = {'token': result['token'], 'login_at': result['login_at'], 'id': result['id']}
            self.to_write_json(result)
        elif path.endswith("/bdlogin/"):
            jsonstr = self.request.body
            result = {}
            if jsonstr:
                params = json.loads(jsonstr)
                logger.info('params:{}'.format(params))
                result = auth_service.bd_sync_login(params)
            self.to_write_json(result)
            pass
        elif path.endswith("/authlogin/"):
            result = {'tag': 'authlogin'}
            for f in self.request.query_arguments:
                logger.info("{}:{}".format(f, self.get_argument(f)))
            self.to_write_json(result)
        elif path.endswith("/register/"):
            self.render('register.html')
        elif path.endswith("/essay/"):
            self.render('newessay.html')
        elif path.endswith("/access_code/"):
            logger.info("login body:".format(self.request.body))
            token = self.get_body_argument("token")
            code = self.get_body_argument("code")
            pan_name = self.get_body_argument("pan_name")
            refresh_str = self.get_body_argument("refresh")
            # print('refresh_str:', refresh_str)
            can_refresh = True
            if refresh_str == '0':
                can_refresh = False
            payload = get_payload_from_token(token)
            user_id = decrypt_user_id(payload['id'], )
            # print("payload:", payload)
            # print("can_refresh:", can_refresh)
            access_token, pan_acc_id, err = pan_service.get_pan_user_access_token(user_id, code, pan_name, can_refresh)
            need_renew_pan_acc = pan_service.load_pan_acc_list_by_user(user_id)
            result = {"result": "ok", "access_token": access_token, "pan_acc_id": pan_acc_id, "token": self.token}
            if need_renew_pan_acc:
                result['pan_acc_list'] = need_renew_pan_acc
            if err:
                result = {"result": "fail", "error": err}
            logger.info("result:{}".format(result))
            self.to_write_json(result)
        elif path.endswith("/save/"):
            mobile_no = self.get_body_argument("mobile_no")
            passwd = self.get_body_argument("password")
            token, fuzzy_id, err = pan_service.save_user(mobile_no, passwd)
            result = {"result": "ok", "token": token, "fuzzy_id": fuzzy_id}
            if err:
                result = {"result": "fail", "error": err}
            logger.info("result:{}".format(result))
            self.write(json.dumps(result))
        elif path.endswith("/ready_login/"):
            v = self.get_cookie('pan_site_is_web')
            ref = self.get_cookie('pan_site_ref')
            _force = self.get_cookie('pan_site_force')
            self.set_cookie('pan_site_force', '')
            logger.info("ready_login v:{}".format(v))
            logger.info("ready_login ref:{}".format(ref))
            uri = 'https://www.oopsteam.site/authlogin/'
            # uri = 'http://localhost:8080/authlogin'
            if '1' == v:
                self.render('login.html', **{'ref': ref, 'force': _force})
                # self.set_header("Referer", "https://www.oopsteam.site/index.html")
                # self.redirect(get_bd_auth_uri(uri, display='page'))
            else:
                self.to_write_json({"result": "fail", "state": -1, 'force': _force,
                                    "lg": get_bd_auth_uri(uri)})
        elif path.endswith("/fresh_token/"):
            pan_id = self.get_argument('panid')
            pan_service.fresh_token(pan_id)
            self.to_write_json({"result": "ok"})
        else:
            logger.debug("path:", path)
            if path and len(path) > 1 and path[0] == '/':
                path = path[1:]
                self.render(path, **{'ref': '', 'force': ''})
            else:
                self.render('index.html', **{'ref': '', 'force': ''})

    def post(self):
        self.get()
