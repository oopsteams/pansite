# -*- coding: utf-8 -*-
"""
Created by susy at 2019/10/20
"""
import requests
from cfg import mysql_worker_config, ES
mysql_worker_config['port'] = 3307
ES["hosts"] = [{"host": "127.0.0.1", "port": 9201}]
import time
import os
from utils import random_password
from dao.mdao import DataDao


def downfile(filename,url,start,end,total):
    header={
        'Range': 'bytes=%d-%d'%(start,end-1),
        "User-Agent": "pan.baidu.com"
    }
    try:
        res=requests.get(url,stream=True, verify=False,headers=header)
    except BaseException as e:
        print(e)
    with open(filename,'ab+') as F:
        # F.seek(start)
        # F.truncate()#删除当前指针后的内容
        s=start
        for i in res.iter_content(1024):
            F.write(i)
            s=s+len(i)
            #print(s)
            # time.sleep(1)
            print('{:.2%}'.format((s-start)/total), end="\r")


def query_file_head(url):
    headers = {"User-Agent": "pan.baidu.com"}
    res = requests.head(url, headers=headers)
    md5_val = res.headers.get('Content-MD5', "")
    print("header:", res.headers)
    print("content:", res.content)
    print("md5_val:", md5_val)
    print("status_code:", res.status_code)


def load_pan_acc(file_name):
    from controller.service import pan_service
    obj = DataDao.get_data_item_by_filename(file_name)
    print("item:", obj)
    if obj:
        rs = DataDao.pan_account_by_id(obj['panacc'])
        if rs:
            params = pan_service.query_file(obj['id'])
            print(rs)
            print("file info:", params)
            print("file dlink:", params['item']['dlink'])

if __name__ == '__main__':

    _url = 'https://d.pcs.baidu.com/file/dab80fc0592783edb16fd49a5e810015?fid=2717926781-250528-641249558821162&rt=pr&sign=FDtAER-DCb740ccc5511e5e8fedcff06b081203-YEtl3PsJ%2Fd%2FyBbdSMBfY0Zdicmk%3D&expires=8h&chkbd=0&chkv=0&dp-logid=1631313692692286822&dp-callid=0&dstime=1572532680&r=610572866&access_token=21.a5e710bd8298fb220972172af377541d.2592000.1573799656.2717926781-9850001'
    # header: {'Connection': 'keep-alive', 'Content-Type': 'text/plain; charset=utf-8',
    #          'Date': 'Sun, 20 Oct 2019 02:41:40 GMT', 'Flow-Level': '3', 'Http-X-Isis-Logid': '1067964967966296431',
    #          'Location': 'http://d7.baidupcs.com/file/dea063d108f71d0a3ead2f39a1cbf554?bkt=en-6766f9da69592c12affcb77c3a28035396f3ec055be3a03380fa4aa4e2c278dc7260351006004136a1a9f1dadc0a53e239493629b5e64092fefb6892368eac42&xcode=0a0ed92ea5fad649edd1032ada325e158a3db9d668100ef26c92ffd450d743eb7318f89076b711aaf2cad6a7ea7250019717ec4418c70769&fid=2717926781-250528-245730032113873&time=1571539300&sign=FDTAXGERLQBHSKfa-DCb740ccc5511e5e8fedcff06b081203-aJdqLX3gsgRNeHQCwCQwvb0sBuI%3D&to=d7&size=243968000&sta_dx=243968000&sta_cs=30386&sta_ft=avi&sta_ct=7&sta_mt=6&fm2=MH%2CQingdao%2CAnywhere%2C%2Ctianjin%2Ccnc&ctime=1378347940&mtime=1554304936&resv0=cdnback&resv1=0&resv2=&resv3=&resv4=&vuk=2717926781&iv=0&htype=&randtype=&newver=1&newfm=1&secfm=1&flow_ver=3&pkey=en-d51dfeca6bf0636a0466aed5448a18bbf50ba6f919e7ea8a7ca819f6cf70ef21adaf86a4931636d08e5969f86a5b5ada2e612ce3d3c7510f305a5e1275657320&sl=76480590&expires=8h&rt=pr&r=694215333&vbdid=-&fin=little.bear.s01e04.avi&rtype=1&dp-logid=1067964967966296431&dp-callid=0.1&tsl=80&csl=80&csign=BDYhNL2ZG7x22O1db3gPoO51N2E%3D&so=1&ut=6&uter=0&serv=1&uc=1559654663&ti=548236dbf16cf8fab486d99718ab5f8b02f99d93201afc76&reqlabel=250528_f&by=themis',
    #          'P3p': 'CP=" OTI DSP COR IVA OUR IND COM "', 'Remote-Ip': 'd.pcs.baidu.com', 'Server': 'nginx',
    #          'Set-Cookie': 'BAIDUID=34A6AD460A801198B6C54037E89C2898:FG=1; expires=Mon, 19-Oct-20 02:41:40 GMT; max-age=31536000; path=/; domain=.baidu.com; version=1',
    #          'X-Bs-Pcs-Extra': 'user_operator=cnc&app_id=250528&iv=0&file_type=avi&file_size=243968000&digest=dea063d108f71d0a3ead2f39a1cbf554&user_terminal=def&user_type=default&user_id=77767179&freeispflag=-100&method=file&v_user_id=77767179&fs_id=245730032113873&visitor_ip=117.15.89.244&xflag=',
    #          'X-Bs-Remote-Ip': '10.155.31.21',
    #          'X-Bs-Request-Id': 'eXEwMS1vYmplY3QwNC1yMzEtMDMtMDQ4LnlxMDEuYmFpZHUuY29tOjEwLjE1NS4zMS4yMToyMDIwOjEwNjc5NjQ5Njc5NjYyOTY0MzE6MjAxOS0xMC0yMCAxMDo0MTo0MA==',
    #          'X-Pcs-Member': '0', 'X-Poms-Key': '1400dea063d108f71d0a3ead2f39a1cbf5541058cefb00000e8aa800',
    #          'Yld': '9088482050308983570'}
    """
    {'Connection': 'keep-alive', 'Content-Type': 'text/plain; charset=utf-8', 'Date': 'Thu, 31 Oct 2019 14:52:03 GMT', 'Flow-Level': '3', 'Http-X-Isis-Logid': '1631313692692286822', 'Location': 'http://qdall01.baidupcs.com/file/dab80fc0592783edb16fd49a5e810015?bkt=en-26dcfdb4e5ee1a49a33089a16a190b8c383b7e70835fc93886515b0b344607b3967f6b43bed9fec6&fid=2717926781-250528-641249558821162&time=1572533523&sign=FDTAXGERLQBHSKfW-DCb740ccc5511e5e8fedcff06b081203-cnNooOtkucA5XMAijB05aIi4wJk%3D&to=34&size=9730818&sta_dx=9730818&sta_cs=82027&sta_ft=mkv&sta_ct=7&sta_mt=7&fm2=MH%2CQingdao%2CAnywhere%2C%2Cheilongjiang%2Ccnc&ctime=1478017640&mtime=1537022354&resv0=cdnback&resv1=0&resv2=&resv3=&resv4=9730818&vuk=2717926781&iv=-2&htype=&randtype=&newver=1&newfm=1&secfm=1&flow_ver=3&pkey=en-4b39fe50e8ac02df3eb62da2fcfda0a1f9d94b50840143f8bda4dc00c043f4eaced09c36491e312e&sl=80740430&expires=8h&rt=pr&r=610572866&vbdid=-&fin=13+-+5+-+Choosing+the+Number+of+Clusters+%288+min%29.mkv&rtype=1&dp-logid=1631313692692286822&dp-callid=0.1&tsl=15&csl=78&csign=7rHoPlXj4i5S0GSHpz5yFNKP3z8%3D&so=1&ut=8&uter=0&serv=1&uc=1559654663&ti=4de86e32109cef278b2eba14ededffb3d15b847f70d4aba7&reqlabel=250528_f&by=themis', 'P3p': 'CP=" OTI DSP COR IVA OUR IND COM "', 'Remote-Ip': 'd.pcs.baidu.com', 'Server': 'nginx', 'Set-Cookie': 'BAIDUID=C29517A8F074E231E76973DB24D97873:FG=1; expires=Fri, 30-Oct-20 14:52:03 GMT; max-age=31536000; path=/; domain=.baidu.com; version=1', 'X-Bs-Pcs-Extra': 'user_terminal=def&file_size=9730818&method=file&file_type=mkv&user_operator=cnc&digest=dab80fc0592783edb16fd49a5e810015&user_id=77767179&visitor_ip=116.136.20.85&app_id=250528&v_user_id=77767179&user_type=crack_user&iv=-2&fs_id=641249558821162&freeispflag=-100&xflag=', 'X-Bs-Remote-Ip': '10.61.53.49', 'X-Bs-Request-Id': 'eXEwMS1vYmplY3QwNC1yMDEtMDMtMTI5LnlxMDEuYmFpZHUuY29tOjEwLjYxLjUzLjQ5OjIxMDA6MTYzMTMxMzY5MjY5MjI4NjgyMjoyMDE5LTEwLTMxIDIyOjUyOjAz', 'X-Pcs-Member': '0', 'X-Poms-Key': '0000fdae4e9dd10972321d24e30589795f98', 'Yld': '131994792635416462'}
    header: {'Server': 'nginx', 'Date': 'Sun, 20 Oct 2019 02:44:28 GMT', 'Content-Type': 'text/html', 'Connection': 'close', 'Location': 'http://111.177.8.46/r/d7.baidupcs.com/file/dea063d108f71d0a3ead2f39a1cbf554?bkt=en-6766f9da69592c12affcb77c3a28035396f3ec055be3a03380fa4aa4e2c278dc7260351006004136a1a9f1dadc0a53e239493629b5e64092fefb6892368eac42&xcode=0a0ed92ea5fad649edd1032ada325e158a3db9d668100ef26c92ffd450d743eb7318f89076b711aaf2cad6a7ea7250019717ec4418c70769&fid=2717926781-250528-245730032113873&time=1571539300&sign=FDTAXGERLQBHSKfa-DCb740ccc5511e5e8fedcff06b081203-aJdqLX3gsgRNeHQCwCQwvb0sBuI%3D&to=d7&size=243968000&sta_dx=243968000&sta_cs=30386&sta_ft=avi&sta_ct=7&sta_mt=6&fm2=MH%2CQingdao%2CAnywhere%2C%2Ctianjin%2Ccnc&ctime=1378347940&mtime=1554304936&resv0=cdnback&resv1=0&resv2=&resv3=&resv4=&vuk=2717926781&iv=0&htype=&randtype=&newver=1&newfm=1&secfm=1&flow_ver=3&pkey=en-d51dfeca6bf0636a0466aed5448a18bbf50ba6f919e7ea8a7ca819f6cf70ef21adaf86a4931636d08e5969f86a5b5ada2e612ce3d3c7510f305a5e1275657320&sl=76480590&expires=8h&rt=pr&r=694215333&vbdid=-&fin=little.bear.s01e04.avi&rtype=1&dp-logid=1067964967966296431&dp-callid=0.1&tsl=80&csl=80&csign=BDYhNL2ZG7x22O1db3gPoO51N2E%3D&so=1&ut=6&uter=0&serv=1&uc=1559654663&ti=548236dbf16cf8fab486d99718ab5f8b02f99d93201afc76&reqlabel=250528_f&by=themis', 'content-length': '0', 'Cache-Control': 'no-cache'}
    """
    # _url = "http://d7.baidupcs.com/file/dea063d108f71d0a3ead2f39a1cbf554?bkt=en-6766f9da69592c12affcb77c3a28035396f3ec055be3a03380fa4aa4e2c278dc7260351006004136a1a9f1dadc0a53e239493629b5e64092fefb6892368eac42&xcode=0a0ed92ea5fad649edd1032ada325e158a3db9d668100ef26c92ffd450d743eb7318f89076b711aaf2cad6a7ea7250019717ec4418c70769&fid=2717926781-250528-245730032113873&time=1571539300&sign=FDTAXGERLQBHSKfa-DCb740ccc5511e5e8fedcff06b081203-aJdqLX3gsgRNeHQCwCQwvb0sBuI%3D&to=d7&size=243968000&sta_dx=243968000&sta_cs=30386&sta_ft=avi&sta_ct=7&sta_mt=6&fm2=MH%2CQingdao%2CAnywhere%2C%2Ctianjin%2Ccnc&ctime=1378347940&mtime=1554304936&resv0=cdnback&resv1=0&resv2=&resv3=&resv4=&vuk=2717926781&iv=0&htype=&randtype=&newver=1&newfm=1&secfm=1&flow_ver=3&pkey=en-d51dfeca6bf0636a0466aed5448a18bbf50ba6f919e7ea8a7ca819f6cf70ef21adaf86a4931636d08e5969f86a5b5ada2e612ce3d3c7510f305a5e1275657320&sl=76480590&expires=8h&rt=pr&r=694215333&vbdid=-&fin=little.bear.s01e04.avi&rtype=1&dp-logid=1067964967966296431&dp-callid=0.1&tsl=80&csl=80&csign=BDYhNL2ZG7x22O1db3gPoO51N2E%3D&so=1&ut=6&uter=0&serv=1&uc=1559654663&ti=548236dbf16cf8fab486d99718ab5f8b02f99d93201afc76&reqlabel=250528_f&by=themis"
    # _url = "http://111.177.8.46/r/d7.baidupcs.com/file/dea063d108f71d0a3ead2f39a1cbf554?bkt=en-6766f9da69592c12affcb77c3a28035396f3ec055be3a03380fa4aa4e2c278dc7260351006004136a1a9f1dadc0a53e239493629b5e64092fefb6892368eac42&xcode=0a0ed92ea5fad649edd1032ada325e158a3db9d668100ef26c92ffd450d743eb7318f89076b711aaf2cad6a7ea7250019717ec4418c70769&fid=2717926781-250528-245730032113873&time=1571539300&sign=FDTAXGERLQBHSKfa-DCb740ccc5511e5e8fedcff06b081203-aJdqLX3gsgRNeHQCwCQwvb0sBuI%3D&to=d7&size=243968000&sta_dx=243968000&sta_cs=30386&sta_ft=avi&sta_ct=7&sta_mt=6&fm2=MH%2CQingdao%2CAnywhere%2C%2Ctianjin%2Ccnc&ctime=1378347940&mtime=1554304936&resv0=cdnback&resv1=0&resv2=&resv3=&resv4=&vuk=2717926781&iv=0&htype=&randtype=&newver=1&newfm=1&secfm=1&flow_ver=3&pkey=en-d51dfeca6bf0636a0466aed5448a18bbf50ba6f919e7ea8a7ca819f6cf70ef21adaf86a4931636d08e5969f86a5b5ada2e612ce3d3c7510f305a5e1275657320&sl=76480590&expires=8h&rt=pr&r=694215333&vbdid=-&fin=little.bear.s01e04.avi&rtype=1&dp-logid=1067964967966296431&dp-callid=0.1&tsl=80&csl=80&csign=BDYhNL2ZG7x22O1db3gPoO51N2E%3D&so=1&ut=6&uter=0&serv=1&uc=1559654663&ti=548236dbf16cf8fab486d99718ab5f8b02f99d93201afc76&reqlabel=250528_f&by=themis"



    url = "http://qdall01.baidupcs.com/file/dab80fc0592783edb16fd49a5e810015?bkt=en-26dcfdb4e5ee1a49a33089a16a190b8c383b7e70835fc93886515b0b344607b3967f6b43bed9fec6&fid=2717926781-250528-641249558821162&time=1572533523&sign=FDTAXGERLQBHSKfW-DCb740ccc5511e5e8fedcff06b081203-cnNooOtkucA5XMAijB05aIi4wJk%3D&to=34&size=9730818&sta_dx=9730818&sta_cs=82027&sta_ft=mkv&sta_ct=7&sta_mt=7&fm2=MH%2CQingdao%2CAnywhere%2C%2Cheilongjiang%2Ccnc&ctime=1478017640&mtime=1537022354&resv0=cdnback&resv1=0&resv2=&resv3=&resv4=9730818&vuk=2717926781&iv=-2&htype=&randtype=&newver=1&newfm=1&secfm=1&flow_ver=3&pkey=en-4b39fe50e8ac02df3eb62da2fcfda0a1f9d94b50840143f8bda4dc00c043f4eaced09c36491e312e&sl=80740430&expires=8h&rt=pr&r=610572866&vbdid=-&fin=13+-+5+-+Choosing+the+Number+of+Clusters+%288+min%29.mkv&rtype=1&dp-logid=1631313692692286822&dp-callid=0.1&tsl=15&csl=78&csign=7rHoPlXj4i5S0GSHpz5yFNKP3z8%3D&so=1&ut=8&uter=0&serv=1&uc=1559654663&ti=4de86e32109cef278b2eba14ededffb3d15b847f70d4aba7&reqlabel=250528_f&by=themis"
    """
    {'Connection': 'keep-alive', 'Content-Type': 'text/plain; charset=utf-8', 'Date': 'Thu, 31 Oct 2019 14:53:51 GMT', 'Flow-Level': '3', 'Http-X-Isis-Logid': '1631313692692286822', 'Location': 'http://qdall01.baidupcs.com/file/dab80fc0592783edb16fd49a5e810015?bkt=en-26dcfdb4e5ee1a49a33089a16a190b8c383b7e70835fc93886515b0b344607b3967f6b43bed9fec6&fid=2717926781-250528-641249558821162&time=1572533631&sign=FDTAXGERLQBHSKfW-DCb740ccc5511e5e8fedcff06b081203-2NHkczpGDUM0yLGU7x4oGqfubXM%3D&to=34&size=9730818&sta_dx=9730818&sta_cs=82027&sta_ft=mkv&sta_ct=7&sta_mt=7&fm2=MH%2CQingdao%2CAnywhere%2C%2Cheilongjiang%2Ccnc&ctime=1478017640&mtime=1537022354&resv0=cdnback&resv1=0&resv2=&resv3=&resv4=9730818&vuk=2717926781&iv=-2&htype=&randtype=&newver=1&newfm=1&secfm=1&flow_ver=3&pkey=en-4b39fe50e8ac02df3eb62da2fcfda0a1f9d94b50840143f8bda4dc00c043f4eaced09c36491e312e&sl=80740430&expires=8h&rt=pr&r=610572866&vbdid=-&fin=13+-+5+-+Choosing+the+Number+of+Clusters+%288+min%29.mkv&rtype=1&dp-logid=1631313692692286822&dp-callid=0.1&tsl=15&csl=78&csign=7rHoPlXj4i5S0GSHpz5yFNKP3z8%3D&so=1&ut=8&uter=0&serv=1&uc=1559654663&ti=26fa64dbec288224f1c7bf79dbbe7f475d23d57046e6b709305a5e1275657320&reqlabel=250528_f&by=themis', 'P3p': 'CP=" OTI DSP COR IVA OUR IND COM "', 'Remote-Ip': 'd.pcs.baidu.com', 'Server': 'nginx', 'Set-Cookie': 'BAIDUID=EAC6F7D130DC2D3A7B08FE159430EA11:FG=1; expires=Fri, 30-Oct-20 14:53:51 GMT; max-age=31536000; path=/; domain=.baidu.com; version=1', 'X-Bs-Pcs-Extra': 'v_user_id=77767179&user_operator=cnc&user_type=crack_user&file_size=9730818&iv=-2&user_id=77767179&visitor_ip=116.136.20.85&fs_id=641249558821162&digest=dab80fc0592783edb16fd49a5e810015&method=file&app_id=250528&user_terminal=def&file_type=mkv&freeispflag=-100&xflag=', 'X-Bs-Remote-Ip': '10.155.100.46', 'X-Bs-Request-Id': 'eXEwMS1vYmplY3QwNC1yMzEtMDItMDU2LnlxMDEuYmFpZHUuY29tOjEwLjE1NS4xMDAuNDY6MjE0MDoxNjMxMzEzNjkyNjkyMjg2ODIyOjIwMTktMTAtMzEgMjI6NTM6NTE=', 'X-Pcs-Member': '0', 'X-Poms-Key': '0000fdae4e9dd10972321d24e30589795f98', 'Yld': '132023936848410570'}
    """
    url = "http://qdall01.baidupcs.com/file/dab80fc0592783edb16fd49a5e810015?bkt=en-26dcfdb4e5ee1a49a33089a16a190b8c383b7e70835fc93886515b0b344607b3967f6b43bed9fec6&fid=2717926781-250528-641249558821162&time=1572533631&sign=FDTAXGERLQBHSKfW-DCb740ccc5511e5e8fedcff06b081203-2NHkczpGDUM0yLGU7x4oGqfubXM%3D&to=34&size=9730818&sta_dx=9730818&sta_cs=82027&sta_ft=mkv&sta_ct=7&sta_mt=7&fm2=MH%2CQingdao%2CAnywhere%2C%2Cheilongjiang%2Ccnc&ctime=1478017640&mtime=1537022354&resv0=cdnback&resv1=0&resv2=&resv3=&resv4=9730818&vuk=2717926781&iv=-2&htype=&randtype=&newver=1&newfm=1&secfm=1&flow_ver=3&pkey=en-4b39fe50e8ac02df3eb62da2fcfda0a1f9d94b50840143f8bda4dc00c043f4eaced09c36491e312e&sl=80740430&expires=8h&rt=pr&r=610572866&vbdid=-&fin=13+-+5+-+Choosing+the+Number+of+Clusters+%288+min%29.mkv&rtype=1&dp-logid=1631313692692286822&dp-callid=0.1&tsl=15&csl=78&csign=7rHoPlXj4i5S0GSHpz5yFNKP3z8%3D&so=1&ut=8&uter=0&serv=1&uc=1559654663&ti=26fa64dbec288224f1c7bf79dbbe7f475d23d57046e6b709305a5e1275657320&reqlabel=250528_f&by=themis"
    """
        {'Connection': 'keep-alive', 'Content-Type': 'text/plain; charset=utf-8', 'Date': 'Thu, 31 Oct 2019 14:55:04 GMT', 'Flow-Level': '3', 'Http-X-Isis-Logid': '1631313692692286822', 'Location': 'http://qdall01.baidupcs.com/file/dab80fc0592783edb16fd49a5e810015?bkt=en-26dcfdb4e5ee1a49a33089a16a190b8c383b7e70835fc93886515b0b344607b3967f6b43bed9fec6&fid=2717926781-250528-641249558821162&time=1572533703&sign=FDTAXGERLQBHSKfW-DCb740ccc5511e5e8fedcff06b081203-tPbrKBo3oDHqV3ssk%2F%2BY83v0rAA%3D&to=34&size=9730818&sta_dx=9730818&sta_cs=82027&sta_ft=mkv&sta_ct=7&sta_mt=7&fm2=MH%2CQingdao%2CAnywhere%2C%2Cheilongjiang%2Ccnc&ctime=1478017640&mtime=1537022354&resv0=cdnback&resv1=0&resv2=&resv3=&resv4=9730818&vuk=2717926781&iv=-2&htype=&randtype=&newver=1&newfm=1&secfm=1&flow_ver=3&pkey=en-4b39fe50e8ac02df3eb62da2fcfda0a1f9d94b50840143f8bda4dc00c043f4eaced09c36491e312e&sl=80740430&expires=8h&rt=pr&r=610572866&vbdid=-&fin=13+-+5+-+Choosing+the+Number+of+Clusters+%288+min%29.mkv&rtype=1&dp-logid=1631313692692286822&dp-callid=0.1&tsl=15&csl=78&csign=7rHoPlXj4i5S0GSHpz5yFNKP3z8%3D&so=1&ut=8&uter=0&serv=1&uc=1559654663&ti=2b2a9b9e504d9ed2290b31716a15b78aa5ea18e1fe3bf950&reqlabel=250528_f&by=themis', 'P3p': 'CP=" OTI DSP COR IVA OUR IND COM "', 'Remote-Ip': 'd.pcs.baidu.com', 'Server': 'nginx', 'Set-Cookie': 'BAIDUID=6395924FAFE609232E82F54E510F4A13:FG=1; expires=Fri, 30-Oct-20 14:55:04 GMT; max-age=31536000; path=/; domain=.baidu.com; version=1', 'X-Bs-Pcs-Extra': 'digest=dab80fc0592783edb16fd49a5e810015&user_id=77767179&visitor_ip=116.136.20.85&method=file&app_id=250528&v_user_id=77767179&file_size=9730818&fs_id=641249558821162&file_type=mkv&freeispflag=-100&user_type=crack_user&user_terminal=def&iv=-2&user_operator=cnc&xflag=', 'X-Bs-Remote-Ip': '10.61.73.16', 'X-Bs-Request-Id': 'eXEwMS1vYmplY3QwMi1yMTAtMDMtMDkwLnlxMDEuYmFpZHUuY29tOjEwLjYxLjczLjE2OjIwMTA6MTYzMTMxMzY5MjY5MjI4NjgyMjoyMDE5LTEwLTMxIDIyOjU1OjAz', 'X-Pcs-Member': '0', 'X-Poms-Key': '0000fdae4e9dd10972321d24e30589795f98', 'Yld': '132043250762953938'}
    """
    url = "http://qdall01.baidupcs.com/file/dab80fc0592783edb16fd49a5e810015?bkt=en-26dcfdb4e5ee1a49a33089a16a190b8c383b7e70835fc93886515b0b344607b3967f6b43bed9fec6&fid=2717926781-250528-641249558821162&time=1572533703&sign=FDTAXGERLQBHSKfW-DCb740ccc5511e5e8fedcff06b081203-tPbrKBo3oDHqV3ssk%2F%2BY83v0rAA%3D&to=34&size=9730818&sta_dx=9730818&sta_cs=82027&sta_ft=mkv&sta_ct=7&sta_mt=7&fm2=MH%2CQingdao%2CAnywhere%2C%2Cheilongjiang%2Ccnc&ctime=1478017640&mtime=1537022354&resv0=cdnback&resv1=0&resv2=&resv3=&resv4=9730818&vuk=2717926781&iv=-2&htype=&randtype=&newver=1&newfm=1&secfm=1&flow_ver=3&pkey=en-4b39fe50e8ac02df3eb62da2fcfda0a1f9d94b50840143f8bda4dc00c043f4eaced09c36491e312e&sl=80740430&expires=8h&rt=pr&r=610572866&vbdid=-&fin=13+-+5+-+Choosing+the+Number+of+Clusters+%288+min%29.mkv&rtype=1&dp-logid=1631313692692286822&dp-callid=0.1&tsl=15&csl=78&csign=7rHoPlXj4i5S0GSHpz5yFNKP3z8%3D&so=1&ut=8&uter=0&serv=1&uc=1559654663&ti=2b2a9b9e504d9ed2290b31716a15b78aa5ea18e1fe3bf950&reqlabel=250528_f&by=themis"
    """
    
    curl -g "https://pan.baidu.com/rest/2.0/xpan/multimedia?method=filemetas&access_token=21.848a539ac5fbae080360ce510d1a2ce0.2592000.1576903339.2717926781-9850001&fsids=[376617852158153]&thumb=0&dlink=1&extra=1" -H "User-Agent: pan.baidu.com"
    curl -L -g "https://d.pcs.baidu.com/file/b89838f4a6fa0bc070dd0965c9f06fd6?fid=2717926781-250528-376617852158153&rt=pr&sign=FDtAER-DCb740ccc5511e5e8fedcff06b081203-6xRWjz4SXMdRydT9SHDroFP8ll8%3D&expires=8h&chkbd=0&chkv=0&dp-logid=4235837805524664497&dp-callid=0&dstime=1574577361&r=208891183&access_token=21.848a539ac5fbae080360ce510d1a2ce0.2592000.1576903339.2717926781-9850001" -H "User-Agent: pan.baidu.com"
    """

    url = "https://d.pcs.baidu.com/file/b89838f4a6fa0bc070dd0965c9f06fd6?fid=3090991555-250528-818025613027874&rt=pr&sign=FDtAER-DCb740ccc5511e5e8fedcff06b081203-uAgKvcQZy62wK0RbdvRetk0f0wI%3D&expires=8h&chkbd=0&chkv=0&dp-logid=3880469753250037717&dp-callid=0&dstime=1574573811&r=559971058&access_token=21.9cdf793f6dd80111a4d9263f525f2586.2592000.1576903342.3090991555-9850001"
    url = "https://d.pcs.baidu.com/file/663fec067c9cf9e9266a09082c81ec00?fid=721132532-250528-827322491135924&rt=pr&sign=FDtAER-DCb740ccc5511e5e8fedcff06b081203-CQdFVJLc%2FsLT34HevItBBJvIv88%3D&expires=8h&chkbd=0&chkv=0&dp-logid=3897204685888635360&dp-callid=0&dstime=1574573974&r=239020143&access_token=21.7d80c6dd344936851435bf6fb99ae07a.2592000.1576903343.721132532-9850001"

    # load_pan_acc("1Q84（全集）.epub")
    url = "https://d.pcs.baidu.com/file/094d0617bfcbc7ed25b0159a621e8009?fid=3090991555-250528-158531883966813&rt=pr&sign=FDtAERV-DCb740ccc5511e5e8fedcff06b081203-veknT6jyEkCB2m95dCyqlVHSmzw%3D&expires=8h&chkbd=0&chkv=2&dp-logid=4060082492992274496&dp-callid=0&dstime=1593172816&r=263495965&access_token=121.87033f1a9b45594adc671f90ab101219.Y37JZ9tujQTiU-Hmhe-pOoRkLB8pjf6VBtlOTPY.R7ap-Q"
    query_file_head(_url)
    """ """
    # _url = "http://qdall01.baidupcs.com/file/c13da89e2993c6945b3c6bdbf3515378?bkt=en-06f5c65000af0ed6091c56bb2ed1af7f2b9aae899ab9bbe07476d89f8050d2f5ff7019d139a04654&fid=2717926781-250528-436166430879136&time=1572579078&sign=FDTAXGERLQBHSKfWa-DCb740ccc5511e5e8fedcff06b081203-CT9Rh9vlBNZZNaSfHm2aR5V8YMI%3D&to=34&size=157388238&sta_dx=157388238&sta_cs=1066&sta_ft=mp4&sta_ct=7&sta_mt=3&fm2=MH%2CYangquan%2CAnywhere%2C%2Cheilongjiang%2Ccnc&ctime=1527591637&mtime=1571452783&resv0=cdnback&resv1=0&resv2=&resv3=&resv4=157388238&vuk=2717926781&iv=-2&htype=&randtype=&newver=1&newfm=1&secfm=1&flow_ver=3&pkey=en-c120475f739ea46fd8e6061e0c03bf24236d23007dbed21a846c244c8d0295435ba1225035cce4ee&sl=80740430&expires=8h&rt=pr&r=352462039&vbdid=-&fin=1.%E8%AF%A6%E8%A7%A3%E6%9D%8E%E7%99%BD%E3%80%8A%E6%B8%A1%E8%8D%86%E9%97%A8%E9%80%81%E5%88%AB%E3%80%8B%E3%80%90%E8%A7%86%E9%A2%91%E5%85%AC%E5%BC%80%E8%AF%BE%E3%80%91.mp4&rtype=1&dp-logid=340225413102246347&dp-callid=0.1&tsl=15&csl=78&csign=7rHoPlXj4i5S0GSHpz5yFNKP3z8%3D&so=1&ut=8&uter=0&serv=1&uc=1559654663&ti=ac918a9d760b19a8067c30781520bbbac129d989f0e1671d&reqlabel=250528_f&by=themis"
    page_cnt = 3
    total = 157388238
    filesize=total//page_cnt  #5590000，文件大小
    # for i in range(page_cnt):
    #     filename="%d.log" % i
    #     flag=downfile(filename,_url,filesize*i,filesize*(i+1), total)

    # index = 2
    # filename = "%d.log" % index
    # if index == page_cnt - 1:
    #     filename = "%d.log" % index
    #     flag = downfile(filename, _url, filesize * index, total, total - filesize * index)
    # elif index < page_cnt -1:
    #     filename = "%d.log" % index
    #     flag = downfile(filename, _url, filesize * index, filesize*(index+1), filesize)

    # print(os.urandom(32))
    # random_password(4)



