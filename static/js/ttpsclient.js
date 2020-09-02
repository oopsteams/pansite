function psclient(app, saver) {
    //var window = app;
    //window.pushclient = null;
    var SocketTask = null;
    var that = app;
    var IPClinet = {
        createNew: function () {
        }
    };
    var IPRequest = {
        createNew: function () {
        }
    };
    var IPResponse = {
        createNew: function () {
        }
    };
    var IPSaver = {
        createNew: function () {
        }
    };
    var Kind = {'INT': 0, 'LONG': 1, 'STRING': 2, 'BYTE': 3, 'ACK': 4};
    app.Kind = Kind;
    var Msg = {
        createNew: function (wsclient) {
            var msg = {};
            msg.wsclient = wsclient;
            msg.send = function (tag, kind, val) {
                tag = tag % 10;
                kind = kind % 10;
                //console.log("will send:",val);
                msg.tosend('' + tag + kind + val);


                //return tag+kind+val;
            };
            msg.sendbytes = function (msg) {
                /*
                var sn = (new Date()).getTime();
                var _msg = new Uint8Array(msg.length+2);
                _msg.set([''+tag,''+kind],0);
                _msg.set(msg,3);
                */
                //this.tosend(new Blob(msg,{type:"application/octet-binary"}));
                this.tosend(msg.buffer);
            };
            msg.unmarshal = function (val) {
                if (typeof val === 'string') {
                    val = '' + val;
                    var tag = parseInt(val.substring(0, 1));
                    var kind = parseInt(val.substring(1, 2));
                    var _val = val.substring(2);
                } else {
                    var tag = val[0];

                    var kind = val[1];
                    var _val = val.slice(2, -1);
                }
                return [tag, kind, _val];
            };
            msg.tosend = function (data) {
                if (!data || data.length == 0) return;
                try {
                    msg.wsclient.writeflush(data, false);
                } catch (e) {
                    console.log('tosend err:' + e);
                }
            };
            return msg;
        }
    };
    var WSClient = {
        createNew: function (pclient) {
            var client = {};
            client.threshold = 512;
            client.pclient = pclient;
            client.connecting = false;
            client.running = false;
            client.isconnected = false;
            client.waitreply = false;

            client.connectRetry = 0;
            client.timestamp = 0;
            client.checktimeout = 10000;
            client.lastcheck = 0;
            client.host = pclient.request.host;
            client.port = pclient.request.port;
            client.fixport = pclient.request.fixport;
            client.readers = [];
            client.cache = [];
            client.timer = null;
            client.delay = 50;
            client.proxy = pclient.request.proxy;
            client.monitorrunner = function () {
                if (client.waitreply) {
                    client.isconnected = false;
                }
                //console.log('monitorrunner in.');
                client.checkRemote();
            };
            client.getBlobReader = function () {
                for (var i = 0; i < this.readers.length; i++) {
                    var r = this.readers[i];
                    console.log("check reader index:" + i);
                    if (r.pin == 0) {
                        r.pin = 1;
                        r.rs = null;
                        return r;
                    }
                }
                var _r = {"pin": 1, "fr": new FileReader(), "cb": null};
                _r.fr.p = _r;
                _r.fr.onload = function (evt) {
                    if (evt.target.readyState == FileReader.DONE) {
                        this.p.pin = 0;
                        if (this.p.cb) this.p.cb(new Uint8Array(this.result));
                    }
                };
                this.readers[this.readers.length] = _r;
                return _r;
            };
            client.blobToArray = function (b, cb) {
                var r = client.getBlobReader();
                if (r) {
                    r.cb = cb;
                    r.fr.readAsArrayBuffer(b);
                }
            };
            client.authorize = function () {
                client.pclient.request.authorize();
            };
            client.onclose = function (evt) {
                console.log('DISCONNECTED.evt:');
                console.log(evt);
                client.isconnected = false;
            };
            client.onmessage = function (evt) {
                if (evt) {
                    // console.log('onmessage evt:');
                    // console.log(evt);

                    if (evt.data) {
                        if (typeof evt.data === 'string') {
                            var datas = client.msgbody.unmarshal(evt.data);
                            client.pclient.response.receive(datas[0], datas[1], datas[2]);
                        } else {
                            // console.log(evt.data);
                            // for (var k in evt.data) {
                            //   console.log(k + ":" + evt.data[k]);
                            // }
                            this.blobToArray(evt.data, function (ab) {
                                var datas = client.msgbody.unmarshal(ab);
                                console.log("blob tag:" + datas[0] + ",byte kind:" + datas[1]);
                                client.pclient.response.receive(datas[0], datas[1], datas[2]);
                            });


                        }

                    }
                }

            };
            client.onerror = function (evt) {
                console.log('CONNECT ERR.等待重连.');
                client.isconnected = false;
                client.connecting = false;
            };
            client.onopen = function (evt) {
                client.waitreply = false;
                client.connecting = false;
                client.connectRetry = 0;
                client.isconnected = true;
                console.log('CONNECTED.');
                client.authorize();
            };
            client.changeAddress = function (host, port) {
                // client.host = host;
                client.port = port;
                pclient.request.add("auth", "1");
                console.log("changeAddress host:" + host + ",port:" + port);
                client.connect();
            };
            client.connect = function () {
                if (client.connecting) return;
                client.connecting = true;
                client.waitreply = true;
                this.close();
                client.connectRetry += 1;
                client.timestamp = (new Date()).getTime();

                try {
                    //var wsUri=client.proxy+"://"+client.host+":"+client.port+"/?enoding=text";

                    var wsUri = client.proxy + "://" + client.host + ":" + client.fixport + (client.port > 0 ? "/?" + client.port : "/");
                    // var wsUri = client.proxy + "://" + client.host + (client.port > 0 ? "/ws/?" + client.port : "");
                    console.log('wsUri:' + wsUri);
                    SocketTask = tt.connectSocket({'url': wsUri});
                    SocketTask.onOpen(function (res) {
                        client.onopen(res);
                    });
                    SocketTask.onError(function (res) {
                        client.onerror(res);
                        client.isconnected = false;
                    });
                    SocketTask.onMessage(function (data) {
                        client.onmessage(data);
                    })
                    SocketTask.onClose(function (res) {
                        client.onclose(res);
                    })
                    //client.wsocket.binaryType = "arraybuffer";

                } catch (e) {
                    console.log(e);
                    client.isconnected = false;
                }
            };
            client.close = function () {
                if (SocketTask) {
                    SocketTask.close();
                }
            };
            client.checkRemote = function () {
                var ct = (new Date()).getTime();
                try {
                    //console.log('ct-client.lastcheck:'+(ct-client.lastcheck));
                    //console.log('ct:'+ct);
                    //console.log('client.lastcheck:'+client.lastcheck);
                    //console.log('client.checktimeout:'+client.checktimeout);
                    if (ct - client.lastcheck > client.checktimeout - 1) {
                        if (client.isconnected && client.running) {
                            client.writeflush(null, true);
                            client.pclient.response.heart(client.connectRetry);
                            return true;
                        }
                    }
                } catch (e) {
                    client.isconnected = false;
                }
                if (client.running && !client.isconnected) {
                    if (client.connectRetry > 0) {
                        var time = client.connectRetry > 6 ? 6 : client.connectRetry;
                        if (ct - client.timestamp > client.checktimeout * time) {
                            client.connect();
                            client.pclient.response.heart(client.connectRetry);
                        }
                    } else {
                        client.connect();
                        client.pclient.response.heart(client.connectRetry);
                    }


                }
                return false;
            };
            client.tostart = function () {

                client.msgbody = Msg.createNew(client);
                client.pclient.ready();
                client.startrunner();
            };
            var runnable = function () {
                if (client.monitor) {
                    clearTimeout(client.monitor);
                }
                client.monitorrunner();
                if (client.running) {
                    client.monitor = setTimeout(runnable, 15000);
                } else {
                    client.release();
                }
            };
            client.startrunner = function () {
                if (!client.running) {
                    client.running = true;
                    client.connect();
                    client.monitor = setTimeout(runnable, 15000);
                }

            };
            client.shutdown = function () {
                client.running = false;
            };
            client.release = function () {
                client.close();
            };
            client.startsend = function () {

                if (client.cache && client.cache.length > 0) {
                    if (client.isconnected) {
                        var fdata = client.cache[0];

                        try {
                            //				                console.log(typeof(fdata.data));
                            //				                console.log(fdata.type);
                            //				                console.log(fdata);

                            var params = {};
                            if (typeof (fdata) == "string") {
                                params['data'] = fdata;
                            } else {
                                console.log(client.cache);
                                params['data'] = fdata;
                            }
                            params['data'] = fdata;
                            params['complete'] = function () {
                                client.lastcheck = (new Date()).getTime();
                                client.delay = 1;
                                client.cache.splice(0, 1);

                                if (client.cache && client.cache.length > 0) {
                                    setTimeout(function () {
                                        client.startsend()
                                    }, 1);
                                } else {
                                    //console.log('not find any cache.');
                                    if (client.timer) {
                                        clearTimeout(client.timer);
                                        client.timer = null;
                                        console.log('not find andy cache,close timer.');
                                        setTimeout(function () {
                                            client.startsend()
                                        }, client.delay * 10);
                                    } else {
                                        // console.log('client timer not exist,send over.');
                                    }
                                }

                            };
                            if (SocketTask) {
                                SocketTask.send(params);
                            }

                            //console.log("send one data end.");
                        } catch (e) {
                            console.log('writeflush err,' + e);
                            client.isconnected = false;
                            //throw e;
                        }

                    }

                }
                //console.log("ready check cache .");


            };
            client.writeflush = function (data, isheart) {
                if (client.isconnected) {
                    var isEmpty = (client.cache.length == 0);
                    if (isheart) {
                        if (!client.cache || client.cache.length == 0) {
                            client.cache[client.cache.length] = '12';//{'data':'12','type':'string'};
                        }
                    } else {
                        client.cache[client.cache.length] = data;//{'data':data,'type':'binary'};
                    }
                    if (isEmpty) {
                        //if(!client.timer)client.timer = window.setTimeout(function(){client.startsend()},client.delay);
                        client.startsend();
                    }
                }
            };
            client.willreconnect = function () {
                client.isconnected = false;
            };
            return client;
        }
    };
    var PClient = {
        createNew: function () {
            var pclient = {};
            var byte_cache = null;
            var cache_timer = null;
            var cache_loop_send_max = 9;
            var cache_loop_send_cnt = 0;
            pclient.request = {

                'params': {},
                'add': function (key, val) {
                    pclient.request.params[key] = val;
                    if ("sids" == key) {
                        var sids = val.split(",");
                        if (sids.length > 0) pclient.request.defaultSid = sids[0];
                    } else if ("vids" == key) {
                        var vids = val.split(",");
                        if (vids.length > 0) pclient.request.defaultGid = vids[0];
                    }
                },
                'authorizeInfo': function () {
                    var pms = '';
                    if (pclient.request.params) {
                        for (var key in pclient.request.params) {
                            pms += "&" + key + "=" + pclient.request.params[key];
                        }
                    }
                    var info = "tk=" + pclient.request.token + "&hc=" + pclient.request.uuid + "&uid=" + pclient.request.uuid + pms;
                    return info;
                },
                'authorize': function () {
                    var ainfo = pclient.request.authorizeInfo();
                    console.log('authorize in.ainfo:', ainfo);
                    pclient.request.msgbody.send(0, 2, ainfo);
                },

                'syncparams': function () {
                    console.log('syncparams in.');
                    pclient.request.msgbody.send(0, 4, pclient.request.authorizeInfo());
                },
                'apply': function (page, sn) {
                    cache_loop_send_cnt = 0;
                    console.log("apply function ,page:" + page + ",sn:" + sn);
                    if (byte_cache && byte_cache[sn]) {
                        if (page in byte_cache[sn]) {
                            delete byte_cache[sn][page];
                        }
                        var find = false;
                        for (var k in byte_cache[sn]) {
                            find = true;
                            break;
                        }
                        if (!find) {
                            delete byte_cache[sn]
                            byte_cache = null;
                            pclient.response.onidle();
                        } else {
                            if (cache_timer) {
                                clearTimeout(cache_timer);
                            }
                            pclient.request.startsendtimer();
                        }
                    } else {
                        pclient.response.onidle();
                    }
                },
                'startsendtimer': function () {
                    if (cache_timer) {
                        clearTimeout(cache_timer);
                    }
                    if (byte_cache) {
                        for (var sn in byte_cache) {
                            for (var page in byte_cache[sn]) {
                                var cacheobj = byte_cache[sn][page];
                                //console.log(cacheobj.data);
                                var ct = (new Date()).getTime();
                                if (!cacheobj.time) {
                                    console.log("send timer will send bytes page[" + page + "] body:" + cacheobj.data.length);
                                    cacheobj.time = ct;
                                    pclient.request.msgbody.sendbytes(cacheobj.data);
                                } else {
                                    if (ct - cacheobj.time > 60000) {
                                        cacheobj.time = ct;
                                        console.log("send timer will resend bytes page[" + page + "] body:" + cacheobj.data.length);
                                        pclient.request.msgbody.sendbytes(cacheobj.data);
                                    }
                                }

                                break;
                            }
                            break;
                        }
                        cache_loop_send_cnt++;
                        if (cache_loop_send_cnt < cache_loop_send_max) {
                            cache_timer = setTimeout(pclient.request.startsendtimer, 30000);
                        } else {
                            byte_cache = null;
                            cache_timer = null;
                            pclient.response.onidle();
                        }

                    } else {
                        cache_timer = null;
                        pclient.response.onidle();
                    }

                },
                'nsend': function (tm, sid, vid, routeid, touid, method, val) {
                    var fromuid = pclient.request.defaultSid + "_" + pclient.request.defaultGid + "_" + pclient.request.uuid;
                    var _touid = ("" + touid).split("_");
                    var target = "" + touid;
                    if (_touid.length < 3) {
                        target = sid + "_" + vid + "_" + touid;
                    }
                    var tag = 2;
                    var kind = Kind.STRING;
                    pclient.request.msgbody.send(tag, kind, "#" + tm + ":" + sid + ":" + vid + ":" + routeid + ":" + fromuid + ":" + target + ":" + method + ":#" + val);
                },
                'send': function (sid, vid, routeid, touid, method, val) {
                    pclient.request.nsend(0, sid, vid, routeid, touid, method, val);
                },
                'recvOk': function (key) {
                    var touid = pclient.request.uuid;
                    if (!key) key = "";
                    var tag = 5;
                    var kind = Kind.STRING;
                    pclient.request.msgbody.send(tag, kind, key);
                },
                'nsendbytes': function (tm, sid, vid, routeid, touid, method, type, msg, sync) {
                    if (sync) {
                        if (byte_cache) {
                            console.log("正在同步上一次未发送完的二进制数据!");
                            return;
                        } else {
                            byte_cache = {};
                        }
                    }
                    var fromuid = pclient.request.defaultSid + "_" + pclient.request.defaultGid + "_" + pclient.request.uuid;
                    var _touid = ("" + touid).split("_");
                    var target = "" + touid;
                    if (_touid.length < 3) {
                        target = sid + "_" + vid + "_" + touid;
                    }
                    var tag = 2;
                    var kind = Kind.BYTE;
                    var sn = "" + (new Date()).getTime();
                    if (sync) byte_cache[sn] = [];
                    var _msg = new Uint8Array(msg.buffer);

                    var size = 81920;
                    console.log("msg len:" + msg.length + ",_msg len:" + _msg.length + ",size:" + size);
                    var page = ~~(_msg.length / size);
                    if (page * size < _msg.length) page += 1;
                    if (page == 1) {
                        var uint_head = [tag, kind];
                        var pstr = "#" + tm + ":" + sid + ":" + vid + ":" + routeid + ":" + fromuid + ":" + target + ":" + method + ":" + type + ":" + "0" + ":" + sn + ":#";
                        for (var i = 0; i < pstr.length; i++) {
                            uint_head[uint_head.length] = pstr.charCodeAt(i);
                        }
                        var head = new Uint8Array(uint_head);
                        var body = new Uint8Array(head.length + _msg.length);
                        body.set(head);
                        body.set(_msg, head.length);
                        console.log("will send bytes body:" + body.length);
                        if (sync) {
                            byte_cache[sn][0] = {"data": body};
                        } else {
                            pclient.request.msgbody.sendbytes(body);
                        }
                    } else {
                        for (var i = 0; i < page; i++) {
                            var spos = i * size;
                            var epos = (i + 1) * size;
                            if (epos > _msg.length) epos = _msg.length;

                            var uint_head = [tag, kind];
                            var pstr = "#" + tm + ":" + sid + ":" + vid + ":" + routeid + ":" + fromuid + ":" + target + ":" + method + ":" + type + ":" + i + ":" + sn + ":#";
                            for (var j = 0; j < pstr.length; j++) {
                                uint_head[uint_head.length] = pstr.charCodeAt(j);
                            }
                            var head = new Uint8Array(uint_head);
                            var body = new Uint8Array(head.length + epos - spos);
                            body.set(head);
                            body.set(_msg.slice(spos, epos), head.length);
                            if (sync) {
                                console.log("will add page[" + i + "] bytes body to cache,body size:" + body.length);
                                byte_cache[sn][i] = {"data": body};
                            } else {
                                console.log("will send bytes page[" + i + "] body:" + body.length);
                                pclient.request.msgbody.sendbytes(body);
                            }
                            //break;
                        }
                    }
                    var uint_head = [tag, kind];
                    var pstr = "#" + tm + ":" + sid + ":" + vid + ":" + routeid + ":" + fromuid + ":" + target + ":" + method + ":" + type + ":" + page + ":" + sn + ":";
                    for (var j = 0; j < pstr.length; j++) {
                        uint_head[uint_head.length] = pstr.charCodeAt(j);
                    }
                    var head = new Uint8Array(uint_head);


                    if (sync) {
                        byte_cache[sn][page] = {"data": head};
                        pclient.request.startsendtimer();
                    } else {
                        console.log("will send bytes body last page head:" + head.length + ",last page:" + page);
                        pclient.request.msgbody.sendbytes(head);
                    }
                },
                'sendbytes': function (sid, vid, routeid, touid, method, type, msg, sync) {
                    pclient.request.nsendbytes(0, sid, vid, routeid, touid, method, type, msg, sync);
                }
            };
            pclient.request.defaultSid = null;
            pclient.request.defaultGid = null;
            pclient.request.host = '127.0.0.1';
            pclient.request.port = 19999;
            pclient.request.proxy = "ws";
            pclient.response = {
                'heart': function (retry) {
                    if (retry > 0) console.log('retry:' + retry);
                },
                'onmessage': function (msg) {
                },
                'onready': function () {
                },
                'sendOver': function (msg, head) {
                    console.log("sendOver msg:", msg, head);
                },
                'onidle': function () {
                },
                'receive': function (tag, kind, val) {//tag,1:注册回应,2:来自服务端的消息
                    if (tag == 1) {
                        switch (kind) {
                            case Kind.INT:
                                var v = parseInt(val);
                                if (v == 3) {
                                    this.debug("Receiver 提供的注册信息异常，不能通过PushService注册验证!");
                                    pclient.wsclient.onerror();
                                } else if (v == 1) {
                                    this.debug("PushService 不能为Receiver 提供有效的推送服务器地址，请等待!");
                                    this.delaycall(function () {
                                        pushclient.pclient.request.authorize();
                                    }, 20000);
                                } else if (v == 2) {
                                    // console.log('heart ok,' + (new Date()));
                                }

                                break;
                            case Kind.STRING:
                                console.log('kind 2:' + val);
                                var vals = val.split(":");
                                var ip = vals[0];
                                var port = parseInt(vals[1]);
                                var uuid = pclient.request.uuid;
                                if (vals.length > 2) {
                                    pclient.request.uuid = vals[2];
                                }
                                console.log('ip:' + ip + ',port:' + port);
                                pclient.changeAddress(ip, port);
                                break;
                        }
                    } else if (tag == 2) {
                        if (kind == Kind.STRING) {
                            var _val = this.parsemsg(val);
                            //console.log("tag:2,STRING,val:" + val);
                            var pos = parseInt(_val[_val.length - 1]);
                            //if(_val.length>4){this.onmessage(Kind.STRING,val);}
                            //console.log("string pos:" + pos);
                            if (pos > 0 && pos < val.length) {
                                this.onmessage(Kind.STRING, val.substring(pos), _val);
                            }
                        } else if (kind = Kind.BYTE) {
                            //console.log("tag:2,BYTE,val:"+val);
                            var _byteVal = this.parseArrmsg(val);
                            var fuid = _byteVal[0];
                            var type = _byteVal[1];
                            var page = _byteVal[2];
                            var sn = _byteVal[3];
                            console.log("fuid:" + fuid + ",type:" + type + ",page:" + page + ",sn:" + sn);
                            var data = null;
                            var pos = parseInt(_byteVal[_byteVal.length - 1]);
                            console.log("byte pos:" + pos);
                            if (pos > 0 && pos < val.length) {
                                data = val.slice(pos);//_byteVal[4];
                                //if(data.length==0)data = null;
                            }
                            this.onmessage(Kind.BYTE, data, [fuid, type, page, sn]);
                        }
                    } else if (tag == 5) {
                        var _val = this.parsemsg(val);
                        var pos = parseInt(_val[_val.length - 1]);
                        this.sendOver(val.substring(pos), _val)
                        //console.log("_val:",_val);
                    } else {
                        if (tag == 0 && kind == Kind.INT && parseInt(val) == 0) {
                            console.log("可以收发消息了");
                            this.onready();
                        }
                        //console.log("tag:" + tag + ",kind:" + kind + ",val:" + val);
                    }
                },
                'delaycall': function (func, timeout) {
                    if (timeout < 10) timeout = 10;
                    var timer = setTimeout(function () {
                        func();
                        clearTimeout(timer);
                    }, timeout);
                },
                'parsemsg': function (msg) {
                    if (!msg) return null;
                    var l = msg.length;
                    var rspos = 0;
                    var cnt = 6;
                    var pos = 0;
                    var lastpos = 0;
                    var rs = [];
                    var stopc = '#';
                    while (rspos < cnt - 1 && pos < l) {
                        if (msg.charAt(pos) == stopc) {
                            if (lastpos < pos) {
                                rs[rspos] = msg.substring(lastpos, pos);
                                lastpos = pos + 1;
                            }
                            pos++;
                            break;
                        } else if (msg.charAt(pos) == ':') {
                            rs[rspos] = msg.substring(lastpos, pos);
                            lastpos = pos + 1;
                            rspos++;
                            if (pos + 1 < l && msg.charAt(pos + 1) == stopc) {
                                pos += 2;
                                break;
                            }
                        }
                        pos++;
                    }
                    //if(rspos==cnt-1){
                    //	rs[rspos]=msg.substring(pos);
                    //}
                    rs[rs.length] = pos;
                    return rs;
                },
                'parseArrmsg': function (msg) {
                    if (!msg) return null;
                    var l = msg.length;
                    var rspos = 0;
                    var cnt = 5;
                    var pos = 0;
                    var lastpos = 0;
                    var rs = [];
                    var stopc = 35;
                    while (rspos < cnt - 1 && pos < l) {
                        if (msg[pos] == stopc) {
                            if (lastpos < pos) {
                                rs[rspos] = '';
                                for (var i = lastpos; i < pos; i++) {
                                    rs[rspos] += String.fromCharCode(msg[i]);
                                }
                                lastpos = pos + 1;
                            }
                            pos++;
                            break;
                        } else if (msg[pos] == 58) {
                            rs[rspos] = '';
                            for (var i = lastpos; i < pos; i++) {
                                rs[rspos] += String.fromCharCode(msg[i]);
                            }
                            lastpos = pos + 1;
                            rspos++;
                            if (pos + 1 < l && msg[pos + 1] == stopc) {
                                pos += 2;
                                break;
                            }
                        }
                        pos++;
                    }
                    //if(rspos==cnt-1){
                    //    rs[rspos]=msg.slice(pos);
                    //}
                    rs[rs.length] = pos;
                    return rs;
                },
                'debug': function (msg, e) {
                    if (e) {
                        msg = msg + "," + e;
                    }
                    console.log(msg);
                }
            };
            pclient.running = false;
            pclient.start = function () {
                if (pclient.running) return;
                pclient.running = true;
                if (!pclient.wsclient) {
                    pclient.wsclient = WSClient.createNew(pclient);
                }
                if (pclient.wsclient) {
                    pclient.wsclient.tostart();
                }
            };
            pclient.changeAddress = function (host, port) {
                if (pclient.wsclient) {
                    pclient.wsclient.changeAddress(host, port);
                }
            };
            pclient.shutdown = function () {
                pclient.running = false;
                if (pclient.wsclient) {
                    pclient.wsclient.shutdown();
                }
            };
            pclient.ready = function () {
                pclient.request.msgbody = pclient.wsclient.msgbody;
            };
            pclient.tryrestart = function () {
                pclient.wsclient.willreconnect();
            };
            return pclient;
        }
    };
    var pclient = PClient.createNew();
    app.pushclient = {
        'pclient': pclient,
        'saver': saver
    };
    that.pushclient = app.pushclient;
}

function start(app, _client, pushclient, gid) {
    var window = app;
    var that = app;
    if (!_client) return;
    if (!pushclient)
        pushclient = that.pushclient;
    var cache = {};
    var cache_size = 2 * 1024 * 1024;
    var audioContext = null;
    try {
        audioContext = new AudioContext();
    } catch (e) {
        console.log(e);
    }
    //navigator.getUserMedia = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia || navigator.msGetUserMedia;
    console.log('pushclient:', pushclient);
    pushclient.pclient.response.onready = function () {
        // that.updateClientSt(1);
    };
    var Kind = {'INT': 0, 'LONG': 1, 'STRING': 2, 'BYTE': 3, 'ACK': 4};
    pushclient.pclient.response.onmessage = function (kind, msg, params) {

        if (kind == Kind.STRING) {

            var idx = msg.indexOf(":");
            var tag = "";
            if (idx > 0) tag = msg.substring(0, idx);
            var _idx = idx;
            idx = msg.indexOf(":", _idx + 1);
            var sn = "";
            if (idx > _idx) {
                sn = msg.substring(_idx + 1, idx);
                if (sn) {
                    pushclient.pclient.request.recvOk(sn);
                }
            }
            var submsg = msg.substring(idx + 1);
            var vals = msg.split(":");

            if ("apply" == tag) {
                var _from = params[0];
                window.fromuid = _from;
                var page = ~~sn;
                var sn = submsg;
                pushclient.pclient.request.apply(page, sn);
            } else if ("msg" == tag) {
                var _from = params[0];
                window.fromuid = _from;
                var txt = submsg;
                //console.log("来自" + _from + "[" + sn + "]:" + txt);
                if (typeof pushclient.pclient.cb == "function") {
                    pushclient.pclient.cb('recv', _from, sn, txt);
                }
            }
        }
    };
    pushclient.pclient.cb = function (msg, head) {
    };
    //window.fromuid = 6001;
    //pushclient.pclient.request.host='127.0.0.1';
    //pushclient.pclient.request.host='172.16.24.41';
    pushclient.pclient.request.host = 'wss.oopsteam.site'
    //pushclient.pclient.request.port=19999;
    //pushclient.pclient.request.port=19009;
    pushclient.pclient.request.port = 19443;
    pushclient.pclient.request.fixport = 19443;
    pushclient.pclient.request.token = 'TYL001';
    //pushclient.pclient.request.uuid='';
    // pushclient.pclient.request.uuid = '36801';
    //pushclient.pclient.request.uuid = _client.id;
    pushclient.pclient.request.uuid = 999;
    pushclient.pclient.request.proxy = "wss";
    pushclient.pclient.request.add('sids', '1');
    pushclient.pclient.request.add('vids', '' + gid);
    pushclient.pclient.start();
    pushclient.pclient.inited = true;
    pushclient.pclient.response.sendOver = function (msg, head) {
        //console.log("sendOver msg:", msg);
        //console.log("sendOver head:", head);
        //console.log("pushclient.pclient.cb:",typeof pushclient.pclient.cb);
        var vals = msg.split(":");
        var st = vals[0];
        var sn = "";
        if ("0" == st) {
            sn = vals[1];
        }
        if (typeof pushclient.pclient.cb == "function") {
            var _from = head[0];
            pushclient.pclient.cb('over', _from, sn, st);
        }
    };
    pushclient.pclient.response.onready = function () {
        if (typeof app.onready == "function") {
            app.onready();
        }
        if (typeof pushclient.pclient.cb == "function") {

            pushclient.pclient.cb('ready', 0, null, 0);
        }
    };
}

function sendText(pushclient, txt, touid, cb) {
    var sid = pushclient.pclient.request.defaultSid;
    var vid = pushclient.pclient.request.defaultGid;
    var routeid = 2;
    var md = "dhbyuid";
    if (!touid) {
        md = "downhit";
        touid = vid;
    }
    var sn = "" + (new Date()).getTime();

    setCallBack(pushclient, cb);
    pushclient.pclient.request.nsend(10, sid, vid, routeid, touid, md, "msg:" + sn + ":" + txt);
    return sn;
}

function setCallBack(pushclient, cb) {
    if (pushclient && pushclient.pclient) {
        pushclient.pclient.cb = cb;
    }
    //console.log("setCallBack end,pushclient.pclient.cb:", pushclient.pclient.cb);
}

module.exports.psclient = psclient;
module.exports.start = start;
module.exports.sendText = sendText;
module.exports.setCallBack = setCallBack;