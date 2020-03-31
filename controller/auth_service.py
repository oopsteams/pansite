# -*- coding: utf-8 -*-
"""
Created by susy at 2020/1/27
"""
from controller.base_service import BaseService
from utils import singleton, make_account_token, obfuscate_id, decrypt_user_id, get_now_datetime
from dao.models import Accounts, Role, Org, BASE_FIELDS, PanAccounts, AccountExt
from dao.auth_dao import AuthDao
from dao.dao import DataDao
from utils.constant import FUN_TYPE, USER_TYPE, PAN_ACCESS_TOKEN_TIMEOUT, LOGIN_TOKEN_TIMEOUT
from utils.caches import cache_data
from utils import compare_dt_by_now, log, restapi, get_now_ts, get_payload_from_token
from cfg import NEW_USER_DEFAULT, PAN_SERVICE, get_bd_auth_uri
import time
import arrow
PAN_ACC_CACHE_TIMEOUT = 24 * 60 * 60
ACCOUNT_PAN_ACC_CACHE_CNT = 5


@singleton
class AuthService(BaseService):
    max_page_size = 30
    client_id = PAN_SERVICE['client_id']
    client_secret = PAN_SERVICE['client_secret']
    pan_auth = get_bd_auth_uri()

    @cache_data("pan_acc_{1}_%s" % ACCOUNT_PAN_ACC_CACHE_CNT, timeout_seconds=PAN_ACC_CACHE_TIMEOUT)
    def checkout_pan_accounts(self, account_id=0):
        pan_acc_list = DataDao.pan_account_list(account_id, ACCOUNT_PAN_ACC_CACHE_CNT)
        return {pan_acc.id: pan_acc for pan_acc in pan_acc_list}

    def get_pan_account(self, pan_account_id, account_id) -> PanAccounts:
        pan_acc_cache = self.checkout_pan_accounts(account_id)
        if pan_account_id in pan_acc_cache:
            return pan_acc_cache[pan_account_id]
        return DataDao.pan_account_by_id(pan_account_id)

    def default_pan_account(self, account_id) -> PanAccounts:
        pan_acc_cache = auth_service.checkout_pan_accounts(account_id)
        for pan_account_id in pan_acc_cache:
            pan_acc = pan_acc_cache[pan_account_id]
            if pan_acc.pin == 1:
                return pan_acc
        return None

    def check_pan_token_validation(self, pan_acc: PanAccounts):
        if compare_dt_by_now(pan_acc.expires_at) <= 0:
            new_pan = self.fresh_token(pan_acc.id)
            if new_pan:
                pan_acc.access_token = new_pan.access_token
                pan_acc.refresh_token = new_pan.refresh_token
                pan_acc.expires_at = new_pan.expires_at
                pan_acc.token_updated_at = new_pan.token_updated_at
        return pan_acc

    def build_user_payload(self, account: Accounts) -> (str, dict):
        auth_user_dict = AuthDao.auth_user(account.id)
        fuzzy_id = obfuscate_id(account.id)
        auth_user_dict['id'] = fuzzy_id
        pan_acc_cache = self.checkout_pan_accounts(account.id)
        for pan_account_id in pan_acc_cache:
            pan_acc = pan_acc_cache[pan_account_id]
            if pan_acc.pin == 1:
                auth_user_dict['_p'] = obfuscate_id(pan_account_id)
                break
        log.info("auth_user_dict:{}".format(auth_user_dict))
        tk = make_account_token(auth_user_dict)
        log.info('make_account_token:'.format(tk))
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
        # print('exists_user:', exists_user)
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

    def login_check_user(self, acc: Accounts):
        need_renew_pan_acc = []
        if acc:
            pan_acc_list = DataDao.pan_account_list(acc.id)
            # pan_acc: PanAccounts = DataDao.pan_account_list(acc.id)
            need_renew_access_token = False
            l = len(pan_acc_list)
            for pan_acc in pan_acc_list:
                if pan_acc.client_id != self.client_id or pan_acc.client_secret != self.client_secret:
                    need_renew_access_token = True
                    need_renew_pan_acc.append({"id": pan_acc.id, "name": pan_acc.name, "use_cnt": pan_acc.use_count,
                                               "refresh": False, 'auth': self.pan_auth})
                elif pan_acc.access_token and pan_acc.token_updated_at:
                    tud = arrow.get(pan_acc.token_updated_at).replace(tzinfo=self.default_tz)
                    if (arrow.now(self.default_tz) - tud).total_seconds() > PAN_ACCESS_TOKEN_TIMEOUT:
                        need_renew_access_token = True
                        need_renew_pan_acc.append({"id": pan_acc.id, "name": pan_acc.name, "use_cnt": pan_acc.use_count,
                                                   "refresh": True, 'auth': self.pan_auth})
                else:
                    need_renew_access_token = True
                    need_renew_pan_acc.append({"id": pan_acc.id, "name": pan_acc.name, "use_cnt": pan_acc.use_count,
                                               "refresh": True, 'auth': self.pan_auth})
            if l == 0:
                need_renew_access_token = True
            # if pan_acc and pan_acc['access_token'] and pan_acc['token_updated_at']:
            #     tud = arrow.get(pan_acc['token_updated_at']).replace(tzinfo=self.default_tz)
            #     if (arrow.now(self.default_tz) - tud).total_seconds() < PAN_ACCESS_TOKEN_TIMEOUT:
            #         need_renew_access_token = False

            lud = arrow.get(acc.login_updated_at).replace(tzinfo=self.default_tz)
            diff = arrow.now(self.default_tz) - lud
            params = {}
            if diff.total_seconds() > LOGIN_TOKEN_TIMEOUT or not acc.login_token:
                if not acc.fuzzy_id:
                    acc.fuzzy_id = obfuscate_id(acc.id)
                    params["fuzzy_id"] = acc.fuzzy_id
                # login_token = make_token(acc.fuzzy_id)
                login_token, _ = auth_service.build_user_payload(acc)
                acc.login_token = login_token
                params["login_token"] = login_token
                lud = params["login_updated_at"] = get_now_datetime()
                DataDao.update_account_by_pk(acc.id, params=params)
            else:
                tk = acc.login_token
                if tk:
                    user_payload = get_payload_from_token(tk)
                    if user_payload:
                        tm = user_payload['tm']
                        ctm = get_now_ts()
                        if ctm - tm > LOGIN_TOKEN_TIMEOUT:
                            # login_token = make_token(acc.fuzzy_id)
                            login_token, _ = auth_service.build_user_payload(acc)
                            acc.login_token = login_token
                            params["login_token"] = login_token
                            lud = params["login_updated_at"] = get_now_datetime()
                            DataDao.update_account_by_pk(acc.id, params=params)
            log.debug("login_token:{}".format(acc.login_token))
            result = {"need_renew_access_token": need_renew_access_token}
            if need_renew_access_token:
                result['auth'] = self.pan_auth
            result['token'] = acc.login_token
            result['login_at'] = int(arrow.get(lud).timestamp * 1000)
            # print('login_at:', result['login_at'])
            result['pan_acc_list'] = need_renew_pan_acc
            account_ext = DataDao.account_ext_by_acc_id(acc.id)
            result['username'] = account_ext.username
            result['portrait'] = account_ext.portrait
            result['id'] = acc.fuzzy_id
            return result

        return None

    def _default_new_user_build_user_payload(self, account: Accounts, params):
        auth_user_dict = AuthDao.auth_user(account.id)
        fuzzy_id = obfuscate_id(account.id)
        auth_user_dict['id'] = fuzzy_id
        auth_user_dict['_id'] = account.id
        auth_user_dict['login_updated_at'] = account.login_updated_at

        access_token = params.get('access_token')
        refresh_token = params.get('refresh_token')
        expires_at = params.get('expires_at')

        account_ext_ctx = params.get('accext', {})

        client_id = PAN_SERVICE['client_id']
        client_secret = PAN_SERVICE['client_secret']
        account_ext_ctx['account_id'] = account.id
        account_ext_ctx['username'] = account.name
        log.info("will new account ext:{}".format(account_ext_ctx))
        acc_ext: AccountExt = DataDao.new_accounts_ext(**account_ext_ctx)
        log.info("new account ext ok acc_ext id:{}".format(acc_ext.id))
        pan_acc_id = DataDao.new_pan_account(account.id, account.name, client_id, client_secret,
                                             access_token, refresh_token, expires_at, get_now_datetime(), pin=1, bd_uid=acc_ext.user_id)
        auth_user_dict['_p'] = obfuscate_id(pan_acc_id)
        # print("auth_user_dict:", auth_user_dict)
        tk = make_account_token(auth_user_dict)
        # print('make_account_token:', tk)
        return tk, auth_user_dict

    def _new_user(self, name, password, nickname, access_token, refresh_token, expires_at, context):
        mobile_no = ''
        origin_name = name
        exists_user = AuthDao.check_user_only_by_name(name)
        dog = 20
        while dog > 0 and exists_user:
            name = "{}_{}".format(origin_name, str(int(time.time()))[-4:])
            exists_user = AuthDao.check_user_only_by_name(name)
            time.sleep(1)
            dog = dog - 1
        org_id = NEW_USER_DEFAULT['org_id']
        role_id = NEW_USER_DEFAULT['role_id']
        extroles = []
        extorgs = []
        type = USER_TYPE['SINGLE']
        user_token, user_ext_dict = AuthDao.new_account(name, nickname, mobile_no, password, org_id, role_id, type,
                                                        extorgs, extroles, get_now_datetime(),
                                                        lambda account, ctx:
                                                        self._default_new_user_build_user_payload(account, ctx), {
                                                            "access_token": access_token,
                                                            "refresh_token": refresh_token,
                                                            "expires_at": expires_at,
                                                            "accext": context
                                                        })

        return user_token, user_ext_dict

    def bd_sync_login(self, params):
        acc_name = params.get('acc_name')
        refresh_token = params.get('refresh_token')
        access_token = params.get('access_token')
        expires_in = params.get('expires_in')
        userid = int(params.get('userid'))
        portrait = params.get('portrait')
        username = params.get('username')
        openid = params.get('openid')
        is_realname = int(params.get('is_realname', '1'))
        realname = ''
        userdetail = ''
        birthday = ''
        marriage = ''
        sex = ''
        blood = ''
        figure = ''
        constellation = ''
        education = ''
        trade = ''
        job = ''
        expires_in = expires_in - 20 * 60  # seconds
        expires_at = arrow.now(self.default_tz).shift(seconds=+expires_in).datetime

        acc_ext: AccountExt = DataDao.account_ext_by_bd_user_id(userid)
        # print("find acc_ext:", acc_ext)
        log.info("bd_sync_login bd userid:{}".format(userid))
        now_tm = get_now_datetime()
        result = {}
        if not acc_ext:
            # new user
            # print("not find acc_ext userid:", userid)
            log.info("bd_sync_login not find acc_ext :{}".format(userid))
            user_token, user_ext_dict = self._new_user(acc_name, '654321', username, access_token,
                                                                   refresh_token, expires_at, dict(realname=realname,
                                                                                                   portrait=portrait,
                                                                                                   userdetail=userdetail,
                                                                                                   birthday=birthday,
                                                                                                   marriage=marriage,
                                                                                                   sex=sex,
                                                                                                   blood=blood,
                                                                                                   figure=figure,
                                                                                                   constellation=constellation,
                                                                                                   education=education,
                                                                                                   trade=trade,
                                                                                                   job=job,
                                                                                                   is_realname=is_realname,
                                                                                                   userid=userid
                                                                                                   ))
            # acc_id = user_ext_dict['_id']
            # DataDao.new_accounts_ext(userid, username, realname, portrait, userdetail, birthday, marriage, sex,
            #                          blood, figure, constellation, education, trade, job, is_realname,
            #                          account_id=acc_id)
            login_updated_at = user_ext_dict['login_updated_at']
            lud = arrow.get(login_updated_at).replace(tzinfo=self.default_tz)
            result['token'] = user_token
            result['login_at'] = int(arrow.get(lud).timestamp * 1000)
            # print('login_at:', result['login_at'])
            result['pan_acc_list'] = []
            result['username'] = username
            result['portrait'] = portrait
            result['id'] = user_ext_dict['id']
        else:
            # print("find acc_ext:", acc_ext.username)
            log.info("bd_sync_login find acc_ext :{}".format(userid))
            acc_id = acc_ext.account_id
            account: Accounts = DataDao.account_by_id(acc_id)
            DataDao.update_account_ext_by_user_id(userid, dict(username=username, portrait=portrait, account_id=acc_id))

            pan_acc: PanAccounts = DataDao.pan_account_by_bd_uid(acc_id, acc_ext.user_id)
            if not pan_acc:
                pan_acc = DataDao.pan_account_by_name(acc_id, acc_name)
            if pan_acc:
                if pan_acc.pin != 1:
                    n = DataDao.query_pan_acc_count_by_acc_id(acc_id)
                    if n > 1:
                        DataDao.update_pan_account_by_acc_id(acc_id, {'pin': 0})
                DataDao.update_pan_account_by_pk(pan_acc.id,
                                                 {"access_token": access_token, "refresh_token": refresh_token,
                                                  "expires_at": expires_at, "token_updated_at": now_tm, "pin": 1})
            else:
                client_id = PAN_SERVICE['client_id']
                client_secret = PAN_SERVICE['client_secret']
                pan_acc_id = DataDao.new_pan_account(acc_id, acc_name, client_id, client_secret,
                                                     access_token, refresh_token, expires_at, get_now_datetime(), pin=1,
                                                     bd_uid=acc_ext.user_id)

                pan_acc = self.get_pan_account(pan_acc_id, acc_id)

            result = self.login_check_user(account)
        return result

    def sync_pan_user_info(self, access_token, account_id):
        jsonrs = restapi.sync_user_info(access_token, True)
        if jsonrs:
            userid = jsonrs.get('userid', '')
            username = jsonrs.get('username', '')
            realname = jsonrs.get('realname', '')
            portrait = jsonrs.get('portrait', '')
            userdetail = jsonrs.get('userdetail', '')
            birthday = jsonrs.get('birthday', '')
            marriage = jsonrs.get('marriage', '')
            sex = jsonrs.get('sex', '')
            blood = jsonrs.get('blood', '')
            figure = jsonrs.get('figure', '')
            constellation = jsonrs.get('constellation', '')
            education = jsonrs.get('education', '')
            trade = jsonrs.get('trade', '')
            job = jsonrs.get('job', '')
            is_realname = jsonrs.get('is_realname', '')
            if not DataDao.check_account_ext_exist(userid):
                return DataDao.new_accounts_ext(userid, username, realname, portrait, userdetail, birthday, marriage, sex,
                                         blood, figure, constellation, education, trade, job, is_realname,
                                         account_id=account_id)
            else:
                DataDao.update_account_ext_by_user_id(userid, dict(username=username, realname=realname,
                                                                   portrait=portrait, userdetail=userdetail,
                                                                   birthday=birthday, marriage=marriage, sex=sex,
                                                                   blood=blood, figure=figure,
                                                                   constellation=constellation, education=education,
                                                                   trade=trade, job=job, is_realname=is_realname,
                                                                   account_id=account_id))
        return None

    def fresh_token(self, pan_id):
        def cb(pan_accounts):
            now = arrow.now(self.default_tz)
            pan: PanAccounts = None
            need_sleep = False
            for pan in pan_accounts:
                if pan.refresh_token:
                    if need_sleep:
                        time.sleep(3)
                    jsonrs = restapi.refresh_token(pan.refresh_token, True)
                    access_token = jsonrs["access_token"]
                    refresh_token = jsonrs["refresh_token"]
                    expires_in = jsonrs["expires_in"] - 20*60  # seconds
                    expires_at = now.shift(seconds=+expires_in).datetime
                    now_tm = get_now_datetime()
                    DataDao.update_pan_account_by_pk(pan.id,
                                                     {"access_token": access_token, "refresh_token": refresh_token,
                                                      "expires_at": expires_at, "token_updated_at": now_tm})
                    pan.access_token = access_token
                    pan.refresh_token = refresh_token
                    pan.expires_at = expires_at
                    pan.token_updated_at = now_tm
                    try:
                        log.info("sync pan user[{},{}] info to db!".format(access_token, pan.user_id))
                        self.sync_pan_user_info(access_token, pan.user_id)
                    except Exception as e:
                        log.error("sync_pan_user_info err:", e)
                    need_sleep = True
            return pan

        if pan_id:
            return DataDao.check_expired_pan_account_by_id(pan_id, callback=cb)
        else:
            DataDao.check_expired_pan_account(callback=cb)
        return None


auth_service = AuthService()
