# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/29
"""
import os
from controller.base_service import BaseService
from utils import singleton, obfuscate_id, get_now_datetime
from dao.goods_dao import GoodsDao
from dao.models import Goods, Category, ProductImg, SPUStruct, CourseProduct


@singleton
class GoodsService(BaseService):

    def query_goods_by_org(self, org_id, order_map, offset, n):

        return GoodsDao.query_goods_by_org(org_id, order_map, offset, n)

    def query_goods_by_gid(self, gid):
        return GoodsDao.query_goods_by_gid(gid)

    def query_goods_by_pid(self, pid):
        if pid:
            goods = GoodsDao.query_goods_by_pid_pin(pid, 0)
            if not goods:
                goods = GoodsDao.query_goods_by_pid_pin(pid, 1)
            if goods:
                g_dict = Goods.to_dict(goods, ['gid'])
                g_dict['gid'] = obfuscate_id(goods.gid)
                return g_dict
        return {}

    def query_product_list_by_ref(self, ref_id, org_id, pin, page, size, is_single):
        offset = (page - 1) * size
        return GoodsDao.query_product_dict_list(ref_id, org_id, pin, offset, size, is_single)

    def query_product(self, pid):
        return GoodsDao.query_product_dict(pid)

    def query_spu_by_pid(self, pid, cid):
        return GoodsDao.query_spu_by_pid_cid(pid, cid)

    def query_category(self):
        ms = GoodsDao.query_category()
        rs = []
        print("query category ms:", ms)
        for category in ms:
            rs.append(Category.to_dict(category))

        return rs

    def query_sub_category(self, cid, lvl):
        rs = []
        category_list = GoodsDao.query_sub_category(cid, lvl)
        for c in category_list:
            cc = c.cc
            c_dict = Category.to_dict(c)
            # cc_dict = CateCate.to_dict(cc)
            c_dict['lvl'] = cc.lvl
            rs.append(c_dict)
        return rs

    def query_spu(self, cid):
        return GoodsDao.query_spu(cid)

    def query_imgs(self, pid):
        return GoodsDao.query_imgs(pid)

    # update
    def del_product_img(self, pid, url):
        GoodsDao.del_product_img(pid, url)

    def update_img(self, pid, url, istop, cmd, ref_id, basepath):
        old_pi = GoodsDao.query_product_img_by_pid_url(pid, url)
        print("update_img pid:", pid, ",url:", url)
        if "del" == cmd:
            upload_path = os.path.join(basepath, 'static', 'files', str(ref_id), str(pid))  # 文件的暂存路径
            upload_thumb_path = os.path.join(upload_path, 's')
            file_path = os.path.join(upload_path, url)
            if os.path.exists(file_path):
                os.remove(file_path)

            s_img_url = None

            if old_pi:
                s_img_url = old_pi.simgurl
                GoodsDao.del_product_img(pid, url)
            if s_img_url:
                thumb_file_path = os.path.join(upload_thumb_path, s_img_url)
                if os.path.exists(thumb_file_path):
                    os.remove(thumb_file_path)
        else:
            if old_pi and old_pi.pin != istop:
                GoodsDao.update_product_img(pid, url, {'pin': istop})

    def offgoods(self, gid):
        params = dict(
            undertime=get_now_datetime(),
            pin=1
        )
        return GoodsDao.update_goods_by_gid(gid, params)

    def need_parse_update_fields(self, fileds, obj, params):
        _params = {}
        for f in fileds:
            if f in params:
                v = params[f]
                o_v = getattr(obj, f)
                if v != o_v:
                    _params[f] = v
                    setattr(obj, f, v)
        return _params

    # new
    def new_product(self, name, net_weight, tp_cid, cid, desc, ref_id, spuids, spustructids):
        params = dict(
            name=name,
            netweight=net_weight,
            tpcid=tp_cid,
            cid=cid,
            desc=desc,
            ref_id=ref_id
        )

        old_cp: CourseProduct = GoodsDao.query_product_by_name(name)
        if old_cp:

            _params = self.need_parse_update_fields(CourseProduct.field_names(), old_cp, params)
            if _params:
                GoodsDao.update_product_by_id(old_cp.pid, _params)
            return old_cp
        else:
            pid, cp = GoodsDao.new_product(params, spuids, spustructids)
            return cp

    def new_goods(self, pid, price, ref_id):
        rs = {"status": 0}
        cp_dict = GoodsDao.query_product_dict(pid)
        spus = GoodsDao.query_spu_by_pid_cid(pid, cp_dict['tpcid'])
        goods = GoodsDao.query_goods_by_pid_pin(pid, 0)
        if not goods:
            goods = GoodsDao.query_goods_by_pid_pin(pid, 1)
        if goods:
            if goods.pin == 0:
                rs["status"] = -1
                rs["error"] = "Please taken product{} off the shelves!".format(cp_dict['name'])
                return rs
        params = dict(
            pid=pid,
            price=price,
            pin=0,
            undertime=get_now_datetime(),
            sku=cp_dict['desc'],
            ref_id=ref_id
        )
        ng: Goods = GoodsDao.new_goods(params, spus)
        rs['gid'] = obfuscate_id(ng.gid)
        return rs

    def build_product_img(self, pid, imgurl, idx, istop, ref_id) -> ProductImg:

        product_img_params = dict(
            pid=pid,
            imgurl=imgurl,
            idx=idx,
            ref_id=ref_id,
            pin=istop
        )
        old_pi = GoodsDao.query_product_img_by_pid_url(pid, imgurl)
        if not old_pi:
            old_pi = GoodsDao.new_product_img(product_img_params)
        return old_pi

    def update_product_img(self, pid, url, params):
        GoodsDao.update_product_img(pid, url, params)

goods_service = GoodsService()

