# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/26
"""
from controller.action import BaseHandler
from controller.auth_service import auth_service
from utils.constant import LOGIN_TOKEN_TIMEOUT
from controller.wx.wx_service import wx_service
from controller.wx.goods_service import goods_service
from controller.payment.payment_service import payment_service
from controller.open_service import open_service
from utils import wxapi, decrypt_id, log, get_now_ts, get_payload_from_token, constant, caches

import json


def build_role_include(user_payload):
    au = user_payload['au']
    oid = au['oid']
    if oid in [1, 2, 4]:
        base_val = user_payload['ext']['bf']
        if (base_val & constant.FUN_BASE['DEL']) == constant.FUN_BASE['DEL']:
            return [2001]
    return []


class WXAppGet(BaseHandler):

    # def sendmsg(self, sn, params, cb, cb_key):
    #     context = {'cbok': False}
    #
    #     def _cb(tag, sn, txt):
    #         print("tag:%s,sn:%s,txt:%s" % (tag, sn, txt))
    #         context['cbok'] = True
    #         _json = json.loads(txt)
    #         cb(_json)
    #
    #     self.recv.delegate.addCB(cb_key, cb=_cb)
    #     msg = "m:%s:%s" % (sn, json.dumps(params))
    #     sid = self.recv.sid
    #     vid = self.recv.vid
    #     self.recv.sendmsg(sid, vid, self.recv.touid, msg=msg)
    #     dog = 25
    #     while not context['cbok'] and dog > 0:
    #         sleep(.2)
    #         dog = dog - 1
    #     if not context['cbok']:
    #         self.recv.sendmsg(sid, vid, self.recv.touid, msg=msg)
    #         dog = 20
    #         while not context['cbok'] and dog > 0:
    #             sleep(.2)
    #             dog = dog - 1
    #     if not context['cbok']:
    #         print("wait push service call timeout.")

    def wx_user(self):
        if self.guest and self.user_id:
            if self.guest.id == self.user_id:
                return self.guest
        if self.user_id:
            return wx_service.fetch_user_by_id(self.user_id)
        return None

    def parseCMD(self, **params):
        cmd = u'' + params.get("cmd", "")
        wx_user = params.get("user", {})
        print("cmd:", cmd)
        # header = self.request.headers
        rs = {"status": 0}
        # print("header", header)
        if u"ip" == cmd:
            rip = self.getRemoteIp()
            rs['ip'] = rip
            print("rip:%s" % rip)
        elif "test" == cmd:
            payment_service.clear_cache(self.user_id, self.ref_id)
        elif u"openid" == cmd:
            code = params["code"]
            fuzzy_source = params.get("source", None)
            print("openid code:", code)
            if code:
                rsjson = wxapi.get_openid(code)
                openid = rsjson['openid']
                session_key = rsjson['session_key']
                print("session_key =========================:", session_key)
                print("openid =========================:", openid)
                if openid:
                    wx_user = params.get("user", {})
                    source = 0
                    if fuzzy_source:
                        source = decrypt_id(fuzzy_source)
                    user_dict = wx_service.wx_sync_login(openid, session_key, self.guest, wx_user, source=source)
                    # rs['user'] = {'uid': self.guest, 'sync': 0, 'pin': Mission.GUEST(), 'ri': rinclude, 're': '',
                    #               'orgid': orgid, 'deptid': deptid}
                    rs = user_dict
                    rs['openid'] = openid
                    # rs['user'] = wx_service.check_openid(self.guest)
            return rs

        elif "userrawdata" == cmd:
            rs["signed"] = {
                "signed": False,
                "counter": -1
            }
            raw = params['raw']
            fuzzy_uid = params['uid']
            wx_id = decrypt_id(fuzzy_uid)
            iv = params['iv']
            # print("raw:", raw, ",wx_id:", wx_id)
            u = wx_service.fetch_wx_account(wx_id)
            if u:
                info = wx_service.extractUserInfo(u.session_key, raw, iv)
                if info:
                    wx_service.update_wx_account(info, u)
                    if u.account_id == self.guest.id:
                        auth_service.wx_sync_login(u)
                        result = auth_service.wx_sync_login(u)
                        self.token = result["token"]
                        self.user_payload = get_payload_from_token(self.token)
                        # if result:
                        #     ref_id = result['ref_id']
                        #     signed_rs = payment_service.check_signed(ref_id)
                        #     rs["state"] = signed_rs
            rs = wx_service.profile(wx_id, self.guest)
            rs['user']['ri'] = build_role_include(self.user_payload)
            print("userrawdata profile rs:", rs)
            if "state" in rs and "cr_id" in rs["state"]:
                rs["state"] = rs["state"].copy()
                rs["state"]["cr_id"] = 0
        elif "signed" == cmd:
            if self.guest.id == self.user_id:
                rs["balance"] = {
                    "balance": 0,
                    "amount": 0,
                    "frozen_amount": 0
                }
                rs["state"] = {
                    "signed": False,
                    "counter": -1
                }
            else:
                rs["state"] = payment_service.reward_credit_by_signed(self.user_id, self.ref_id)
                balance_rs = payment_service.query_credit_balance(self.user_id)
                rs["balance"] = balance_rs
            if "state" in rs and "cr_id" in rs["state"]:
                rs["state"] = rs["state"].copy()
                rs["state"]["cr_id"] = 0

        elif "ntoken" == cmd:
            fuzzy_wx_id = params.get('uid', None)
            if fuzzy_wx_id:
                caches.cache_service.put_on_not_exists(fuzzy_wx_id, get_now_ts())

        elif "profile" == cmd:
            fuzzy_wx_id = params.get('uid', None)
            if not fuzzy_wx_id:
                wx_id = 0
            else:
                wx_id = decrypt_id(fuzzy_wx_id)
            print("user_id:", self.user_id, ",ref_id:", self.ref_id, ", guest id:", self.guest.id, ",payload:", self.user_payload)
            new_token = self.token
            if self.token and self.user_id != self.guest.id:
                # print('payload:', self.user_payload, ctm, ctm - tm, LOGIN_TOKEN_TIMEOUT)
                need_new_token = caches.cache_service.rm(fuzzy_wx_id)
                if need_new_token:
                    acc = wx_service.get_acc_by_wx_acc({"account_id": self.user_id}, self.guest)
                    login_rs = auth_service.login_check_user(acc, source="wx")
                    new_token = login_rs['token']
                    self.user_payload = get_payload_from_token(new_token)
                rs = wx_service.simple_profile(self.user_id, self.ref_id, wx_id, new_token)
                rs['user']['ri'] = build_role_include(self.user_payload)
            else:
                rs = wx_service.guest_profile(self.guest)
            if "state" in rs and "cr_id" in rs["state"]:
                rs["state"] = rs["state"].copy()
                rs["state"]["cr_id"] = 0
            # if uid:
            #     ub = wx_service.fetch_wx_account(uid)
            #     if ub:
            #         rexclude = ""
            #         if ub.setting.rexclude:
            #             rexclude = ub.setting.rexclude
            #         rs['user'] = {'uid': uid, 'sync': 0, 'pin': ub.pin, 'ri': ub.setting.rinclude, 're': rexclude,
            #                       'name': ub.user.rname}
            #         rs['openid'] = ub.externid
            #         if hasattr(ub, 'orgprofile'):
            #             rs['user']['op'] = {'tips': ub.orgprofile.tips, 'ops': ub.orgprofile.ops}
            #         # if hasattr(ub,'user') and ub.user.code:
            #         #     rs['user']['code']=ub.user.code
            #         if hasattr(ub, 'user') and ub.user.deptid:
            #             rs['user']['deptid'] = ub.user.deptid
            #         if hasattr(ub, 'orgid') and hasattr(ub, 'org'):
            #             rs['user']['orgid'] = ub.orgid
            #             rs['user']['orgname'] = ub.org.alias

            return rs
        elif "querygoods" == cmd:
            fuzzy_gid = params.get('gid', None)
            goods = []
            if fuzzy_gid:
                gid = decrypt_id(fuzzy_gid)
                goods = goods_service.query_goods_by_gid(gid)
            rs['goods'] = goods
        elif "querygoodslist" == cmd:
            ordmapstr = params.get('ordmap', '')
            offset = int(params.get('offset', '0'))
            n = 5
            rs['size'] = n
            rs['offset'] = offset
            ordmap = {}
            if ordmapstr:
                ordmap = json.loads(ordmapstr)
            org_id = self.guest.auth_user.org_id
            goodslist = goods_service.query_goods_by_org(org_id, ordmap, offset, n)
            rs['goodslist'] = goodslist
        elif "queryproductlist" == cmd:
            size = 100
            page = int(params.get('page', '1'))
            pin = params.get('pin', None)
            if pin:
                pin = int(pin)
            print("user_payload:", self.user_payload)
            rs['list'] = goods_service.query_product_list_by_ref(self.ref_id, self.org_id, pin, page, size, False)
            rs['page'] = page
            rs['size'] = size
        elif "queryproduct" == cmd:
            size = 100
            fuzzy_pid = params.get('pid', None)
            page = int(params.get('page', '1'))
            # pin = int(params.get('pin', '-1'))
            products = []
            spus = []
            print("queryproduct fuzzy_pid:", fuzzy_pid)
            if fuzzy_pid:
                pid = int(decrypt_id(fuzzy_pid))
                cp_dict = goods_service.query_product(pid)
                if cp_dict:
                    products.append(cp_dict)
                rs['products'] = products
                if cp_dict:
                    spus = goods_service.query_spu_by_pid(pid, cp_dict['tpcid'])
                    goods_dict = goods_service.query_goods_by_pid(pid)
                    if goods_dict:
                        goods_dict['price'] = goods_dict['price'] / float(100)
                    rs['goods'] = goods_dict
            rs['spus'] = spus
            rs['page'] = page
            rs['size'] = size
            rs['cates'] = goods_service.query_category()
        elif "querysubcates" == cmd:
            cid = int(params.get('cid', '0'))
            lvl = int(params.get('lvl', '0'))
            cates = goods_service.query_sub_category(cid, lvl)
            rs['cates'] = cates
        elif "queryspu" == cmd:
            cid = int(params.get('cid', '0'))
            structs = goods_service.query_spu(cid)
            rs['structs'] = structs
        elif "queryimgs" == cmd:
            fuzzy_pid = params.get('pid')
            pid = int(decrypt_id(fuzzy_pid))
            imgs = goods_service.query_imgs(pid)
            rs['imgs'] = imgs
        elif "shared" == cmd:
            fs_id = params.get("fs_id", "")
            print("shared fs_id:", fs_id, ",params:", params)
            # freeze credit
            price = open_service.get_price(fs_id)
            pay_id = payment_service.freeze_credit(self.user_id, price)
            # rs = open_service.fetch_shared_skip_visible(fs_id)
            if pay_id:
                try:
                    rs = wxapi.rpc_shared(fs_id)
                    print("rpc return:", rs)
                    if rs['state'] == 0:
                        payment_service.active_frozen_credit(self.user_id)
                    else:
                        payment_service.un_freeze_credit_by_id(pay_id, price)
                    rs['balance'] = payment_service.query_credit_balance(self.user_id)
                except Exception:
                    log.error("rpc shared err.", exc_info=True)
                    payment_service.un_freeze_credit_by_id(pay_id, price)
                    rs = {'state': -1, 'err': 'rpc service ,bad gateway!'}
        return rs

    def check_header(self, tag):
        headers = self.request.headers
        for hk in headers:
            print(tag, ":", hk, "=", headers[hk])

    def get(self):
        self.check_header("wx get")
        # rs = {"status": 0}
        cmd = self.get_argument("cmd", "")
        name = self.get_argument("name", "")
        params = {"cmd": cmd, "name": name}
        if "openid" == cmd:
            params["code"] = self.get_argument("code", "")
        rs = self.parseCMD(**params)

        self.to_write_json(rs)

    def post(self):
        self.check_header("wx post")
        rs = {"status": 0}
        cmd = self.get_argument("cmd", "")
        bd = self.request.body
        _params = json.loads(bd)
        if cmd:
            _params['cmd'] = cmd
        if _params:
            # rs = yield gen.Task(self.parseCMD,**_params)
            # print "yield rs:",rs
            rs = self.parseCMD(**_params)
        print("rs:", rs)
        self.to_write_json(rs)
