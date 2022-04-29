window.mac_vendor = (function(){
    if (window.mac_vendor) {
        return window.mac_vendor;
    }
    var data_version = "?v=PKG_VERSION";
    var base_url = null;
    document.querySelectorAll('script[src*="/mac_vendor.js"]').forEach(function(s) {
        if (base_url == null || base_url == '') {
            var m = (s.getAttribute('src') || '').match(/^(.*)\/mac_vendor\.js(?:\?.*)?$/);
            if (m) {
                base_url = m[1];
            }
        }
    });
    var oui_path = base_url + "/oui.csv" + data_version;
    var oui_cn_path = base_url + "/oui_cn.json" + data_version;
    var oui_p = [9, 7, 6];
    var oui;
    var oui_cn;
    var fetch_oui;
    var fetch_oui_cn;
    var queryVendor = function(mac) {
        for (var i in oui_p) {
            if (mac.length >= oui_p[i]) {
                var vendor = oui[mac.substring(0, oui_p[i])];
                if (vendor !== undefined) {
                    return vendor
                }
            }
        }
    };
    var query = function(mac) {
        if (!oui || !mac){
            return;
        }
        mac = mac.replaceAll(/[-:]/g, '').toUpperCase();
        var vendor = queryVendor(mac);
        if (vendor === undefined) {
            return;
        }
        var vendor_cn;
        if (oui_cn) {
            vendor_cn = oui_cn[vendor];
        }
        return {vendor: vendor, vendor_cn:vendor_cn}
    };

    return (function(p){return {onready:function(cb){p.then(cb)}}})(
        new Promise(function(resolve){
            setTimeout(function(){
                fetch_oui=fetch(oui_path, {credentials: 'same-origin'})
                    .then(function(res){return res.text();})
                    .then(function(data){
                        oui = data.split('\n').reduce(function(acc, line){
                            var mid = line.indexOf('\t');
                            if (mid != -1) {
                                acc[line.substring(0, mid)] = line.substring(mid+1);
                            }
                            return acc;
                        }, {});
                    });
                fetch_oui_cn=fetch(oui_cn_path, {credentials: 'same-origin'})
                    .then(function(res){return res.json();})
                    .then(function(data){
                        oui_cn = data;
                    });
                var tasks=[fetch_oui, fetch_oui_cn];
                resolve(Promise.all(tasks))
            }, 500);
        })
        .then(function(){return {query:query};})
        );
})();
/* 
window.mac_vendor.onready(api=>api.query("98:01:A7:A8:00:00"))
*/
