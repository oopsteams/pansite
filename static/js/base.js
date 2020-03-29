
function GetQueryString(name){
     var reg = new RegExp("(^|&)"+ name +"=([^&]*)(&|$)");
     var r = window.location.search.substr(1).match(reg);
     if(r!=null){
         return decodeURIComponent(r[2])
     }
     return null;
}

function extname(filename) {
    if(!filename || typeof filename !== 'string'){
        return false
    }
    if(filename.indexOf('.')>0){
        let a = filename.split('').reverse().join('');
        let b = a.substring(0, a.search(/\./)).split('').reverse().join('')
        return b;
    } else {
        return '';
    }
}

function call_service(point, params, cb) {
   $.ajax({
           url:point,
           data:params,
           dataType:"json",
           method:"POST",
           contentType:"application/x-www-form-urlencoded; charset=UTF-8",
       }).done(function(res){
           console.log("load rs:", res);
           cb(res);
       });
}

function call_service_by_get(point, params, cb) {
   $.ajax({
           url:point,
           data:params,
           dataType:"json",
           method:"GET",
           contentType:"application/x-www-form-urlencoded; charset=UTF-8",
       }).done(function(res){
           console.log("load rs:", res);
           cb(res);
       });
}
