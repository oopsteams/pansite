# -*- coding: utf-8 -*-
"""
Created by susy at 2020/5/4
"""
import os
from controller.action import BaseHandler
from controller.wx.goods_service import goods_service
from utils import obfuscate_id, decrypt_id
from PIL import Image
import json


class WXAppUpload(BaseHandler):

    def post(self):
        basepath = self.context['basepath']
        fname = self.get_argument("filename")
        # puid = self.get_argument("uid")
        fuzzy_pid = self.get_argument("pid")
        idx = self.get_argument("idx")
        istop = int(self.get_argument("top", "0"))
        isthumb = int(self.get_argument("s", "0"))
        top = int(self.get_argument("y", "0"))

        ofilename = self.get_argument("o", "")
        delidxstr = self.get_argument("delidx", "")
        delidxs = []
        if delidxstr:
            delidxs = delidxstr.split(',')
        if idx:
            idx = int(idx)
        rs = {"status": 0}
        puid = None
        if fuzzy_pid:
            pid = decrypt_id(fuzzy_pid)
            p_dict = goods_service.query_product(pid)
            puid = p_dict['ref_id']
        if puid:
            p_ref_id = decrypt_id(puid)
            upload_path = os.path.join(basepath, 'static', 'files', puid, fuzzy_pid)  # 文件的暂存路径
            if isthumb:
                upload_path = os.path.join(upload_path, 's')
            file_metas = self.request.files.get('files', None)  # 提取表单中‘name’为‘file’的文件元数据
            # print ("upload file_metas:",file_metas)
            if not file_metas:
                rs['result'] = 'Invalid Args'
                return rs

            if os.path.exists(upload_path) and idx == 0 and delidxs:
                for fn in delidxs:
                    fnp = os.path.join(upload_path, fn)
                    if os.path.exists(fnp):
                        os.remove(fnp)
                        goods_service.del_product_img(pid, fnp)
                        # Mission.delProductImg(pid, fnp)

            if not os.path.exists(upload_path):
                os.makedirs(upload_path)

            for meta in file_metas:
                # filename = meta['filename']
                file_path = os.path.join(upload_path, fname)

                if not isthumb:
                    pi = goods_service.build_product_img(pid, fname, idx, istop, p_ref_id)
                else:
                    goods_service.update_product_img(pid, ofilename, {"simgurl": fname})
                with open(file_path, 'wb') as up:
                    up.write(meta['body'])
                    # OR do other thing

                # 生成缩略图
                if not isthumb:
                    print("top:", top)
                    img = Image.open(file_path)
                    iw, ih = img.size
                    print("img size:", img.size)
                    if iw < ih:
                        box = (0, top, iw, top + iw - 1)
                        region = img.crop(box)
                    else:
                        region = img
                    sfname = fname
                    upload_path = os.path.join(basepath, 'static', 'files', puid, fuzzy_pid, 's')
                    if not os.path.exists(upload_path):
                        os.makedirs(upload_path)
                    file_path = os.path.join(upload_path, sfname)
                    region.save(file_path, quality=80)
                    goods_service.update_product_img(pid, fname, {"simgurl": sfname})

                    print("s file_path:", file_path)

        self.write(json.dumps(rs))


