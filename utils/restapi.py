# -*- coding: utf-8 -*-
"""
Created by susy at 2019/10/19
"""
import requests
from cfg import PAN_SERVICE
import time
import json
from utils import url_encode, get_now_ts, log as logger
from utils.constant import PAN_ERROR_CODES
POINT = "{protocol}://{domain}".format(protocol=PAN_SERVICE['protocol'], domain=PAN_SERVICE['domain'])


# auth
def access_token_code(code):
    auth_point = "{}://{}".format(PAN_SERVICE['protocol'], PAN_SERVICE['auth_domain'])
    _params = {'grant_type': 'authorization_code', 'client_id': PAN_SERVICE["client_id"],
              'code': code,
              'redirect_uri': 'oob',
              'client_secret': PAN_SERVICE["client_secret"]}
    pan_url = '{}token'.format(auth_point)
    rs = requests.get(pan_url, params=_params)
    # print(rs.content)
    jsonrs = rs.json()
    return jsonrs


def refresh_token(refresh_tk, recursion=True):
    auth_point = "{}://{}".format(PAN_SERVICE['protocol'], PAN_SERVICE['auth_domain'])
    path = "token"
    params = {"grant_type": 'refresh_token', "refresh_token": refresh_tk, "client_id": PAN_SERVICE["client_id"],
              "client_secret": PAN_SERVICE["client_secret"]}
    headers = {"User-Agent": "pan.baidu.com"}
    rs = requests.get("%s%s" % (auth_point, path), params=params, headers=headers)
    # logger.info("refresh_token request state:{}".format(rs.status_code))
    # print("content:", rs.content)
    logger.info("restapi refresh_token:{}, status_code:{}".format(refresh_tk, rs.status_code))
    if rs.status_code == 200:
        jsonrs = rs.json()
        return jsonrs
    else:
        logger.warn(rs.content)
        if recursion:
            time.sleep(1)
            return refresh_token(refresh_tk, False)
        else:
            return {}


# pan accounts
def sync_user_info(access_token, recursion=True):
    auth_point = "{}://{}".format(PAN_SERVICE['protocol'], "openapi.baidu.com/rest/2.0/passport/users/getInfo")
    params = {"access_token": access_token}
    headers = {"User-Agent": "pan.baidu.com"}

    rs = requests.get(auth_point, params=params, headers=headers)
    # logger.info("sync_user_info request state:{}".format(rs.status_code))
    # print("content:", rs.content)
    logger.info("restapi sync_user_info access_token:{}, status_code:{}".format(access_token, rs.status_code))
    if rs.status_code == 200:
        jsonrs = rs.json()
        return jsonrs
    else:
        if recursion:
            time.sleep(1)
            return refresh_token(refresh_token, False)
        else:
            return {}


def file_list(access_token, parent_dir: None, recursion=True):
    url_path = 'file'
    from_dir = '/'
    if parent_dir:
        from_dir = parent_dir
    params = {"method": 'list', "access_token": access_token, "dir": from_dir, "limit": 10000}
    headers = {"User-Agent": "pan.baidu.com"}
    rs = requests.get("%s/%s" % (POINT, url_path), params=params, headers=headers)
    # logger.info("file_list request state:{}".format(rs.status_code))
    logger.info("restapi file_list parent_dir:{}, status_code:{}".format(parent_dir, rs.status_code))
    if rs.status_code == 200:
        jsonrs = rs.json()
        data_list = jsonrs.get('list', [])
        logger.info("restapi file_list count:{}".format(len(data_list)))
        # layer = 0
        return data_list
    else:
        if recursion:
            time.sleep(1)
            return file_list(access_token, parent_dir, False)
        else:
            return None


def file_search(access_token, key, web=0, parent_dir=None):
    url_path = 'file'
    from_dir = '/'
    if parent_dir:
        from_dir = parent_dir
    params = {"method": 'search', "access_token": access_token, "key": key, "recursion": 0, "dir": from_dir, "web": web}
    headers = {"User-Agent": "pan.baidu.com"}
    rs = requests.get("%s/%s" % (POINT, url_path), params=params, headers=headers)
    # logger.info("file_search request state:{}".format(rs.status_code))
    # logger.info("file search content:{}".format(rs.content))
    logger.info("restapi file_search key:{}, status_code:{}".format(key, rs.status_code))
    jsonrs = rs.json()
    data_list = jsonrs.get('list', [])
    # layer = 0
    return data_list


def del_file(access_token, filepath):
    url_path = 'file'
    params = {"method": 'filemanager', "access_token": access_token, "opera": "delete"}
    datas = {"async": 0, "filelist": '["%s"]' % filepath}
    headers = {"User-Agent": "pan.baidu.com"}
    rs = requests.post("%s/%s" % (POINT, url_path), params=params, data=datas, headers=headers)
    # print("content:", rs.content)
    jsonrs = rs.json()
    # print(jsonrs)
    err_no = jsonrs["errno"]
    logger.info("restapi del file:{}, err_no:{}".format(filepath, err_no))
    if err_no:
        err_msg = jsonrs.get("err_msg", "")
        if not err_msg:
            err_msg = PAN_ERROR_CODES.get(err_no, "")
            jsonrs["err_msg"] = err_msg
    return jsonrs


def file_rename(access_token, filepath, newname):
    url_path = 'file'
    params = {"method": 'filemanager', "access_token": access_token, "opera": "rename"}
    filelist = '[{%s}]' % ('"path":"{path}", "newname":"{newname}"'.format(path=filepath, newname=newname))
    datas = {"async": 0, "filelist": filelist}
    headers = {"User-Agent": "pan.baidu.com"}
    # print("file_rename file:", access_token, ",path:", filepath, ", filelist:", datas["filelist"])
    rs = requests.post("%s/%s" % (POINT, url_path), params=params, data=datas, headers=headers)
    # print("content:", rs.content)
    jsonrs = rs.json()
    err_no = jsonrs.get("errno", None)
    logger.info("restapi file_rename:{}, err_no:{}".format(filepath, err_no))
    if err_no:
        err_msg = jsonrs.get("err_msg", "")
        if not err_msg:
            err_msg = PAN_ERROR_CODES.get(err_no, "")
            jsonrs["err_msg"] = err_msg
    # {'errno': 0, 'info': [{'errno': 0, 'path': '/_SHAREDSYS/07声梦奇缘精讲：第5课.mp4'}], 'request_id': 1739388018147258558}
    return jsonrs


def pan_mkdir(access_token, filepath):
    url_path = 'file'
    params = {"method": 'create', "access_token": access_token}
    datas = {"path": filepath, "size": 0, "isdir": 1, "rtype": 0}
    headers = {"User-Agent": "pan.baidu.com"}
    rs = requests.post("%s/%s" % (POINT, url_path), params=params, data=datas, headers=headers)
    # print("content:", rs.content)
    jsonrs = rs.json()
    # print(jsonrs)
    err_no = jsonrs.get("errno", None)
    logger.info("restapi pan_mkdir:{}, err_no:{}".format(filepath, err_no))
    if err_no:
        err_msg = jsonrs.get("err_msg", "")
        if not err_msg:
            err_msg = PAN_ERROR_CODES.get(err_no, "")
            jsonrs["err_msg"] = err_msg
    return jsonrs


def sync_file(access_token, fsids, fetch_dlink=True):
    url_path = 'multimedia'
    # print(str(fsids))
    dlink_tag = 1
    if not fetch_dlink:
        dlink_tag = 0
    params = {"method": 'filemetas', "access_token": access_token, "dlink": dlink_tag, "fsids": str(fsids)}
    headers = {"User-Agent": "pan.baidu.com"}
    # logger.info("sync_file %s/%s" % (POINT, url_path))
    rs = requests.get("%s/%s" % (POINT, url_path), params=params, headers=headers, verify=False)
    jsonrs = rs.json()
    # print(jsonrs)
    if jsonrs:
        err_no = jsonrs.get("errno", None)
        logger.info("restapi sync_file fsids:{}, err_no:{}".format(fsids, err_no))
        return jsonrs.get('list', [])
    return []


def query_file_head(url):
    headers = {"User-Agent": "pan.baidu.com"}
    res = requests.head(url, headers=headers)
    # md5_val = res.headers.get('Content-MD5', "")
    last_loc_url = url
    recursive_cnt = 10
    if res.status_code == 302:
        loc_url = res.headers.get('Location', '')
        last_loc_url = loc_url
        while recursive_cnt > 0 and res.status_code == 302 and loc_url:
            recursive_cnt = recursive_cnt - 1
            res = requests.head(loc_url, headers=headers)
            last_loc_url = loc_url
            loc_url = res.headers.get('Location', '')
    # print("recursive_cnt:", recursive_cnt)
    # print("header:", res.headers)
    # print("last_loc_url:", last_loc_url)
    # print("md5_val:", md5_val)
    logger.info("query_file_head status_code:{}".format(res.status_code))
    return last_loc_url


def get_media_flv_info(access_token, fpath):
    url_path = 'file'
    params = {"method": 'streaming', "access_token": access_token, "path": fpath, "type": "M3U8_FLV_264_480", "nom3u8": 1}
    ua = "xpanvideo;{app};{ver};{sys};{sys_ver};flv".format(app="netdisk", ver='2.2.1', sys="pc-mac", sys_ver="10.13.6")
    headers = {"User-Agent": ua}
    url = "%s/%s" % (POINT, url_path)
    logger.info("get_media_flv_info params:{}, url:{}".format(params, url))
    rs = requests.get(url, params=params, headers=headers, verify=False)
    jsonrs = rs.json()
    err_no = jsonrs["errno"]
    if err_no:
        err_msg = jsonrs.get("err_msg", "")
        if not err_msg:
            err_msg = PAN_ERROR_CODES.get(err_no, "")
            jsonrs["err_msg"] = err_msg
    else:
        mlink = "%s/%s" % (POINT, url_path)
        mlink = "{qp}?method=streaming&path={path}&type=M3U8_FLV_264_480&adToken={adToken}".format(qp=mlink,
                                                                                                   path=fpath,
                                                                                                   adToken=
                                                                                                   jsonrs['adToken'])
        jsonrs['mlink_start_at'] = jsonrs['ltime'] + get_now_ts()
        jsonrs['mlink'] = mlink
    logger.info("get_media_flv_info jsonrs:{}".format(jsonrs))
    return jsonrs


def get_dlink_by_sync_file(access_token, fs_id, need_thumbs=False):
    need_thumb_val = 0
    if need_thumbs:
        need_thumb_val = 1
    url_path = 'multimedia'
    params = {"method": 'filemetas', "access_token": access_token, "dlink": 1, "fsids": str([fs_id]), "thumb": need_thumb_val}
    headers = {"User-Agent": "pan.baidu.com"}
    url = "%s/%s" % (POINT, url_path)
    logger.info('get_dlink_by_sync_file:{}'.format(url))
    logger.info('get_dlink_by_sync_file params:{}'.format(params))
    thumbs = {}
    try:
        rs = requests.get(url, params=params, headers=headers, verify=False)
        jsonrs = rs.json()
        # print(jsonrs)
        if jsonrs:
            err_no = jsonrs.get("errno", None)
            logger.info("restapi get_dlink_by_sync_file fs_id:{}, err_no:{}".format(fs_id, err_no))
            sync_list = jsonrs.get('list', [])
            for sync_item in sync_list:
                if fs_id == sync_item['fs_id']:
                    dlink = sync_item['dlink']
                    if need_thumbs:
                        if "thumbs" in sync_item:
                            thumbs = sync_item["thumbs"]
                    return dlink, thumbs
    except Exception:
        pass
    return None, thumbs


def is_black_list_error(jsonrs):
    err_no = jsonrs["errno"]
    if err_no:
        if err_no in [115, 108, 110]:
            return True
    return False


def share_folder(access_token, fs_id, pwd, period=1):
    url_path = 'share?method=set&access_token=%s' % access_token
    url = "%s/%s" % (POINT, url_path)
    headers = {"User-Agent": "pan.baidu.com"}
    params = {"fid_list": "[%s]" % fs_id, "schannel": 4, "channel_list": "[]", "pwd": pwd, "period": period}
    rs = requests.post(url, data=params, headers=headers, verify=False)
    jsonrs = rs.json()
    err_no = jsonrs["errno"]
    logger.info("restapi share_folder fs_id:{}, err_no:{}".format(fs_id, err_no))
    if err_no:
        err_msg = jsonrs.get("err_msg", "")
        if not err_msg:
            err_msg = PAN_ERROR_CODES.get(err_no, "")
            jsonrs["err_msg"] = err_msg
    # print("share_folder:", jsonrs)
    return jsonrs


def get_share_randsk(share_id, pwd, surl):
    url_path = 'share?method=verify'
    url = "%s/%s" % (POINT, url_path)
    headers = {"User-Agent": "pan.baidu.com", "Referer": "pan.baidu.com"}
    params = {"pwd": pwd, "surl": surl, "shareid": share_id}
    datas = {"pwd": pwd}
    rs = requests.post(url, data=datas, params=params, headers=headers, verify=False)
    jsonrs = rs.json()
    # print(jsonrs)
    err_no = jsonrs["errno"]
    logger.info("restapi get_share_randsk share_id:{}, err_no:{}".format(share_id, err_no))
    if err_no:
        err_msg = jsonrs.get("err_msg", "")
        if not err_msg:
            err_msg = PAN_ERROR_CODES.get(err_no, "")
            jsonrs["err_msg"] = err_msg
    return jsonrs


def get_share_list(share_id, short_url, randsk):
    url_path = 'share?method=list'
    url = "%s/%s" % (POINT, url_path)
    headers = {"User-Agent": "pan.baidu.com"}
    params = {"shareid": share_id, "shorturl": short_url, "sekey": randsk, "root": 1}
    rs = requests.get(url, params=params, headers=headers, verify=False)
    jsonrs = rs.json()
    err_no = jsonrs["errno"]
    logger.info("restapi get_share_list share_id:{}, err_no:{}".format(share_id, err_no))
    if err_no:
        err_msg = jsonrs.get("err_msg", "")
        if not err_msg:
            err_msg = PAN_ERROR_CODES.get(err_no, "")
            jsonrs["err_msg"] = err_msg
    logger.info("get_share_list:{}".format(jsonrs))
    return jsonrs


def get_share_info(share_id, special_short_url, randsk):
    point = "{protocol}://{domain}".format(protocol=PAN_SERVICE['protocol'], domain="pan.baidu.com/api")
    url_path = 'shorturlinfo'
    url = "%s/%s" % (point, url_path)
    headers = {"User-Agent": "pan.baidu.com"}
    params = {"shareid": share_id, "shorturl": special_short_url, "spd": randsk}
    rs = requests.get(url, params=params, headers=headers, verify=False)
    jsonrs = rs.json()
    err_no = jsonrs["errno"]
    logger.info("restapi get_share_info share_id:{}, err_no:{}".format(share_id, err_no))
    if err_no:
        jsonrs["errno"] = 0
    logger.info("get_share_info:{}".format(jsonrs))
    return jsonrs


def transfer_share_files(access_token, share_id, from_uk, randsk, fs_id, path, recursion=True):
    point = "{protocol}://{domain}".format(protocol=PAN_SERVICE['protocol'], domain="pan.baidu.com/share")
    url_path = 'transfer'
    url = "%s/%s" % (point, url_path)
    headers = {"User-Agent": "pan.baidu.com", "Referer": "pan.baidu.com"}
    # params = {"access_token": access_token, "shareid": share_id, "from": from_uk, "sekey": randsk, "async": 0}
    # params 内部转码后报参数错误
    url = url + "?access_token={}&shareid={}&from={}&sekey={}&async=0".format(access_token, share_id, from_uk, randsk)
    datas = {"fsidlist": "[%s]" % fs_id, "path": path}
    logger.info("transfer_share_files url:{},fsidlist:{},path:{}".format(url, datas['fsidlist'], path))
    rs = requests.post(url, data=datas, headers=headers, verify=False)
    jsonrs = rs.json()
    err_no = jsonrs["errno"]
    if err_no:
        if 12 == err_no:
            if "info" in jsonrs:
                info_list = jsonrs["info"]
                if info_list:
                    _info = info_list[0]
                    info_err_no = _info.get("errno", None)
                    if info_err_no and info_err_no == -30 and "path" in _info:
                        return {"errno": -30, "path": _info["path"]}
            if recursion:
                time.sleep(0.5)
                logger.info("transfer_share_files will retry on time!")
                return transfer_share_files(access_token, share_id, from_uk, randsk, fs_id, path, False)

        err_msg = jsonrs.get("err_msg", "")
        if not err_msg:
            err_msg = PAN_ERROR_CODES.get(err_no, "")
            jsonrs["err_msg"] = err_msg
    logger.info("transfer_share_files:{}".format(jsonrs))
    return jsonrs


def split_file_content(size, cnt, fs_id):
    import json
    min_size = 1024 * 1024
    page_count = cnt
    l = size
    while l / page_count < min_size and page_count > 1:
        page_count = page_count - 1
    page_size = round(l / page_count)
    task_list = []

    for i in range(page_count-1):
        task_params = {'id': fs_id + '_' + str(i), 'source_id': fs_id, 'start': i * page_size,
                       'end': (i + 1) * page_size, 'over': 0, 'pos': 0, 'retry': 0, 'loader_id': 0,
                       'state': 2}
        task_list.append(task_params)
    last_task_params = {'id': fs_id + '_' + str(page_count-1), 'source_id': fs_id, 'start': (page_count-1) * page_size, 'end': l,
                        'over': 0, 'pos': 0, 'retry': 0, 'loader_id': 0, 'state': 2}
    task_list.append(last_task_params)
    print(json.dumps(task_list))



if __name__ == '__main__':
    from controller.service import pan_service
    from dao.dao import DataDao
    # at = pan_service.pan_acc.access_token
    # print(file_list(at, "/"))
    fs_id = '214812092436210'
    path = '/家长看（C妈力荐）  PDF 做孩子最好的英语学习规划师  中国儿童英语习得全路线图.pdf'
    # 创建分享文件
    # print(share_folder(at, fs_id, 'a1b2'))
    # {'errno': 0, 'request_id': 7211784906115626160, 'shareid': 1110347500, 'link': 'https://pan.baidu.com/s/1VI4YH1WC_eJ_yg1Zbha4Eg', 'shorturl': 'https://pan.baidu.com/s/1VI4YH1WC_eJ_yg1Zbha4Eg', 'ctime': 1573137992, 'expiredType': 1, 'premis': False}
    # 获得分享打开密码
    # print(get_share_randsk(1110347500, 'a1b2', 'VI4YH1WC_eJ_yg1Zbha4Eg'))
    # {'errno': 0, 'err_msg': '', 'request_id': 294418531557578125, 'randsk': 'J82nBsdaTzjsend0LBOFPGc2ZEEeOrwF5jzaCCyhoNE%3D'}
    # 获得文件列表
    # print(get_share_list(1110347500, 'VI4YH1WC_eJ_yg1Zbha4Eg', 'J82nBsdaTzjsend0LBOFPGc2ZEEeOrwF5jzaCCyhoNE'))
    # {'errno': 0, 'request_id': 294455618585607178, 'server_time': 1573138736, 'title': '/家长看（C妈力荐）  PDF 做孩子最好的英语学习规划师  中国儿童英语习得全路线图.pdf', 'list': [{'category': '4', 'fs_id': '214812092436210', 'isdir': '0', 'local_ctime': '1453303594', 'local_mtime': '1453303594', 'md5': '1cac7747df02d534288e807b9fb57338', 'path': '/家长看（C妈力荐）  PDF 做孩子最好的英语学习规划师  中国儿童英语习得全路线图.pdf', 'server_ctime': '1453303594', 'server_filename': '家长看（C妈力荐）  PDF 做孩子最好的英语学习规划师  中国儿童英语习得全路线图.pdf', 'server_mtime': '1545959795', 'size': '32100319', 'thumbs': {'url1': 'https://thumbnail0.baidupcs.com/thumbnail/1cac7747df02d534288e807b9fb57338?fid=2717926781-250528-214812092436210&time=1573135200&rt=sh&sign=FDTAER-DCb740ccc5511e5e8fedcff06b081203-opClOZbytJbBqk5LXTY2ggKm6D8%3D&expires=8h&chkv=0&chkbd=0&chkpc=&dp-logid=294455618585607178&dp-callid=0&size=c140_u90&quality=100&vuk=-&ft=video', 'url3': 'https://thumbnail0.baidupcs.com/thumbnail/1cac7747df02d534288e807b9fb57338?fid=2717926781-250528-214812092436210&time=1573135200&rt=sh&sign=FDTAER-DCb740ccc5511e5e8fedcff06b081203-opClOZbytJbBqk5LXTY2ggKm6D8%3D&expires=8h&chkv=0&chkbd=0&chkpc=&dp-logid=294455618585607178&dp-callid=0&size=c850_u580&quality=100&vuk=-&ft=video'}, 'docpreview': 'https://pcsdata.baidu.com/doc/1cac7747df02d534288e807b9fb57338?fid=2717926781-250528-214812092436210&time=1573138736&rt=sh&sign=FDTAER-DCb740ccc5511e5e8fedcff06b081203-o5H7ES19d9HBrfAgzT%2FWVZr%2FqZs%3D&expires=8h&chkv=0&chkbd=0&chkpc=&dp-logid=294455618585607178&dp-callid=0'}], 'share_id': 1110347500, 'uk': 2717926781}
    # 获得文件信息
    # print(get_share_info(1110347500, '1VI4YH1WC_eJ_yg1Zbha4Eg', 'J82nBsdaTzjsend0LBOFPGc2ZEEeOrwF5jzaCCyhoNE'))
    # {'shareid': 1110347500, 'uk': 2717926781, 'dir': '', 'type': 0, 'prod_type': 'share', 'page': 1, 'root': 0, 'third': 0, 'longurl': 'shareid=1110347500&uk=2717926781', 'fid': 0, 'errno': 0, 'expire_days': 1, 'ctime': 1573137992, 'expiredtype': 85125, 'fcount': 1, 'uk_str': '2717926781'}
    # 转存账户token
    # _pan_acc = DataDao.pan_account_list(5, False)
    # print(_pan_acc.access_token)
    # print(pan_mkdir(_pan_acc.access_token, "/__tmp/"))
    # {'fs_id': 233899009366173, 'path': '/__tmp', 'ctime': 1573185366, 'mtime': 1573185366, 'status': 0, 'isdir': 1, 'errno': 0, 'name': '/__tmp', 'category': 6}
    # print(file_list(_pan_acc.access_token, "/"))
    # print(file_list('21.a5e710bd8298fb220972172af377541d.2592000.1573799656.2717926781-9850001', "/__tmp/"))
    # transfer_share_files(_pan_acc.access_token, 1110347500, from_uk=2717926781, randsk='J82nBsdaTzjsend0LBOFPGc2ZEEeOrwF5jzaCCyhoNE%3D', fs_id='214812092436210', path="/__tmp")
    # {'errno': 0, 'extra': {'list': [{'from': '/家长看（C妈力荐）  PDF 做孩子最好的英语学习规划师  中国儿童英语习得全路线图.pdf', 'from_fs_id': 214812092436210, 'to': '/__tmp//家长看（C妈力荐）  PDF 做孩子最好的英语学习规划师  中国儿童英语习得全路线图.pdf'}]}, 'info': [{'errno': 0, 'fsid': 214812092436210, 'path': '/家长看（C妈力荐）  PDF 做孩子最好的英语学习规划师  中国儿童英语习得全路线图.pdf'}], 'newno': '', 'request_id': 2531398234635023443, 'show_msg': '', 'task_id': 0}
    # print(file_list(_pan_acc.access_token, "/__tmp/家长看（C妈力荐）  PDF 做孩子最好的英语学习规划师  中国儿童英语习得全路线图.pdf"))
    # print(file_search(_pan_acc.access_token, key="规划师  中国儿童", parent_dir="/__tmp"))
    """
    curl "https://pan.baidu.com/share/transfer?access_token=21.8e1f959c2fc669bb8da59fd58244316a.2592000.1575470390.758773548-9850001&shareid=1110347500&from=2717926781&sekey=J82nBsdaTzjsend0LBOFPGc2ZEEeOrwF5jzaCCyhoNE%3D" -d 'fsidlist=[214812092436210]&path=%2f' -H "User-Agent: pan.baidu.com" -H "Referer:pan.baidu.com"
    """
    # 删除某一个文件
    # del_file(_pan_acc.access_token, "/家长看（C妈力荐）  PDF 做孩子最好的英语学习规划师  中国儿童英语习得全路线图.pdf")
    # split_file_content(1683106197, 9, '486285832886933')
    # get_media_flv_info()
    params = {'method': 'streaming', 'access_token': '21.769a60e242d94eee55fa72128d788bc9.2592000.1585700305.3090991555-17490062', 'path': '/知识库/02.会员库/完结/D【英语学习】/31【粽子英语】/01.迪斯尼英语【完结】/25. 精讲课：第25集（上）.mp4', 'type': 'M3U8_FLV_264_480', 'nom3u8': 1}
    # rs = get_media_flv_info('21.769a60e242d94eee55fa72128d788bc9.2592000.1585700305.3090991555-17490062', '/知识库/02.会员库/完结/D【英语学习】/31【粽子英语】/01.迪斯尼英语【完结】/25. 精讲课：第25集（上）.mp4')
    file_rename("21.9cf5249bec2419e49c6434e70f2ac146.2592000.1584546455.721132532-17490062", "/_SHAREDSYS/07声梦奇缘精讲：第5课.mp4", "865202870529846.mp4", "/_SHAREDSYS/")