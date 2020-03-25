# -*- coding: utf-8 -*-
"""
Created by susy at 2020/3/6
"""
from dao.models import db, query_wrap_db, Product, OrderItem, Order, Assets, AuthUser
from utils import obfuscate_id, scale_size, decrypt_id, guess_file_type
from peewee import fn, ModelSelect
import time


class ProductDao(object):
    # query
    @classmethod
    @query_wrap_db
    def product_by_pro_no(cls, data_id) -> Product:
        pro_no = obfuscate_id(data_id)
        return Product.select().where(Product.pro_no == pro_no).first()

    @classmethod
    @query_wrap_db
    def query_assets_count_by_ref_id(cls, ref_id, pin=None):
        model_rs: ModelSelect = Assets.select(fn.count(Assets.id).alias('count'))
        if pin is None:
            model_rs = model_rs.where(Assets.ref_id == ref_id)
        else:
            model_rs = model_rs.where(Assets.ref_id == ref_id and Assets.pin == pin)
        # print("query_assets_count_by_ref_id sql:", model_rs)
        if model_rs:
            model_dict = model_rs.dicts()
            if model_dict:
                v = model_dict[0].get('count')
                if v:
                    return v
        return 0

    @classmethod
    @query_wrap_db
    def fetch_assets_by_ref_id_assets_id(cls, ref_id, assets_id):
        return Assets.select().where(Assets.ref_id == ref_id and Assets.id == assets_id).first()

    @classmethod
    @query_wrap_db
    def query_assets_by_ref_id(cls, ref_id, pin=None, offset=0, limit=500):
        model_rs: ModelSelect = Assets.select()
        if pin is None:
            model_rs = model_rs.where(Assets.ref_id == ref_id)
        else:
            model_rs = model_rs.where(Assets.ref_id == ref_id, Assets.pin == pin)
        # print("query_assets_by_ref_id sql:", model_rs)
        return model_rs.offset(offset).limit(limit)


    @classmethod
    def query_assets_by_ref_id_for_tree(cls, ref_id, pin=None, offset=0, limit=500):
        assets_list = cls.query_assets_by_ref_id(ref_id, pin, offset, limit)
        params = []
        assets: Assets = None
        for assets in assets_list:
            data_id = decrypt_id(assets.pro_no)
            has_children = False
            if assets.isdir == 1:
                icon_val = "folder"
                has_children = True
            else:
                f_type = guess_file_type(assets.desc)
                if f_type:
                    icon_val = "jstree-file file-%s" % f_type
            item = {"id": obfuscate_id(data_id), "text": assets.desc,
                    "data": {"path": "#", "server_ctime": 0, "isdir": assets.isdir, "tag": "asset",
                             "_id": obfuscate_id(assets.id)},
                    "children": has_children, "icon": icon_val}
            params.append(item)
        return params


    # update
    @classmethod
    def update_product(cls, data_id, params):
        pro_no = obfuscate_id(data_id)
        _params = {p: params[p] for p in params if p in Product.field_names()}
        with db:
            Product.update(**_params).where(Product.pro_no == pro_no).execute()

    # new data
    @classmethod
    def new_product(cls, data_id, man_user_ref_id, params):
        with db:
            # "pro_no", "isdir", "name", "fs_id", "ref_id", "data_id", "price", "size"
            product: Product = Product(pro_no=obfuscate_id(data_id),
                                       isdir=params['isdir'],
                                       name=params['name'],
                                       fs_id=params['fs_id'],
                                       ref_id=man_user_ref_id,
                                       data_id=data_id,
                                       price=params.get('price', 0),
                                       size=params['size'],
                                       pin=0)
            product.save(force_insert=True)
            return product

    @classmethod
    def new_order_item(cls, product: Product, order: Order):
        with db:
            # "id", "ord_id", "pro_no", "price"
            oi: OrderItem = OrderItem(ord_id=order.id, pro_no=product.pro_no, price=product.price)
            oi.save(force_insert=True)
            return oi

    @classmethod
    def new_order(cls, user_ref_id, total):
        with db:
            oid = int(time.time() * 1000 * 1000)
            # "ord_no", "state", "ref_id", "total"
            o: Order = Order(ord_no=obfuscate_id(oid), ref_id=user_ref_id, total=total)
            o.save(force_insert=True)
            return o

    @classmethod
    def new_assets(cls, isdir, format_size, desc, order: Order, order_item: OrderItem, pro: Product):
        with db:
            # "ord_no", "pro_no", "fs_id", "isdir", "ref_id"
            a: Assets = Assets(ord_no=order.ord_no, pro_no=order_item.pro_no, fs_id=pro.fs_id, isdir=isdir,
                               ref_id=order.ref_id, desc=desc, format_size=format_size, price=order_item.price)
            a.save(force_insert=True)
            return a

    @classmethod
    def new_order_assets(cls, acc_auth: AuthUser, pro: Product):
        with db:
            oid = int(time.time() * 1000 * 1000)
            # "ord_no", "state", "ref_id", "total"
            o: Order = Order(ord_no=obfuscate_id(oid), ref_id=acc_auth.ref_id, total=pro.price)
            o.save(force_insert=True)
            oi: OrderItem = OrderItem(ord_id=o.id, pro_no=pro.pro_no, price=pro.price)
            oi.save(force_insert=True)
            format_size = scale_size(pro.size)
            a: Assets = Assets(ord_no=o.ord_no, pro_no=oi.pro_no, fs_id=pro.fs_id, isdir=pro.isdir,
                               ref_id=o.ref_id, desc=pro.name, format_size=format_size, price=oi.price)
            a.save(force_insert=True)
            return a
