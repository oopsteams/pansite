# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/26
"""
from controller.action import BaseHandler
from controller.auth_service import auth_service
from utils.constant import USER_TYPE
from controller.wx.wx_service import wx_service
from controller.wx.goods_service import goods_service
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
                    rs['openid'] = openid
                    user_dict = wx_service.wx_sync_login(openid, session_key, self.guest)
                    # rs['user'] = {'uid': uid, 'sync': 0, 'pin': Mission.GUEST(), 'ri': rinclude, 're': '',
                    #               'orgid': orgid, 'deptid': deptid}
                    rs['user'] = user_dict
            return rs

        elif "userrawdata" == cmd:
            raw = params['raw']
            uid = params['uid']
            iv = params['iv']
            print("raw,uid:", raw, uid)

            u = wx_service.fetch_wx_account(uid)
            if u:
                info = wx_service.extractUserInfo(u.session_key, raw, iv)
                if info:
                    wx_service.update_wx_account(info, u.id)
        elif "profile" == cmd:
            uid = params.get('uid', None)
            if not uid:
                uid = 0
            rs = wx_service.profile(uid, self.guest)
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
            gid = int(params.get('gid', '0'))
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
        elif "queryproduct" == cmd:
            size = 100
            pid = int(params.get('pid', '0'))
            page = int(params.get('page', '1'))
            pin = int(params.get('pin', '-1'))
            products = []
            cp_dict = goods_service.query_product_dict(pid)
            if cp_dict:
                products.append(cp_dict)
            rs['products'] = products
            spus = []
            if products:
                spus = goods_service.query_spu_by_pid(pid, products[0]['tpcid'])
                rs['goods'] = goods_service.query_goods_by_pid(pid)
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

    def get(self):
        rs = {"status": 0}
        cmd = self.get_argument("cmd", "")
        name = self.get_argument("name", "")
        params = {"cmd": cmd, "name": name}
        if "openid" == cmd:
            params["code"] = self.get_argument("code", "")
        rs = self.parseCMD(**params)

        self.to_write_json(rs)

    def post(self):
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
