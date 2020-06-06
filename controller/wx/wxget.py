# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/26
"""
from controller.action import BaseHandler
from controller.auth_service import auth_service
from utils.constant import USER_TYPE
from controller.wx.wx_service import wx_service
from controller.wx.goods_service import goods_service
from controller.payment.payment_service import payment_service
from utils import wxapi, decrypt_id

import json


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
        elif u"openid" == cmd:
            code = params["code"]
            print("openid code:", code)
            if code:
                rsjson = wxapi.get_openid(code)
                openid = rsjson['openid']
                session_key = rsjson['session_key']
                print("session_key =========================:", session_key)
                print("openid =========================:", openid)
                if openid:
                    wx_user = params.get("user", {})
                    user_dict = wx_service.wx_sync_login(openid, session_key, self.guest, wx_user)
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
            print("raw:", raw, ",wx_id:", wx_id)
            u = wx_service.fetch_wx_account(wx_id)
            if u:
                info = wx_service.extractUserInfo(u.session_key, raw, iv)
                if info:
                    wx_service.update_wx_account(info, u.id)
                    if u.account_id == self.guest.id:
                        result = auth_service.wx_sync_login(u)
                        # if result:
                        #     ref_id = result['ref_id']
                        #     signed_rs = payment_service.check_signed(ref_id)
                        #     rs["state"] = signed_rs
            rs = wx_service.profile(wx_id, self.guest)
            if "state" in rs and "cr_id" in rs["state"]:
                rs["state"]["cr_id"] = 0
        elif "signed" == cmd:
            if self.guest.id == self.user_id:
                rs = {
                    "balance": 0,
                    "amount": 0,
                    "frozen_amount": 0
                }
            else:
                payment_service.reward_credit_by_signed(self.user_id, self.ref_id)
                rs = payment_service.query_credit_balance(self.user_id)
            if "state" in rs and "cr_id" in rs["state"]:
                rs["state"]["cr_id"] = 0

        elif "profile" == cmd:
            fuzzy_wx_id = params.get('uid', None)
            if not fuzzy_wx_id:
                wx_id = 0
            else:
                wx_id = decrypt_id(fuzzy_wx_id)
            print("user_id:", self.user_id, ",ref_id:", self.ref_id, ", guest id:", self.guest.id, ",payload:", self.user_payload)
            if self.token and self.user_id != self.guest.id:
                rs = wx_service.simple_profile(self.user_id, self.ref_id, wx_id, self.token)
            else:
                rs = wx_service.guest_profile(self.guest)
            if "state" in rs and "cr_id" in rs["state"]:
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
