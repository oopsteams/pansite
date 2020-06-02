# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/26
"""
from controller.action import BaseHandler
from controller.auth_service import auth_service
from controller.wx.goods_service import goods_service
from dao.models import CourseProduct
from utils import obfuscate_id, decrypt_id
import json


class WXAppPut(BaseHandler):

    def parsePutCMD(self, **params):
        cmd = u'' + params.get("cmd", "")
        print("cmd:", cmd)
        rs = {"status": 0}
        if "scan" == cmd:
            code = params["code"]
            print("code:", code)
        elif "newproduct" == cmd:
            cid = int(params.get("cid", '0'))
            tpcid = params.get("tpcid", '0')
            pname = params.get("name", "")
            ip_rule = params.get("ip_rule", "")
            netweight = float(params.get("netweight", '0'))
            # sugarweight = float(params.get("sugar", '0'))
            desc = params.get("desc", "")
            spuids = params.get("spuids", "")
            spustructids = params.get("spustructids", "")
            print("newproduct params:", params)
            if pname:
                p: CourseProduct = goods_service.new_product(pname, netweight, tpcid, cid, desc, self.ref_id, spuids, spustructids, ip_rule)
                rs['pid'] = obfuscate_id(p.pid)

        elif "newgoods" == cmd:
            fuzzy_pid = params.get("pid", None)
            price = int(float(params.get("price", '0')) * 100)
            if fuzzy_pid:
                pid = decrypt_id(fuzzy_pid)
                rs = goods_service.new_goods(pid, price, self.ref_id)
            else:
                rs["status"] = -1
                rs["error"] = "Please Select one Product!"

        elif "offgoods" == cmd:
            fuzzy_gid = params.get("gid", None)
            if fuzzy_gid:
                gid = decrypt_id(fuzzy_gid)
                goods_service.offgoods(gid)

        elif "updateimg" == cmd:
            fuzzy_pid = params.get("pid", None)
            url = params.get("url", "")
            fuzzy_uid = params.get("uid", None)
            tag = params.get("tag", "")
            if url and fuzzy_pid:
                pid = decrypt_id(fuzzy_pid)
                p_ref_id = decrypt_id(fuzzy_uid)
                basepath = self.context['basepath']
                istop = int(params.get("top", "0"))
                goods_service.update_img(pid, url, istop, cmd, p_ref_id, basepath)
                rs['istop'] = istop
            else:
                rs['status'] = -1
                rs['error'] = "Product[{}] not exists!".format(fuzzy_pid)

        return rs

    def get(self):

        cmd = self.get_argument("cmd", "")
        name = self.get_argument("name", "")
        params = {"cmd": cmd, "name": name}
        if "openid" == cmd:
            params["code"] = self.get_argument("code", "")
        rs = self.parsePutCMD(**params)

        self.to_write_json(rs)

    def post(self):
        # self.get()
        rs = {"status": 0}
        cmd = self.get_argument("cmd", "")
        bd = self.request.body
        _params = json.loads(bd)
        if cmd:
            _params['cmd'] = cmd
        if _params:
            rs = self.parsePutCMD(**_params)
        self.to_write_json(rs)
