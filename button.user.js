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
// @include        https://*waffles.ch/*
// @include        http*://*hdbits.org/*
// @include        http*://*bitmetv.org/*
// @include        http*://*sceneaccess.eu/*
// @include        http*://*awesome-hd.me/*
// @include        http*://*bit-hdtv.com/*
// @include        http*://*x264.me/*
// @include        http*://*gazellegames.net/*
// @include        http*://*redacted.ch/*
// @include        http*://*apollo.rip/*
// @include        http*://*morethan.tv/*
// @include        http*://*notwhat.cd/*
// @version        0.0.22
// @date           2014-17-11
// @grant          GM_getValue
// @grant          GM_setValue
// @grant          GM_notification
// ==/UserScript==

if (/https?.*?what\.cd.*/.test(document.URL)) {
	var linkregex = /torrents.php\?action=download.*?id=(\d+).*/i;
	var divider = ' | ';
	var site = "whatcd";
} else if (/https?.*?broadcasthe\.net.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var divider = ' | ';
	var site = "broadcasthenet";
} else if (/https?.*?fux0r\.eu.*/.test(document.URL)) {
	var linkregex = /torrents.php\?action=download.*?id=(\d+).*?/i;
	var divider = ' : ';
	var site = "fux0r";
} else if (/https?.*?passthepopcorn\.me.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var divider = ' | ';
	var site = "passthepopcorn";
} else if (/https?.*?tehconnection\.eu.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var divider = ' | ';
	var site = "tehconnection";
} else if (/https?.*?waffles\.ch.*/.test(document.URL)) {
	var linkregex = /.*?download.php\/\d+\/(\d+)\/(.*?)\.torrent\?passkey.*/i;
	var divider = ' | ';
	var site = "waffles";
	var includename = "2";
} else if (/https?.*?hdbits\.org.*/.test(document.URL)) {
	var linkregex = /download.php\?id=(\d+).*/i;
	var divider = ' | ';
	var site = "hdbits";
	// var includename = "2";
} else if (/https?.*?bitmetv\.org.*/.test(document.URL)) {
	var linkregex = /.*?download.php\/(\d+)\/(.*?)\.torrent$/i;
	var divider = ' | ';
	var site = "bitmetv";
	var includename = "2";
} else if (/https?.*?sceneaccess\.eu.*/.test(document.URL)) {
	var linkregex = /downloadbig.php\?id=(\d+).*?/i;
	var divider = ' | ';
	var site = "sceneaccess";
} else if (/https?.*?awesome-hd\.me.*/.test(document.URL)) {
	var linkregex = /torrents.php\?action=download.*?id=(\d+).*?/i;
	var divider = ' | ';
	var site = "awesomehd";
} else if (/https?.*?bit-hdtv\.com.*/.test(document.URL)) {
	var linkregex = /.*?download.php\/(\d+)\/(.*?)\.torrent.*/i;
	var divider = ' | ';
	var site = "bithdtv";
	var includename = "2";
} else if (/https?.*?x264\.me.*/.test(document.URL)) {
	var linkregex = /.*?download.php\/(\d+)\/(.*?)\.torrent.*/i;
	var divider = ' | ';
	var site = "bithdtv";
	var includename = "2";
} else if (/https?.*?gazellegames\.net.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var divider = ' | ';
	var site = "gazellegames";
} else if (/https?.*?redacted\.ch.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var divider = ' | ';
	var site = "redacted";
} else if (/https?.*?apollo\.rip.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var divider = ' | ';
	var site = "apollo";
} else if (/https?.*?morethan\.tv.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var devider = ' | ';
	var site = "morethantv";
} else if (/https?.*?notwhat\.cd.*/.test(document.URL)) {
	var linkregex = /torrents\.php\?action=download.*?id=(\d+).*?authkey=.*?torrent_pass=(?=([a-z0-9]+))\2(?!&)/i;
	var devider = ' | ';
	var site = "notwhat";
} else {
	alert("You have found a bug. Go and tell blubba!");
}

var settings = getSettings();
var settingsPage = window.location.href.match('user.php\\?action=edit&userid=');
var top10Page = window.location.href.match('top10.php');
var linkLabel = "pWA";
if (top10Page) {
	linkLabel = "[" + linkLabel + "]";
}

if (settings.pass && settings.url && settings.port) {
	alltorrents = [];
	for (var i = 0; i < document.links.length; i++) {
		alltorrents.push(document.links[i]);
	}

	for (var i = 0; i < alltorrents.length; i++) {
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
			createLink(alltorrents[i], id, name);
		}
	}
}

if (settingsPage) {
	appendSettings();
	document.getElementById('pywhatauto_settings_pass').addEventListener('change', saveSettings, false);
	document.getElementById('pywhatauto_settings_url').addEventListener('change', saveSettings, false);
	document.getElementById('pywhatauto_settings_port').addEventListener('change', saveSettings, false);
}

if (!settings && !settingsPage) {
	GM_notification({
		text: 'Missing configuration\nVisit user settings and setup',
		title: 'pyWHATauto:',
		timeout: 6000,
	});
}

function createLink(linkelement, id, name) {
	var link = document.createElement("pyWA");
	link.appendChild(document.createElement("a"));
	link.firstChild.appendChild(document.createTextNode(linkLabel));
	link.appendChild(document.createTextNode(divider));

	if (name) {
		link.firstChild.href = settings.url + ":" + settings.port + "/dl.pywa?pass=" + settings.pass + "&name=" + name + "&site=" + site + "&id=" + id;
	} else {
		link.firstChild.href = settings.url + ":" + settings.port + "/dl.pywa?pass=" + settings.pass + "&site=" + site + "&id=" + id;
	}
	link.firstChild.target = "_blank";
	link.firstChild.title = "Direct download to pyWHATauto";
	linkelement.parentNode.insertBefore(link, linkelement);
}

function appendSettings() {
	var container = document.getElementsByClassName('main_column')[0];
	var lastTable = container.lastElementChild;
	var settingsHTML = '<a name="pywhatauto_settings"></a>\n<table cellpadding="6" cellspacing="1" border="0" width="100%" class="layout border user_options" id="pywhatauto_settings">\n';
	settingsHTML += '<tbody>\n<tr class="colhead_dark"><td colspan="2"><strong>pyWHATauto Settings (autosaved)</strong></td></tr>\n';
	settingsHTML += '<tr><td class="label" title="Password">Password</td><td><input type="text" id="pywhatauto_settings_pass" placeholder="insert_your_pass" value="' + GM_getValue('pass', '') + '"></td></tr>\n';
	settingsHTML += '<tr><td class="label" title="Your seedbox hostname set in pywhatauto">Hostname</td><td><input type="text" id="pywhatauto_settings_url" placeholder="http://hostname.com" value="' + GM_getValue('url', '') + '"></td></tr>\n';
	settingsHTML += '<tr><td class="label" title="Your seedbox port set in pywhatauto">Port</td><td><input type="text" id="pywhatauto_settings_port" placeholder="your_chosen_port" value="' + GM_getValue('port', '') + '"></td></tr>\n';
	settingsHTML += '</tbody>\n</table>';
	lastTable.insertAdjacentHTML('afterend', settingsHTML);

	var sectionsElem = document.querySelectorAll('#settings_sections > ul')[0];
	sectionsHTML = '<h2><a href="#pywhatauto_settings" class="tooltip" title="pyWHATauto Settings">pyWHATauto</a></h2>';
	var li = document.createElement('li');
	li.innerHTML = sectionsHTML;
	sectionsElem.insertBefore(li, document.querySelectorAll('#settings_sections > ul > li:nth-child(10)')[0]);
}

function getSettings() {
	var pass = GM_getValue('pass', '');
	var port = GM_getValue('port', '');
	var url = GM_getValue('url', '');
	if (pass && url && port) {
		return {
			pass: pass,
			url: url,
			port: port
		};
	} else {
		return false;
	}
}

function saveSettings() {
	var elem = document.getElementById(this.id);
	var setting = this.id.replace('pywhatauto_settings_', '');
	var border = elem.style.border;
	GM_setValue(setting, elem.value);
	if (GM_getValue(setting) === elem.value) {
		elem.style.border = '1px solid green';
		setTimeout(function () {
			elem.style.border = border;
		}, 2000);
	} else {
		elem.style.border = '1px solid red';
	}
}
