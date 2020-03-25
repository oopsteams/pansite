# -*- coding: utf-8 -*-
"""
Created by susy at 2020/2/5
"""
from controller.action import BaseHandler
from controller.pro_service import product_service
from tornado.web import authenticated
from utils.constant import buy_success_format
from utils import decrypt_id
from controller.auth_service import auth_service
import json


class ProductHandler(BaseHandler):

    def post(self):
        self.get()

    @authenticated
    def get(self):
        path = self.request.path
        rs = {}
        if path.endswith("/untag"):
            # itemid = self.get_argument("itemid")
            item_fuzzy_id = self.get_argument("itemid")
            itemid = int(decrypt_id(item_fuzzy_id))
            product_service.un_tag_product(int(itemid))
            self.to_write_json(rs)
        elif path.endswith("/tag"):
            p_name = self.get_argument("p_name", "")
            p_price = self.get_argument("p_price", "0")
            isdir = self.get_argument("isdir")
            layer = self.get_argument("layer")
            # itemid = self.get_argument("itemid")
            item_fuzzy_id = self.get_argument("itemid")
            itemid = int(decrypt_id(item_fuzzy_id))
            if self.ref_id:
                rfid = self.ref_id
                print("p_name:", p_name, "p_price:", p_price, "isdir:", isdir, "layer:", layer, "itemid:", itemid)
                product = product_service.tag_product(rfid, int(itemid), layer, float(p_price))
                if product:
                    rs = {"state": 0, "pro_no": product.pro_no, "price": product.price}
            else:
                rs = {"state": -1}
            self.to_write_json(rs)
        elif path.endswith("/buy"):
            rs = {"state": 0}
            item_fuzzy_id = self.get_argument("itemid")
            itemid = int(decrypt_id(item_fuzzy_id))
            user_fuzzy_id = self.get_argument("sel")
            assets = product_service.buy_product(int(itemid), user_fuzzy_id)
            print("itemid:", itemid, "user_fuzzy_id:", user_fuzzy_id)
            if not assets:
                rs = {"state": -1}
            else:
                rs['msg'] = buy_success_format(assets.desc, assets.price)
            self.to_write_json(rs)
        elif path.endswith("/su"):
            size = 5
            page = int(self.get_argument("page", "1"))
            kw = self.get_argument("kw", "")
            offset = (page-1) * size if page > 0 else 0
            items = product_service.user_list(kw, size, offset)
            hasnext = False
            if len(items) == size:
                hasnext = True
            rs = {"datas": items, "hasnext": hasnext, "haspre": offset > 0, "page": page}
            self.to_write_json(rs)

        elif path.endswith("/assets"):
            page = int(self.get_argument("page", "1"))
            total = int(self.get_argument("total", "0"))
            rs = product_service.search_assets(self.ref_id, page, total)
            self.to_write_json(rs)

        elif path.endswith("/checkcopyfile"):
            item_fuzzy_id = self.get_argument("id")
            pids = self.get_argument("pids")
            tag = self.get_argument("tag")
            itemid = int(decrypt_id(item_fuzzy_id))

            result = product_service.check_copy_file(self.user_id, self.ref_id, self.default_pan_id, itemid, pids, tag)
            # result = product_service.test_async_task(self.user_id, self.default_pan_id)
            self.to_write_json(result)

        elif path.endswith("dlink"):
            item_fuzzy_id = self.get_argument("id")
            item_id = int(decrypt_id(item_fuzzy_id))
            print("dlink item_id:", item_id)
            sub_params = product_service.checkout_dlink(item_id, self.user_id, self.ref_id)
            result = {"subs": sub_params}
            self.to_write_json(result)
