// ==UserScript==
// @name           What.cd Whatauto link creator
// @namespace      test.com
// @author         blubbablubb
// @description    Userscript to add a download button next to the torrent on the following sites.
// @include        http*://*what.cd/*
// @include        http*://*broadcasthe.net/*
// @include        http*://*fux0r.eu/*
// @include        http*://*passthepopcorn.me/*
// @include        http*://*tehconnection.eu/*
// @include        https://www.waffles.fm/*
// @include        http*://*hdbits.org/*
// @include        http*://*bitmetv.org/*
// @include        http*://*sceneaccess.eu/*
// @include        http*://*awesome-hd.net/*
// @include        http*://*bit-hdtv.com/*
// @include        http*://*x264.me/*
// @include        http*://*gazellegames.net/*
// @include        http*://*redacted.ch/*
// @include        http*://*apollo.rip/*
// @include        http*://*morethan.tv/*
// @version        0.0.22
// @date           2014-17-11
// ==/UserScript==

// EDIT THE FOLLOWING LINE WITH YOUR HOST (OR IP) + PORT WHICH YOU HAVE SELECTED IN setup.conf IN pyWHATAUTO
var weblink = "http://example.com:1337/dl.pywa?pass=youwouldliketoknowthisone";

if (/https?.*?what\.cd.*/.test(document.URL)) { 
	var linkregex = /torrents.php\?action=download.*?id=(\d+).*/i;
	var devider = ' | ';
	var site = "whatcd";
} else if (/https?.*?broadcasthe\.net.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var devider = ' | ';
	var site = "broadcasthenet";
} else if (/https?.*?fux0r\.eu.*/.test(document.URL)) {
	var linkregex = /torrents.php\?action=download.*?id=(\d+).*?/i;
	var devider = ' : ';
	var site = "fux0r";
} else if (/https?.*?passthepopcorn\.me.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var devider = ' | ';
	var site = "passthepopcorn";
} else if (/https?.*?tehconnection\.eu.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var devider = ' | ';
	var site = "tehconnection";
} else if (/https?.*?waffles\.fm.*/.test(document.URL)) {
	var linkregex = /.*?download.php\/\d+\/(\d+)\/(.*?)\.torrent\?passkey.*/i;
	var devider = ' | ';
	var site = "waffles";
	var includename = "2";
} else if (/https?.*?hdbits\.org.*/.test(document.URL)) {
	var linkregex = /download.php\?id=(\d+).*/i;
	var devider = ' | ';
	var site = "hdbits";
	// var includename = "2";
} else if (/https?.*?bitmetv\.org.*/.test(document.URL)) {
	var linkregex = /.*?download.php\/(\d+)\/(.*?)\.torrent$/i;
	var devider = ' | ';
	var site = "bitmetv";
	var includename = "2";
} else if (/https?.*?sceneaccess\.eu.*/.test(document.URL)) {
	var linkregex = /downloadbig.php\?id=(\d+).*?/i;
	var devider = ' | ';
	var site = "sceneaccess";
} else if (/https?.*?awesome-hd\.net.*/.test(document.URL)) {
	var linkregex = /torrents.php\?action=download.*?id=(\d+).*?/i;
	var devider = ' | ';
	var site = "awesomehd";
}  else if (/https?.*?bit-hdtv\.com.*/.test(document.URL)) {
	var linkregex = /.*?download.php\/(\d+)\/(.*?)\.torrent.*/i;
	var devider = ' | ';
	var site = "bithdtv";
	var includename = "2";
}  else if (/https?.*?x264\.me.*/.test(document.URL)) {
	var linkregex = /.*?download.php\/(\d+)\/(.*?)\.torrent.*/i;
	var devider = ' | ';
	var site = "bithdtv";
	var includename = "2";
} else if (/https?.*?gazellegames\.net.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var devider = ' | ';
	var site = "gazellegames";
} else if (/https?.*?redacted\.ch.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var devider = ' | ';
	var site = "redacted";
} else if (/https?.*?apollo\.rip.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var devider = ' | ';
	var site = "apollo";
} else if (/https?.*?morethan\.tv.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var devider = ' | ';
	var site = "morethantv";
} else {
	alert("You have found a bug. Go and tell blubba!");
}

alltorrents = new Array();
for (var i=0; i < document.links.length; i++) {
		alltorrents.push(document.links[i]);
}

for (var i=0; i < alltorrents.length; i++) {
	if (linkregex.exec(alltorrents[i])) {
		if (includename == 1) {
			id = RegExp.$2;
			name = RegExp.$1;
		} else if (includename == 2) {
			id = RegExp.$1;
			name = RegExp.$2;
		} else {
			id = RegExp.$1;
		}
		createlink(alltorrents[i],id,name);
	}
}

function createlink(linkelement,id,name) {
	var link = document.createElement("pyWA");
	link.appendChild(document.createElement("a"));
	link.firstChild.appendChild(document.createTextNode("pWA"));
	link.appendChild(document.createTextNode(devider));
	if (name) {
		link.firstChild.href=weblink+"&name="+name+"&site="+site+"&id="+id;
	} else {
		link.firstChild.href=weblink+"&site="+site+"&id="+id;
	}
	link.firstChild.target="_blank";
	link.firstChild.title="Direct Download to pyWHATauto";
	linkelement.parentNode.insertBefore(link, linkelement);
}
