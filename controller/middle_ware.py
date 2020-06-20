# -*- coding: utf-8 -*-
"""
Created by susy at 2020/1/27
"""
from utils import singleton, get_payload_from_token, get_now_ts, decrypt_user_id, log as logger
from utils.constant import USER_TYPE
from tornado.web import RequestHandler


class MiddleWare(object):
    def __init__(self):
        super().__init__()

    def process_request(self, handler: RequestHandler):
        pass

    def process_response(self, handler: RequestHandler):
        pass


@singleton
class CheckLogin(MiddleWare):

    def process_request(self, handler: RequestHandler):
        headers = handler.request.headers
        token = headers.get('Suri-Token', None)
        if not token:
            token = headers.get('SURI-TOKEN', None)
        if not token:
            token = handler.get_argument('tk', None, True)
            handler.is_web = True
        logger.info("Middle CheckLogin in token:{}".format(token))
        if token and not isinstance(token, str):
            token = None
        if "undefined" == token:
            token = None
        if "[object Null]" == token:
            token = None
        if "login" != token and token:
            try:
                handler.user_payload = get_payload_from_token(token)
                handler.token = token
                if handler.user_payload:
                    if 'ext' in handler.user_payload:
                        handler.user_type = handler.user_payload['ext'].get('t', USER_TYPE['SINGLE'])
                    if 'id' in handler.user_payload:
                        fuzzy_user_id = handler.user_payload['id']
                        handler.user_id = decrypt_user_id(fuzzy_user_id)
                        handler.user_payload['user_id'] = handler.user_id
                    if '_p' in handler.user_payload:
                        fuzzy_pan_id = handler.user_payload['_p']
                        handler.default_pan_id = decrypt_user_id(fuzzy_pan_id)
                    if 'au' in handler.user_payload:
                        au = handler.user_payload['au']
                        handler.ref_id = au['rfid']
                        handler.org_id = au['oid']
            except Exception:
                logger.error("Parse Token Failed![{}]".format(token), exc_info=True)


@singleton
class CheckAuth(MiddleWare):

    def process_request(self, handler: RequestHandler):
        # print("CheckAuth in ....")
        handler.query_path = handler.request.path
        pass


def get_middleware() -> list:
    return [CheckLogin(), CheckAuth()]


