# -*- coding: utf-8 -*-
"""
Created by susy at 2020/1/27
"""
from controller.base_service import BaseService
from utils import singleton, make_account_token, obfuscate_id, decrypt_user_id, get_now_datetime
from dao.models import Accounts, Role, Org, BASE_FIELDS
from dao.auth_dao import AuthDao
from utils.constant import FUN_TYPE


@singleton
class AuthService(BaseService):
    max_page_size = 30

    def build_user_payload(self, account: Accounts) -> (str, dict):
        auth_user_dict = AuthDao.auth_user(account.id)
        fuzzy_id = obfuscate_id(account.id)
        auth_user_dict['id'] = fuzzy_id
        print("auth_user_dict:", auth_user_dict)
        tk = make_account_token(auth_user_dict)
        print('make_account_token:', tk)
        return tk, auth_user_dict

    def get_auth_user_role_by_id(self, fuzzy_id):
        user_id = int(decrypt_user_id(fuzzy_id))
        auth_user_dict = AuthDao.auth_user_role_detail(user_id)
        auth_user_dict['fuzzy_id'] = fuzzy_id
        return auth_user_dict

    def get_auth_user_org_by_id(self, fuzzy_id):
        user_id = int(decrypt_user_id(fuzzy_id))
        auth_user_dict = AuthDao.auth_user_org_detail(user_id)
        auth_user_dict['fuzzy_id'] = fuzzy_id
        return auth_user_dict

    def get_auth_user_by_id(self, fuzzy_id):
        user_id = int(decrypt_user_id(fuzzy_id))
        auth_user_dict = AuthDao.auth_user_detail(user_id)
        auth_user_dict['fuzzy_id'] = fuzzy_id
        return auth_user_dict

    def check_fun(self, account: Accounts):
        pass

    def user_list(self, pin, _type, page):
        offset = int(page) * self.max_page_size
        user_dict_list, has_next = AuthDao.account_list(pin, _type, offset, self.max_page_size)
        org_dict_list, has_next = AuthDao.org_list()
        role_dict_list, has_next = AuthDao.role_list()
        rs = {'user_list': user_dict_list, 'org_list': org_dict_list, 'role_list': role_dict_list}
        return rs, has_next

    def org_list(self, page):
        offset = int(page) * self.max_page_size
        org_list, has_next = AuthDao.org_list(offset, self.max_page_size, transfer_to_dict=False)
        org_dict_list = [Org.to_dict(o, BASE_FIELDS) for o in org_list]
        parent_map = {r['id']: r for r in org_dict_list}
        _ids = []
        for o in org_dict_list:
            if o['parent'] in parent_map:
                o['p'] = parent_map[o['parent']]
            else:
                _ids.append(o['parent'])
        if _ids:
            p_list = AuthDao.query_org_list(_ids)
            p = {r['id']: r for r in p_list}
            for o in org_dict_list:
                if o['parent'] in p:
                    o['p'] = p[o['parent']]

        return org_dict_list, has_next

    def fun_list(self, page):
        offset = int(page) * self.max_page_size
        return AuthDao.fun_list(offset, self.max_page_size)

    def role_detail(self, _id):
        r: Role = AuthDao.query_role_list([_id])[0]
        base_fun_list = AuthDao.get_base_funs(r.base_fun)
        r['base_fun_list'] = base_fun_list
        if r.ext_fun:
            ext_codes = r.ext_fun.split(',')
            r['ext_fun_list'] = AuthDao.get_ext_funs(ext_codes)
        if r.parent:
            pr: Role = AuthDao.query_role_list([r.parent])[0]
            r['p'] = pr

    def role_list(self, page):
        offset = int(page) * self.max_page_size
        role_list, has_next = AuthDao.role_list(offset, self.max_page_size, transfer_to_dict=False)

        role_dict_list = [Role.to_dict(r, BASE_FIELDS) for r in role_list]
        parent_ids = {r['id']: r for r in role_dict_list}
        _ids = []
        for r in role_dict_list:
            base_fun_list = AuthDao.get_base_funs(r['base_fun'])
            r['base_fun_list'] = base_fun_list
            if r['ext_fun']:
                ext_codes = r['ext_fun'].split(',')
                r['ext_fun_list'] = AuthDao.get_ext_funs(ext_codes)
            if r['parent'] in parent_ids:
                r['p'] = parent_ids[r['parent']]
            else:
                _ids.append(r['parent'])
        if _ids:
            p_list = AuthDao.query_role_list(_ids)
            p = {r['id']: r for r in p_list}
            for r in role_dict_list:
                if r['parent'] in p:
                    r['p'] = p[r['parent']]
        for r in role_list:
            bind_dict = AuthDao.bind_parent_role_detail(r)
            parent_ids[r.id]['parent_role_detail'] = bind_dict
        return role_dict_list, has_next

    def update_role(self, params):
        rid = 0
        if 'id' in params:
            rid = params['id']
        name = params['name']
        parent_id = params['parent']
        fun_ids = params['fun_ids']
        dp = '/index.html'
        if 'default_path' in params:
            dp = params['default_path']
        base_rs = 0
        ext_codes = []
        if fun_ids:
            fun_list = AuthDao.query_fun_list(fun_ids)

            for f in fun_list:
                if f['type'] == FUN_TYPE['BASE']:
                    base_rs = base_rs | f['code']
                elif f['type'] == FUN_TYPE['EXT']:
                    ext_codes.append(f['code'])
        if rid:
            AuthDao.update_role(rid, {"desc": name, "parent": parent_id, 'base_fun': base_rs,
                                      'ext_fun': ','.join(ext_codes), 'default_path': dp})
        else:
            AuthDao.new_role(name, parent_id, base_rs, ','.join(ext_codes), dp)

    def update_org(self, params):
        oid = 0
        if 'id' in params:
            oid = params['id']
        name = params['name']
        parent = params['parent']
        if oid:
            AuthDao.update_org(oid, {'name': name, 'parent': parent})
        else:
            AuthDao.new_org(name, parent)

    def check_user(self, username, mobile_no):
        return AuthDao.check_user(username, mobile_no)

    def update_user(self, params):
        oid = 0
        if 'fuzzy_id' in params:
            fuzzy_id = params['fuzzy_id']
            oid = decrypt_user_id(fuzzy_id)
        name = params['name']
        nickname = params['nickname']
        mobile_no = params['mobile_no']
        exists_user = self.check_user(name, mobile_no)
        print('exists_user:', exists_user)
        if not oid and exists_user:
            return False
        password = params['password']
        org_id = params['org']
        role_id = params['role']
        extroles = params['extroles']
        extorgs = params['extorgs']
        type = params['type']
        if oid:
            AuthDao.update_account(oid, name, nickname, password, org_id, role_id, type, extorgs, extroles,
                                   get_now_datetime(), lambda account: self.build_user_payload(account))

        else:
            AuthDao.new_account(name, nickname, mobile_no, password, org_id, role_id, type, extorgs, extroles,
                                get_now_datetime(), lambda account: self.build_user_payload(account))
        return True

auth_service = AuthService()
