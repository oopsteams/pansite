# -*- coding: utf-8 -*-
"""
Created by susy at 2020/1/27
"""
from dao.models import query_wrap_db, Accounts, AuthUser, UReference, Fun, Role, RoleExtend, Org, OrgOrg, UserRefExtend, \
    UserRoleExtend, UserOrgExtend, BASE_FIELDS, db
from utils.constant import USER_TYPE, FUN_BASE, FUN_TYPE
from utils import obfuscate_id
from typing import Callable, Tuple


class AuthDao(object):

    # query
    @classmethod
    @query_wrap_db
    def account_list(cls, pin=None, _type=None, offset=0, page_size=30):
        if pin and _type:
            account_list = Accounts.select(Accounts, AuthUser
                                           ).join(AuthUser, on=(Accounts.id == AuthUser.acc_id), attr='auth').where(
                Accounts.pin == pin, AuthUser.type == _type).order_by(Accounts.created_at.desc()).offset(offset).limit(
                page_size)
        elif _type:
            account_list = Accounts.select(Accounts, AuthUser
                                           ).join(AuthUser, on=(Accounts.id == AuthUser.acc_id), attr='auth').where(
                AuthUser.type == _type).order_by(Accounts.created_at.desc()).offset(offset).limit(page_size)
        elif pin:
            account_list = Accounts.select().where(Accounts.pin == pin).order_by(Accounts.created_at.desc()).offset(
                offset).limit(page_size)
        else:
            account_list = Accounts.select(Accounts).order_by(Accounts.created_at.desc()).offset(offset).limit(
                page_size)
        # print("account_list:", account_list)
        rs = []
        n = 0
        acc_ids = []
        for acc in account_list:
            acc_dict = Accounts.to_dict(acc)
            if hasattr(acc, 'auth') and acc.auth:
                auth_user_dict = AuthUser.to_dict(acc.auth, BASE_FIELDS)
                acc_dict['auth'] = auth_user_dict
            else:
                acc_ids.append(acc.id)
            if not acc.fuzzy_id:
                acc_dict['fuzzy_id'] = obfuscate_id(acc.id)
            rs.append(acc_dict)

            n = n + 1
        au_list = AuthUser.select().where(AuthUser.acc_id.in_(acc_ids))
        au_dict = {}
        if au_list:
            for au in au_list:
                au_dict[au.acc_id] = AuthUser.to_dict(au)

        for acc_dict in rs:
            if acc_dict['id'] in au_dict:
                acc_dict['auth'] = au_dict[acc_dict['id']]
            uoe_list = UserOrgExtend.select().where(UserOrgExtend.acc_id == acc_dict['id'])
            if uoe_list:
                acc_dict['extorgs'] = [uoe.org_id for uoe in uoe_list]
            ure_list = UserRoleExtend.select().where(UserRoleExtend.acc_id == acc_dict['id'])
            if ure_list:
                acc_dict['extroles'] = [ure.role_id for ure in ure_list]
            acc_dict.pop('id')
        return rs, n == page_size

    @classmethod
    @query_wrap_db
    def org_list(cls, offset=0, page_size=30, transfer_to_dict=True):
        org_list = Org.select().offset(offset).limit(page_size)
        rs = []
        n = 0
        for obj in org_list:
            if transfer_to_dict:
                obj_dict = Org.to_dict(obj)
            else:
                obj_dict = obj
            rs.append(obj_dict)
            n = n + 1
        return rs, n == page_size

    @classmethod
    @query_wrap_db
    def fun_list(cls, offset=0, page_size=30):
        data_list = Fun.select().where(Fun.pin >= 0).offset(offset).limit(page_size)
        rs = []
        n = 0
        for obj in data_list:
            obj_dict = Fun.to_dict(obj, BASE_FIELDS)
            rs.append(obj_dict)
            n = n + 1
        return rs, n == page_size

    @classmethod
    @query_wrap_db
    def role_list(cls, offset=0, page_size=30, transfer_to_dict=True):
        data_list = Role.select().offset(offset).limit(page_size)
        rs = []
        n = 0
        for obj in data_list:
            if transfer_to_dict:
                obj_dict = Role.to_dict(obj, BASE_FIELDS)
            else:
                obj_dict = obj
            rs.append(obj_dict)
            n = n + 1
        return rs, n == page_size

    @classmethod
    @query_wrap_db
    def query_role_list(cls, ids):
        data_list = Role.select().where(Role.id.in_(ids))
        rs = []
        for obj in data_list:
            obj_dict = Role.to_dict(obj, BASE_FIELDS)
            rs.append(obj_dict)
        return rs

    @classmethod
    @query_wrap_db
    def query_org_list(cls, ids):
        data_list = Org.select().where(Org.id.in_(ids))
        rs = []
        for obj in data_list:
            obj_dict = Org.to_dict(obj, BASE_FIELDS)
            rs.append(obj_dict)
        return rs

    @classmethod
    @query_wrap_db
    def query_fun_list(cls, ids):
        data_list = Fun.select().where(Fun.id.in_(ids))
        rs = []
        for obj in data_list:
            obj_dict = Fun.to_dict(obj, BASE_FIELDS)
            rs.append(obj_dict)
        return rs

    @classmethod
    @query_wrap_db
    def auth_user_role_detail(cls, account_id) -> dict:
        acc: Accounts = Accounts.select(Accounts).where(Accounts.id == account_id).first()
        rs = AuthUser.select().where(AuthUser.acc_id == account_id)
        auth_user_dict = {'acc': Accounts.to_dict(acc, BASE_FIELDS + ["id", "password", "fuzzy_id", "login_token",
                                                                      "login_updated_at", "pin"])}
        if rs:
            au: AuthUser = rs[0]
            auth_user_dict['au'] = {'oid': au.org_id, 'rfid': au.ref_id, 'rid': au.role_id, 't': au.type}
            auth_user_dict['role'] = cls._get_roles(au)
            role_list = []
            role_obj_list = Role.select()
            for r in role_obj_list:
                role_list.append(Role.to_dict(r, BASE_FIELDS))
            auth_user_dict['roles'] = role_list

        return auth_user_dict

    @classmethod
    @query_wrap_db
    def bind_parent_role_detail(cls, r: Role):
        ext_parent_role = {}
        if r.parent:
            role_extends_list = RoleExtend.select(RoleExtend).where(RoleExtend.role_id == r.id)
            ext_role_ids = []
            if role_extends_list:
                role_extend: RoleExtend = None
                for role_extend in role_extends_list:
                    ext_role_ids.append(role_extend.parent)
                role_list = Role.select().where(Role.id.in_(ext_role_ids))
                ext_base_rs = 0
                ext_ext_fun_list = []
                for role in role_list:
                    if role.ext_fun and role.ext_fun not in ext_ext_fun_list:
                        ext_codes = role.ext_fun.split(',')
                        ext_ext_fun_list = ext_ext_fun_list + ext_codes
                    ext_base_rs = ext_base_rs | role.base_fun
                # 解析为可读 功能点
                ext_parent_role['base'] = cls._get_base_funs(ext_base_rs)
                ext_parent_role['ext'] = cls._get_ext_funs(ext_ext_fun_list)

        return ext_parent_role

    @classmethod
    @query_wrap_db
    def auth_user_org_detail(cls, account_id) -> dict:
        acc: Accounts = Accounts.select(Accounts).where(Accounts.id == account_id).first()
        rs = AuthUser.select().where(AuthUser.acc_id == account_id)
        auth_user_dict = {'acc': Accounts.to_dict(acc, BASE_FIELDS + ["id", "password", "fuzzy_id", "login_token",
                                                                      "login_updated_at", "pin"])}
        if rs:
            au: AuthUser = rs[0]
            org: Org = Org.select().where(Org.id == au.org_id).first()
            auth_user_dict['org'] = {'base': Org.to_dict(org, BASE_FIELDS), 'parent': {'id': 0, 'name': '无'}}
            if org.parent:
                porg: Org = Org.select().where(Org.id == org.parent).first()
                auth_user_dict['org']['parent'] = porg
            ext_org_list = Org.select(Org).join(UserOrgExtend, on=(UserOrgExtend.org_id == Org.id)).where(
                UserOrgExtend.acc_id == au.acc_id)
            if ext_org_list:
                ext_org = auth_user_dict['org']['ext'] = []
                for org in ext_org_list:
                    ext_org.append(Org.to_dict(org, BASE_FIELDS))
            org_list = []
            org_obj_list = Org.select()
            for o in org_obj_list:
                org_list.append(Org.to_dict(o, BASE_FIELDS))
            auth_user_dict['orgs'] = org_list

        return auth_user_dict

    @classmethod
    @query_wrap_db
    def auth_user_detail(cls, account_id) -> dict:
        acc: Accounts = Accounts.select(Accounts).where(Accounts.id == account_id).first()
        rs = AuthUser.select().where(AuthUser.acc_id == account_id)
        auth_user_dict = {'acc': Accounts.to_dict(acc, BASE_FIELDS + ["id", "password", "fuzzy_id", "login_token", "login_updated_at", "pin"])}
        if rs:
            au: AuthUser = rs[0]
            org: Org = Org.select().where(Org.id == au.org_id).first()
            auth_user_dict['org'] = {'base': Org.to_dict(org, BASE_FIELDS), 'parent': {'id': 0, 'name': '无'}}
            if org.parent:
                porg: Org = Org.select().where(Org.id == org.parent).first()
                auth_user_dict['org']['parent'] = porg
            ext_org_list = Org.select(Org).join(UserOrgExtend, on=(UserOrgExtend.org_id == Org.id)).where(UserOrgExtend.acc_id == au.acc_id)
            if ext_org_list:
                ext_org = auth_user_dict['org']['ext'] = []
                for org in ext_org_list:
                    ext_org.append(Org.to_dict(org, BASE_FIELDS))
            auth_user_dict['au'] = {'oid': au.org_id, 'rfid': au.ref_id, 'rid': au.role_id, 't': au.type}
            auth_user_dict['role'] = cls._get_roles(au)

        return auth_user_dict

    @classmethod
    @query_wrap_db
    def auth_user(cls, account_id) -> dict:
        rs = AuthUser.select().where(AuthUser.acc_id == account_id)
        auth_user_dict = {}
        if rs:
            au: AuthUser = rs[0]
            # au_dict = AuthUser.to_dict(au, ['created_at', 'updated_at', 'acc_id', 'type'])
            auth_user_dict['au'] = {'oid': au.org_id, 'rfid': au.ref_id, 'rid': au.role_id}
            auth_user_ext = {}
            base_fun, ext_fun_list, default_path_list = cls._get_fun_codes(au)
            auth_user_ext['p'] = default_path_list
            auth_user_ext['bf'] = base_fun
            auth_user_ext['ef'] = ext_fun_list
            auth_user_ext['t'] = au.type
            if au.type == USER_TYPE['GROUP']:
                origin_org_ids, org_ids = cls._get_org_ids(au)
                auth_user_ext['oog'] = origin_org_ids
                auth_user_ext['og'] = org_ids
            auth_user_dict['ext'] = auth_user_ext
        return auth_user_dict

    @classmethod
    @query_wrap_db
    def _get_org_ids(cls, au: AuthUser):
        org_ids = []
        origin_org_ids = [au.org_id]
        ext_org_list = UserOrgExtend.select().where(UserOrgExtend.acc_id == au.acc_id)
        if ext_org_list and len(ext_org_list) > 0:
            ext_org: UserOrgExtend = None
            for ext_org in ext_org_list:
                origin_org_ids.append(ext_org.org_id)
            oos = OrgOrg.select().where(OrgOrg.parent.in_(origin_org_ids))
            if oos and len(oos) > 0:
                oo: OrgOrg = None
                for oo in oos:
                    org_ids.append(oo.org_id)
        return origin_org_ids, org_ids

    @classmethod
    @query_wrap_db
    def _get_org_detail(cls, au: AuthUser):
        rs = {}
        org_ids = []
        origin_org_ids = [au.org_id]
        oos = OrgOrg.select().where(OrgOrg.parent.in_(origin_org_ids))

    @classmethod
    @query_wrap_db
    def get_base_funs(cls, base_val):
        return cls._get_base_funs(base_val)

    @classmethod
    def _get_base_funs(cls, base_val):
        base_fun_codes = []
        rs = []
        if (base_val & FUN_BASE['QUERY']) == FUN_BASE['QUERY']:
            base_fun_codes.append(FUN_BASE['QUERY'])
        if (base_val & FUN_BASE['NEW']) == FUN_BASE['NEW']:
            base_fun_codes.append(FUN_BASE['NEW'])
        if (base_val & FUN_BASE['UPDATE']) == FUN_BASE['UPDATE']:
            base_fun_codes.append(FUN_BASE['UPDATE'])
        if (base_val & FUN_BASE['DEL']) == FUN_BASE['DEL']:
            base_fun_codes.append(FUN_BASE['DEL'])
        if (base_val & FUN_BASE['MENU']) == FUN_BASE['MENU']:
            base_fun_codes.append(FUN_BASE['MENU'])
        if base_fun_codes:
            fun_list = Fun.select().where(Fun.code.in_(base_fun_codes))
            fun: Fun = None
            for fun in fun_list:
                rs.append(Fun.to_dict(fun, BASE_FIELDS))
        return rs

    @classmethod
    def get_ext_funs(cls, ext_codes):
        return cls._get_ext_funs(ext_codes)

    @classmethod
    @query_wrap_db
    def _get_ext_funs(cls, ext_codes):
        rs = []
        ext_codes = [int(ec) for ec in ext_codes]
        if ext_codes:
            fun_list = Fun.select().where(Fun.code.in_(ext_codes))
            fun: Fun = None
            for fun in fun_list:
                rs.append(Fun.to_dict(fun, BASE_FIELDS))
        return rs

    @classmethod
    @query_wrap_db
    def _get_roles(cls, au: AuthUser):
        rs = {}
        role_ids = []
        origin_role_ids = [au.role_id]
        role_extends_list = RoleExtend.select().where(RoleExtend.role_id.in_(origin_role_ids))
        if role_extends_list:
            rs['base'] = role_extends_list[0]
            role_extend: RoleExtend = None
            for role_extend in role_extends_list:
                role_ids.append(role_extend.parent)
        role_list = Role.select().where(Role.id.in_(origin_role_ids + role_ids))
        base_rs = 0
        ext_fun_list = []
        default_path_list = []
        role: Role = None
        base_role = {'roles': []}
        rs['base'] = base_role
        for role in role_list:
            if role.id in origin_role_ids:
                base_role['roles'].append(Role.to_dict(role, ['created_at', 'updated_at', 'parent']))
                default_path_list.append(role.default_path)
            if role.ext_fun and role.ext_fun not in ext_fun_list:
                ext_codes = role.ext_fun.split(',')
                ext_fun_list = ext_fun_list + ext_codes
            base_rs = base_rs | role.base_fun
        # 解析为可读 功能点
        base_role['fun'] = fun_dict = {}
        fun_dict['base'] = cls._get_base_funs(base_rs)
        fun_dict['ext'] = cls._get_ext_funs(ext_fun_list)
        fun_dict['paths'] = default_path_list
        role_extends_list = RoleExtend.select(RoleExtend).join(UserRoleExtend,
                                                               on=(UserRoleExtend.role_id == RoleExtend.role_id)).where(
            UserRoleExtend.acc_id == au.acc_id)
        ext_origin_role_ids = []
        ext_role_ids = []
        if role_extends_list:
            role_extend: RoleExtend = None
            for role_extend in role_extends_list:
                ext_role_ids.append(role_extend.parent)
                if role_extend.role_id not in ext_origin_role_ids:
                    ext_origin_role_ids.append(role_extend.role_id)
            role_list = Role.select().where(Role.id.in_(ext_origin_role_ids + ext_role_ids))
            ext_base_rs = 0
            ext_ext_fun_list = []
            ext_default_path_list = []
            ext_role = {'roles': []}
            rs['ext'] = ext_role

            for role in role_list:
                if role.id in ext_origin_role_ids:
                    ext_role['roles'].append(Role.to_dict(role, ['created_at', 'updated_at', 'parent']))
                    ext_default_path_list.append(role.default_path)
                if role.ext_fun and role.ext_fun not in ext_ext_fun_list:
                    ext_codes = role.ext_fun.split(',')
                    ext_ext_fun_list = ext_ext_fun_list + ext_codes
                ext_base_rs = ext_base_rs | role.base_fun
            # 解析为可读 功能点
            ext_role['fun'] = fun_dict = {}
            fun_dict['base'] = cls._get_base_funs(ext_base_rs)
            fun_dict['ext'] = cls._get_ext_funs(ext_ext_fun_list)
            fun_dict['paths'] = ext_default_path_list
        return rs

    @classmethod
    @query_wrap_db
    def _get_fun_codes(cls, au: AuthUser):
        role_ids = []
        origin_role_ids = [au.role_id]
        ext_role_list = UserRoleExtend.select().where(UserRoleExtend.acc_id == au.acc_id)
        if ext_role_list:
            ext_role: UserRoleExtend = None
            for ext_role in ext_role_list:
                origin_role_ids.append(ext_role.role_id)
            role_extends_list = RoleExtend.select().where(RoleExtend.role_id.in_(origin_role_ids))
            if role_extends_list:
                role_extend: RoleExtend = None
                for role_extend in role_extends_list:
                    role_ids.append(role_extend.parent)
        role_list = Role.select().where(Role.id.in_(origin_role_ids+role_ids))
        role: Role = None
        base_rs = 0
        ext_fun_list = []
        default_path_list = []
        for role in role_list:
            if role.id in origin_role_ids:
                default_path_list.append(role.default_path)
            if role.ext_fun and role.ext_fun not in ext_fun_list:
                ext_fun_list.append(role.ext_fun)
            base_rs = base_rs | role.base_fun
        return base_rs, ext_fun_list, default_path_list

    @classmethod
    @query_wrap_db
    def check_user(cls, username, mobile_no):
        return Accounts.select().where((Accounts.name == username) | (Accounts.mobile_no == mobile_no)).exists()

    # update
    @classmethod
    def update_role(cls, role_id, params):
        _params = {p: params[p] for p in params if p in Role.field_names()}

        with db:

            if 'parent' in params and params['parent']:
                r: Role = Role.select().where(Role.id == role_id).first()
                if r.parent != params['parent']:
                    RoleExtend.delete().where(RoleExtend.role_id == role_id)
                    re: RoleExtend = RoleExtend(role_id=role_id, parent=params['parent'])
                    re.save(force_insert=True)
                    re_list = RoleExtend.select().where(RoleExtend.role_id == params['parent'])
                    for re in re_list:
                        RoleExtend(role_id=role_id, parent=re.parent).save(force_insert=True)
            Role.update(**_params).where(Role.id == role_id).execute()

    @classmethod
    def new_role(cls, name, parent, base_fun, ext_fun, default_path):
        data_item = Role(desc=name, parent=parent, base_fun=base_fun, ext_fun=ext_fun, default_path=default_path)
        with db:
            data_item.save(force_insert=True)
            if parent and data_item.id:
                re: RoleExtend = RoleExtend(role_id=data_item.id, parent=parent)
                re.save(force_insert=True)
                re_list = RoleExtend.select().where(RoleExtend.role_id == parent)
                for re in re_list:
                    RoleExtend(role_id=data_item.id, parent=re.parent).save(force_insert=True)
            return data_item.id

    @classmethod
    def new_org(cls, name, parent):
        data_item = Org(name=name, parent=parent)
        with db:
            data_item.save(force_insert=True)
            if parent and data_item.id:
                oo: OrgOrg = OrgOrg(org_id=data_item.id, parent=parent)
                oo.save(force_insert=True)
                oo_list = OrgOrg.select().where(OrgOrg.org_id == parent)
                for oo in oo_list:
                    OrgOrg(org_id=data_item.id, parent=oo.parent).save(force_insert=True)
            return data_item.id

    @classmethod
    def update_org(cls, org_id, params):
        _params = {p: params[p] for p in params if p in Role.field_names()}
        with db:
            if 'parent' in params and params['parent']:
                o: Org = Org.select().where(Org.id == org_id).first()
                if o.parent != params['parent']:
                    OrgOrg.delete().where(OrgOrg.org_id == org_id)
                    oo: OrgOrg = OrgOrg(org_id=org_id, parent=params['parent'])
                    oo.save(force_insert=True)
                    oo_list = OrgOrg.select().where(OrgOrg.org_id == params['parent'])
                    for oo in oo_list:
                        OrgOrg(org_id=org_id, parent=oo.parent).save(force_insert=True)
            Org.update(**_params).where(Org.id == org_id).execute()

    @classmethod
    def new_account(cls, name, nickname, mobile_no, password, org_id, role_id, _type, extorgs, extroles, now,
                    envelop_user_lambda: Callable[..., Tuple[str, dict]]=None):
        with db:
            user_token = None
            user_ext_dict = {}
            acc: Accounts = Accounts(name=name, mobile_no=mobile_no, nickname=nickname, password=password)
            acc.save(force_insert=True)
            acc_id = acc.id
            ur: UReference = UReference()
            ur.save(force_insert=True)
            au: AuthUser = AuthUser(acc_id=acc_id, org_id=org_id, role_id=role_id, ref_id=ur.id, type=_type)
            au.save(force_insert=True)
            if extorgs:
                for oid in extorgs:
                    UserOrgExtend(acc_id=acc_id, org_id=oid).save(force_insert=True)
            if extroles:
                for rid in extroles:
                    UserRoleExtend(acc_id=acc_id, role_id=rid).save(force_insert=True)
            if envelop_user_lambda:
                user_token, user_ext_dict = envelop_user_lambda(acc)

                cls.update_account_by_pk(pk_id=acc_id, params={"fuzzy_id": user_ext_dict['id'], "login_updated_at": now,
                                                               "login_token": user_token})
            return user_token, user_ext_dict

    @classmethod
    def update_account_by_pk(cls, pk_id, params):
        """
        :param pk_id:
        :param params:
        :return:
        """
        _params = {p: params[p] for p in params if p in Accounts.field_names()}
        with db:
            Accounts.update(**params).where(Accounts.id == pk_id).execute()

    @classmethod
    def update_account(cls, acc_id, name, nickname, password, org_id, role_id, _type, extorgs, extroles, now,
                       envelop_user_lambda: Callable[..., Tuple[str, dict]]):
        with db:
            update_params = dict(
                name=name, nickname=nickname, login_updated_at=now
            )
            if password:
                update_params['password'] = password
            user_token = None
            user_ext_dict = {}
            au_params = {}
            au: AuthUser = AuthUser.select().where(AuthUser.acc_id == acc_id).first()
            if not au:
                ur: UReference = UReference()
                ur.save(force_insert=True)
                au = AuthUser(acc_id=acc_id, org_id=org_id, role_id=role_id, ref_id=ur.id, type=_type)
                au.save(force_insert=True)
            if au.role_id != role_id:
                au_params['role_id'] = role_id
            if au.org_id != org_id:
                au_params['org_id'] = org_id
            if au.type != _type:
                au_params['type'] = _type
            if au_params:
                AuthUser.update(**au_params).where(AuthUser.acc_id == acc_id).execute()

            if extorgs:
                uoe_list = UserOrgExtend.select().where(UserOrgExtend.acc_id == acc_id,
                                                        UserOrgExtend.org_id.not_in(extorgs))
                del_uoe_ids = [uoe.org_id for uoe in uoe_list]
                if del_uoe_ids:
                    UserOrgExtend.delete().where(UserOrgExtend.acc_id == acc_id, UserOrgExtend.org_id.in_(del_uoe_ids))
                exc_uoe_list = UserOrgExtend.select().where(UserOrgExtend.acc_id == acc_id,
                                                            UserOrgExtend.org_id.in_(extorgs))
                exc_ext_org_ids = [uoe.org_id for uoe in exc_uoe_list]
                insert_ext_org_ids = extorgs
                if exc_ext_org_ids:
                    insert_ext_org_ids = [oid for oid in extorgs if oid not in exc_ext_org_ids]
                for oid in insert_ext_org_ids:
                    UserOrgExtend(acc_id=acc_id, org_id=oid).save(force_insert=True)
            if extroles:
                ure_list = UserRoleExtend.select().where(UserRoleExtend.acc_id == acc_id,
                                                         UserRoleExtend.role_id.not_in(extroles))
                del_ure_ids = [ure.role_id for ure in ure_list]
                if del_ure_ids:
                    UserRoleExtend.delete().where(UserRoleExtend.acc_id == acc_id,
                                                  UserRoleExtend.role_id.in_(del_ure_ids))
                exc_ure_list = UserOrgExtend.select().where(UserOrgExtend.acc_id == acc_id,
                                                            UserOrgExtend.org_id.in_(extorgs))
                exc_ext_role_ids = [ure.role_id for ure in exc_ure_list]
                insert_ext_role_ids = extroles
                if exc_ext_role_ids:
                    insert_ext_role_ids = [rid for rid in extroles if rid not in exc_ext_role_ids]
                for rid in insert_ext_role_ids:
                    UserRoleExtend(acc_id=acc_id, role_id=rid).save(force_insert=True)
            if envelop_user_lambda:
                acc: Accounts = Accounts.select().where(Accounts.id == acc_id).first()
                user_token, user_ext_dict = envelop_user_lambda(acc)
                update_params['fuzzy_id'] = user_ext_dict['id']
                update_params['login_token'] = user_token
            Accounts.update(**update_params).where(Accounts.id == acc_id).execute()
            return user_token, user_ext_dict
