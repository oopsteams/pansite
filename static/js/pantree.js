// let pan_id = '{{pan_id}}';
let dialog = null,form_dialog = null, dist_form_dialog = null, rename_form_dialog = null;
function refresh_jstree(node_id){
    let inst = $.jstree.reference(node_id);
    let node = inst.get_node(node_id);
    let parent_node_id = inst.get_parent(node);
    let parent_node = null;
    if(parent_node_id){
        parent_node = inst.get_node(parent_node_id);
    }
    setTimeout(function () {
        if(parent_node){
            inst.refresh(parent_node);
        } else {
            alert('refresh all!!!');
            inst.refresh();
        }
    }, 800);
}

$('#tree').jstree({
    'core' : {
        'data' : {
            "url" : "fload?lazy&tk="+GetQueryString('tk'),
            "data" : function (node) {
                console.log("lazy node:", node);
                let p = "/";
                let _params = { "id" : node.id, "path": p }
                if(node.data){
                    $.extend(_params, node.data)
                }
                return _params;
            }
        },
        'themes' : {
            'responsive' : false,
            'variant' : 'small',
            'stripes' : true
        }
    },
    "contextmenu":{
        'items': function (node) {
            let ctxmenu = $.jstree.defaults.contextmenu.items();
            delete ctxmenu.ccp;
            delete ctxmenu.remove;
            delete ctxmenu.rename;
            delete ctxmenu.create;
            if (node.data.isdir === 1) {
                if (node.data.source === 'local' && node.data.path !== "/") {
                    if (!node.data['isp']) {
                        ctxmenu.product = {
                            'separator_after': true,
                            'separator_before': true,
                            'label': '标记为商品',
                            'action': function (data) {
                                form_dialog.dialog("open");
                                let inst = $.jstree.reference(data.reference),
                                    node = inst.get_node(data.reference);
                                $('#p_name').val(node.text);
                                $('#p_price').val(node.data['price']);
                                $('#isdir').val(node.data['isdir']);
                                $('#itemid').val(node.data._id);
                                form_dialog.ctx = {"inst": inst, "node": node};
                                //
                                // dialog.dialog( "open" );
                                // let inst = $.jstree.reference(data.reference),
                                //     node = inst.get_node(data.reference);
                                // let params = {tk: GetQueryString('tk'), recursion: 1, 'panid': pan_id, 'id': node.id};
                                // call_service_by_get('/product/tag', params, function (res) {
                                //     let result = res['result'];
                                //     console.log('res result:', result);
                                //     inst.refresh(node);
                                //     dialog.dialog( "close" );
                                // });
                                //
                            }
                        };
                    } else {
                        ctxmenu.untag = {
                            'separator_after': true,
                            'separator_before': true,
                            'label': '取消商品标记',
                            'action': function (data) {
                                let inst = $.jstree.reference(data.reference),
                                    node = inst.get_node(data.reference);
                                let params = {tk: GetQueryString('tk'), 'itemid': node.data._id};
                                dialog.dialog("open");
                                call_service('/product/untag', params, function (res) {
                                    setTimeout(() => {
                                        inst.refresh(node);
                                        dialog.dialog("close");
                                    }, 5000)
                                });
                            }
                        };
                        ctxmenu.distribute = {
                            'separator_after': true,
                            'separator_before': true,
                            'label': '商品卖给用户',
                            'action': function (data) {
                                dist_form_dialog.dialog("open");
                                let inst = $.jstree.reference(data.reference),
                                    node = inst.get_node(data.reference);
                                $('#pro_name').html(node.text);
                                // $('#p_price').val(node.data['price']);
                                // $('#isdir').val(node.data['isdir']);
                                $('#pro_itemid').val(node.data._id);
                                dist_form_dialog.ctx = {"inst": inst, "node": node};
                            }
                        };
                    }
                }
            }
            ctxmenu.clear = {
                'separator_after': false,
                'separator_before': false,
                'label': '清除',
                'action': function (data) {
                    let inst = $.jstree.reference(data.reference),
                        node = inst.get_node(data.reference);
                    let confirm_val = prompt("确认要清除[" + node.text + "]吗?确认请输入DELETE.", "");
                    if ("DELETE" === confirm_val) {
                        dialog.dialog("open");
                        let params = {
                            tk: GetQueryString('tk'),
                            'panid': node.data.sourceid,
                            'id': node.data._id,
                            'source': node.data.source
                        };
                        console.log('clear dir:', params);
                        call_service_by_get('/man/clear', params, function (res) {
                            let st = res['state'];
                            if (st === 0) {
                                inst = $.jstree.reference(data.reference);
                                node = inst.get_node(data.reference);
                                inst.delete_node(node);
                                refresh_jstree(data.reference);
                                dialog.dialog("close");
                            }
                        });
                    }
                }
            };
            if (node.data.source === 'local') {
                ctxmenu.rename = {
                    'separator_after': false,
                    'separator_before': false,
                    'label': '重命名',
                    'action': function (data) {
                        let inst = $.jstree.reference(data.reference), node = inst.get_node(data.reference);
                        rename_form_dialog.dialog("open");
                        $('#old_name').val(node.data.fn);
                        $('#alias_name').val(node.data.alias);
                        $('#rename_itemid').val(node.data._id);
                        $('#rename_source').val(node.data.source);
                        rename_form_dialog.ctx = {"inst": inst, "node": node};
                    }
                };
            }
            if (node.data.isdir === 0) {

            }
            if (node.data.isdir === 1) {
                if (node.data.source === 'local') {
                    ctxmenu.sync = {
                        'separator_after': false,
                        'separator_before': false,
                        'label': '同步目录',
                        'action': function (data) {
                            dialog.dialog("open");
                            let inst = $.jstree.reference(data.reference),
                                node = inst.get_node(data.reference);
                            let params = {
                                tk: GetQueryString('tk'),
                                recursion: 0,
                                'panid': node.data.sourceid,
                                'id': node.data._id
                            };
                            call_service_by_get('/source/syncallnodes', params, function (res) {
                                let result = res['result'];
                                console.log('res result:', result);
                                check_state(node.data.sourceid, function (ok) {
                                    inst.refresh(node);
                                    dialog.dialog("close");
                                });
                            });

                        }
                    };

                }
                if (node.data.path !== '/') {
                    if (node.data.source === 'local') {
                        ctxmenu.syncall = {
                            'separator_after': false,
                            'separator_before': false,
                            'label': '同步所有',
                            'action': function (data) {
                                dialog.dialog("open");
                                let inst = $.jstree.reference(data.reference),
                                    node = inst.get_node(data.reference);
                                let params = {
                                    tk: GetQueryString('tk'),
                                    recursion: 1,
                                    'panid': node.data.sourceid,
                                    'id': node.data._id
                                };
                                call_service_by_get('/source/syncallnodes', params, function (res) {
                                    let result = res['result'];
                                    console.log('res result:', result);
                                    check_state(node.data.sourceid, function (ok) {
                                        inst.refresh(node);
                                        dialog.dialog("close");
                                    });
                                });

                            }
                        };
                    }
                    ctxmenu.sub_dir_show = {
                        'separator_after': false,
                        'separator_before': true,
                        'label': '标记子目录搜索可见',
                        'action': function (data) {
                            dialog.dialog("open");
                            // console.log('isvisible data:', data);
                            let inst = $.jstree.reference(data.reference),
                                node = inst.get_node(data.reference);
                            let params = {
                                tk: GetQueryString('tk'),
                                recursion: 1,
                                'panid': node.data.sourceid,
                                'id': node.id,
                                'parent': node.data.p_id,
                                'source': node.data.source
                            };
                            let url = '/man/show';
                            call_service_by_get(url, params, function (res) {
                                setTimeout(() => {
                                    inst.refresh(node);
                                    dialog.dialog("close");
                                }, 5000)

                            });
                        }
                    };
                    ctxmenu.sub_dir_hide = {
                        'separator_after': false,
                        'separator_before': false,
                        'label': '标记子目录搜索隐藏',
                        'action': function (data) {
                            dialog.dialog("open");
                            let inst = $.jstree.reference(data.reference),
                                node = inst.get_node(data.reference);
                            // console.log('sub_dir_hide node:', node);
                            let params = {
                                tk: GetQueryString('tk'),
                                recursion: 1,
                                'panid': node.data.sourceid,
                                'id': node.id,
                                'parent': node.data.p_id,
                                'source': node.data.source
                            };
                            let url = '/man/hide';
                            call_service_by_get(url, params, function (res) {
                                setTimeout(() => {
                                    inst.refresh(node);
                                    dialog.dialog("close");
                                }, 5000)
                            });
                        }
                    };
                }
            }

            let label = '标记搜索可见';
            let url = '/man/show';
            let pin_v = 1;
            if (node.data.pin === 1) {
                label = '标记搜索隐藏';
                url = '/man/hide';
                pin_v = 0;
            }
            // console.log('menu node:', node);
            if (node.data.isdir === 1 && node.data.source === 'shared' || node.data.isdir === 0 && node.data.source === 'local'){
                ctxmenu.isvisible = {
                    'separator_after': false,
                    'separator_before': true,
                    'label': label,
                    'action': function (data) {
                        dialog.dialog("open");
                        // console.log('isvisible data:', data);
                        let inst = $.jstree.reference(data.reference),
                            node = inst.get_node(data.reference);
                        let params = {
                            tk: GetQueryString('tk'),
                            recursion: 1,
                            'panid': node.data.sourceid,
                            'id': node.data._id,
                            'source': node.data.source
                        };
                        call_service_by_get(url, params, function (res) {
                            // inst.refresh(node);
                            node.data.pin = pin_v;
                            let el = $('#' + node.a_attr.id);
                            if (el) {
                                if (pin_v === 1) {
                                    el.css('color', 'red');
                                } else {
                                    el.css('color', 'black');
                                }
                            }

                            dialog.dialog("close");
                        });

                    }
                };
            }
            if(node.hasOwnProperty('menus')){
                for(var m in node.menus){
                    ctxmenu[m] = node.menus[m];
                }
            }
            return ctxmenu;
        }
    },
    "types":{
        '#': {"valid_children": ["root"]},
        "root": {"valid_children":["default"]},
        'default': {'icon': 'folder', "valid_children": ["default","file"]},
        'file': {'valid_children': [], 'icon': 'glyphicon glyphicon-file'}
    },
    "plugins" : [
        "contextmenu", "dnd", "search",
        "state", "types", "wholerow"
        // , "checkbox"
      ]
}).on('show_contextmenu.jstree', function(e, data){


}).on('changed.jstree', function(e, data){


});