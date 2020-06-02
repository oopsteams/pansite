# -*- coding: utf-8 -*-
"""
Created by susy at 2020/4/29
"""
from dao.models import db, query_wrap_db, Goods, CourseProduct, ProductImg, Org, AuthUser, Category, \
    CateCate, SPUStruct, ProductSpu, OrgOrg
from utils import obfuscate_id
from peewee import fn, ModelSelect, SQL
import json


class GoodsDao(object):

    # query data
    @classmethod
    @query_wrap_db
    def query_goods_by_org(cls, orgid, order_map, offset, n) -> list:
        g = Goods.alias('g')
        cp = CourseProduct.alias('cp')
        cg = Category.alias('cg')
        field_map = {'goods.': 'g.', 'product.': 'cp.', 'category.': 'cg.'}
        _order_fs = {}
        if order_map:
            for f in order_map.keys():
                nf = f
                for fm in field_map.keys():
                    if f.startswith(fm):
                        nf = f.replace(fm, field_map[fm], 1)
                        break
                _order_fs[nf] = order_map[f]

        ms: ModelSelect = g.select(g, cp, cg).join(
            cp, on=(cp.pid == g.pid), attr="product").join(
            cg, on=(cg.cid == cp.cid), attr="category").join(
            AuthUser, on=(g.ref_id == AuthUser.ref_id)).where(
            AuthUser.org_id == orgid, g.pin == 0
        )
        print("_order_fs:", _order_fs)
        order_vals = [cg.cid.asc()]
        for nf in _order_fs:
            if _order_fs[nf].lower() == "asc":
                order_vals.append(SQL(nf).asc())
            else:
                order_vals.append(SQL(nf).desc())
        ms = ms.order_by(*order_vals).offset(offset).limit(n)
        print("queryGoodsByOrg sql:", ms)
        pids = []
        res = []
        catemap = {}
        pidmap = {}
        for goods in ms:
            # goods_dict = Goods.to_dict(goods)
            # res.append(goods_dict)
            fuzzy_pid = obfuscate_id(goods.pid)
            fuzzy_ref_id = obfuscate_id(goods.ref_id)
            fuzzy_gid = obfuscate_id(goods.gid)
            cname = goods.product.category.name
            item = {'gid': fuzzy_gid, 'uid': fuzzy_ref_id, 'pid': fuzzy_pid, 'price': goods.price,
                    'name': goods.product.name, 'ip_rule': goods.product.ip_rule}
            pids.append(goods.pid)
            pidmap[fuzzy_pid] = item
            if cname in catemap:
                catemap[cname]['goods'].append(item)
            else:
                catemap[cname] = {"cname": cname, "goods": [item]}
                res.append(catemap[cname])
        if pids:
            pi_ms: ModelSelect = ProductImg.select().where(ProductImg.pid.in_(pids), ProductImg.pin == 1)
            # pi: ProductImg = None
            print("pi_ms:", pi_ms)
            for pi in pi_ms:
                fuzzy_pid = obfuscate_id(pi.pid)
                item = pidmap[fuzzy_pid]
                item['imgurl'] = pi.imgurl
                item['simgurl'] = pi.simgurl
        return res

    @classmethod
    @query_wrap_db
    def query_goods_by_gid(cls, gid):
        goods: Goods = Goods.select(Goods, CourseProduct, Category).join(
            CourseProduct, on=(CourseProduct.pid == Goods.pid), attr="product").join(
            Category, on=(Category.cid == CourseProduct.cid), attr="category").where(
            Goods.gid == gid, Goods.pin == 0
        ).first()
        if goods:
            goods_dict = Goods.to_dict(goods, ['gid', 'ref_id', 'pid'])
            goods_dict['gid'] = obfuscate_id(goods.gid)
            goods_dict['uid'] = obfuscate_id(goods.ref_id)
            goods_dict['pid'] = obfuscate_id(goods.pid)
            goods_dict['name'] = goods.product.name
            goods_dict['ip_rule'] = goods.product.ip_rule
            goods_dict['netweight'] = goods.product.netweight
            # goods_dict['sugar'] = goods.product.sugar
            goods_dict['cname'] = goods.product.category.name
            goods_dict['imgurls'] = []
            goods_dict['simgurls'] = []
            goods_dict['uids'] = []
            if goods.pid:
                imgs = cls.query_imgs(goods.pid)
                for pi_dict in imgs:
                    fuzzy_uid = pi_dict['uid']
                    goods_dict['imgurls'].append(pi_dict['imgurl'])
                    goods_dict['simgurls'].append(pi_dict['simgurl'])
                    goods_dict['uids'].append(fuzzy_uid)
            return goods_dict
        return {}

    @classmethod
    @query_wrap_db
    def query_goods_by_pid_pin(cls, pid, pin) -> Goods:
        return Goods.select().where(Goods.pid == pid, Goods.pin == pin).first()

    @classmethod
    @query_wrap_db
    def query_product_dict_list(cls, ref_id, org_id, pin, offset, size, is_single=True):
        cp_ms: ModelSelect = CourseProduct.select(CourseProduct, Category).join(
            Category, on=(Category.cid == CourseProduct.cid), attr="category")

        if is_single:
            cp_ms = cp_ms.where(CourseProduct.ref_id == ref_id)
        else:
            oo = OrgOrg.alias()
            au = AuthUser.alias()
            org_arr: ModelSelect = oo.select(oo.org_id).join(
                au, on=(oo.parent == au.org_id)
            ).where(au.ref_id == ref_id).alias("org_arr")
            cp_ms = cp_ms.join(AuthUser, on=(CourseProduct.ref_id == AuthUser.ref_id)).where(
                (AuthUser.org_id == org_id) | (AuthUser.org_id.in_(org_arr)))
        if pin is not None:
            cp_ms = cp_ms.where(CourseProduct.pin == pin)
        cp_ms = cp_ms.offset(offset).limit(size)
        print("query_product_dict_list cp_ms:", cp_ms)
        res = []
        for cp in cp_ms:
            cp_dict = CourseProduct.to_dict(cp, ['pid', 'ref_id'])
            cp_dict['pid'] = obfuscate_id(cp.pid)
            cp_dict['ref_id'] = obfuscate_id(cp.ref_id)
            cp_dict['cname'] = cp.category.name
            res.append(cp_dict)
        return res

    @classmethod
    @query_wrap_db
    def query_product_dict(cls, pid):
        cp_dict = None
        cp: CourseProduct = CourseProduct.select(CourseProduct, Category).join(
            Category, on=(Category.cid == CourseProduct.cid), attr="category").where(CourseProduct.pid == pid).first()
        if cp:
            cp_dict = CourseProduct.to_dict(cp, ['pid', 'ref_id'])
            cp_dict['pid'] = obfuscate_id(cp.pid)
            cp_dict['ref_id'] = obfuscate_id(cp.ref_id)
            cp_dict['cname'] = cp.category.name
            cc_ms: ModelSelect = CateCate.select().where(CateCate.cid == cp.cid).order_by(CateCate.lvl.asc())
            pcids = []
            for cc in cc_ms:
                pcids.append(cc.pcid)
            cp_dict["cids"] = pcids

        return cp_dict

    @classmethod
    @query_wrap_db
    def query_product_by_name(cls, name):
        return CourseProduct.select().where(CourseProduct.name == name).first()

    @classmethod
    @query_wrap_db
    def query_category(cls):
        return Category.select().where(Category.pin == 2)

    @classmethod
    @query_wrap_db
    def query_spu_by_pid_cid(cls, pid, cid):
        if pid:
            spu_ms: ModelSelect = SPUStruct.select().where(SPUStruct.cid == cid)
            spu: SPUStruct = None
            sql = ""
            for spu in spu_ms:
                if not spu.field:
                    spu.field = ""
                if not spu.desc:
                    spu.desc = ""
                # ProductSpu.select(ProductSpu).join()
                if sql:
                    suffix = "select a.spuid,a.structid,b.name,'{desc}','{field}' from productspu a,{table} b where a.spuid=b.id and a.pid={pid}".format(
                        desc=spu.desc, field=spu.field, table=spu.name, pid=pid
                    )
                    sql = "{sql}{op}{suffix}".format(sql=sql, op=" union ", suffix=suffix)
                    # sql = "%s%s%s" % (sql, """
                    # union
                    # ""","select a.spuid,a.structid,b.name,'%s','%s' from productspu a,%s b where a.spuid=b.id and a.pid=%s" % (
                    #                   spu.desc, spu.field, spu.name, pid))
                else:
                    sql = "select a.spuid,a.structid,b.name,'{desc}','{field}' from productspu a,{table} b where a.spuid=b.id and a.pid={pid}".format(
                        desc=spu.desc, field=spu.field, table=spu.name, pid=pid
                    )
            items = []
            if sql:
                print("sql:", sql)
                result_set = db.execute_sql(sql)
                print("result_set:", result_set)
                for spuid, structid, name, structname, field in result_set:
                    item = {'spuid': spuid, 'name': name, 'structid': structid, 'structname': structname,
                            'field': field}
                    print("result set item:", item)
                    items.append(item)
                    # items.append(
                    #     {'spuid': r.spuid, 'name': r.name, 'structid': r.structid, 'structname': r.structname, 'field': r.field})

            return items
        return []

    @classmethod
    @query_wrap_db
    def query_sub_category(cls, cid, lvl):
        return Category.select(Category, CateCate).join(
            CateCate, on=(CateCate.cid == Category.cid), attr="cc").where(CateCate.pcid == cid, CateCate.lvl == lvl)

    @classmethod
    @query_wrap_db
    def query_spu(cls, cid):
        spu_ms: ModelSelect = SPUStruct.select().where(SPUStruct.cid == cid)

        spu_rs = []
        spu: SPUStruct = None
        for spu in spu_ms:
            items = []
            if spu.field:
                _rs = db.execute_sql("select id,name,min,mmax from {field} order by weight desc".format(field=spu.name))
                for id, name, min, mmax in _rs:
                    items.append([id, name, min, mmax])
                spu_rs.append({"key": spu.desc, "structid": spu.structid, "spu": items, "field": spu.field})
            else:
                _rs = db.execute_sql("select id,name from {field} order by weight desc".format(field=spu.name))
                for id, name in _rs:
                    items.append([id, name])
                spu_rs.append({"key": spu.desc, "structid": spu.structid, "spu": items})
        return spu_rs

    @classmethod
    @query_wrap_db
    def query_imgs(cls, pid):
        pi_ms: ModelSelect = ProductImg.select().where(ProductImg.pid == pid).order_by(ProductImg.idx.asc())
        imgs = []
        for pi in pi_ms:
            pi_dict = ProductImg.to_dict(pi, 'ref_id')
            pi_dict['istop'] = pi.pin
            pi_dict['uid'] = obfuscate_id(pi.ref_id)
            imgs.append(pi_dict)
        return imgs

    @classmethod
    @query_wrap_db
    def query_product_img_by_pid_url(cls, pid, url) -> ProductImg:
        return ProductImg.select().where(ProductImg.pid == pid, ProductImg.imgurl == url).first()

    # update
    @classmethod
    def update_product_by_id(cls, pid, params):
        _params = {p: params[p] for p in params if p in CourseProduct.field_names()}
        with db:
            CourseProduct.update(**_params).where(CourseProduct.pid == pid).execute()

    @classmethod
    def update_goods_by_gid(cls, gid, params):
        _params = {p: params[p] for p in params if p in Goods.field_names()}
        with db:
            Goods.update(**_params).where(Goods.gid == gid).execute()

    @classmethod
    def update_product_img(cls, pid, imgurl, params):
        _params = {p: params[p] for p in params if p in ProductImg.field_names()}
        with db:
            ProductImg.update(**_params).where(ProductImg.pid == pid, ProductImg.imgurl == imgurl).execute()

    @classmethod
    @query_wrap_db
    def del_product_img(cls, pid, img_url):
        with db:
            ProductImg.delete().where(ProductImg.pid == pid, ProductImg.imgurl == img_url).execute()

    # new
    @classmethod
    def new_product(cls, params, spuids, spustructids):
        _params = {p: params[p] for p in params if p in CourseProduct.field_names()}
        cp: CourseProduct = CourseProduct(**_params)
        with db:
            cp.save(force_insert=True)
            if spuids:
                spuidlist = spuids.split(",")
                structidlist = spustructids.split(",")
                # pspus = []
                for i in range(0, len(spuidlist)):
                    struct_id = structidlist[i]
                    spu_id = spuidlist[i]
                    spu_params = dict(
                        structid=struct_id,
                        spuid=spu_id,
                        pid=cp.pid,
                        pin=0,
                        ref_id=cp.ref_id
                    )
                    ProductSpu.insert_many(spu_params).execute()
            return cp.id, cp

    @classmethod
    def new_goods(cls, params, spus):
        _params = {p: params[p] for p in params if p in Goods.field_names()}
        spuarr = []
        if spus:
            for spuitem in spus:
                f = spuitem['field']
                spu_dict = dict(k=spuitem['structname'], v=spuitem['name'], f=f)
                spuarr.append(spu_dict)

        if spuarr:
            _params['spu'] = json.dumps(spuarr, ensure_ascii=False)
        goods: Goods = Goods(**_params)
        with db:
            goods.save(force_insert=True)
            return goods

    @classmethod
    def new_product_img(cls, params):
        _params = {p: params[p] for p in params if p in ProductImg.field_names()}
        pi: ProductImg = ProductImg(**_params)
        with db:
            pi.save(force_insert=True)
            return pi
