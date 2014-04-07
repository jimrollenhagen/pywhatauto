#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from __future__ import with_statement
from __future__ import division


print('Starting main program.')
print('pyWHATauto: johnnyfive + blubba. WHATauto original creator: mlapaglia.')


import BaseHTTPServer
import ConfigParser
import cookielib
import datetime
import math
import os
import random
import re
import socket
import SocketServer
import sqlite3
import sys
import thread
import threading
import time
import traceback
import urllib
import urllib2

import db
import globals as G
import irclib
from torrentparser import torrentparser


VERSION = 'v1.73'
USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_1) '
              'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 '
              'Safari/537.36')
print('You are running pyWHATauto version %s\n' % VERSION)


def main():
    global irc, log, log2, lastFSCheck, last, SETUP
    last = False
    lastFSCheck = False
    log = False
    os.chdir(G.SCRIPTDIR)
    loadConfigs()
    if G.LOG:
        if not os.path.isdir(os.path.join(G.SCRIPTDIR, 'logs')):
            os.makedirs(os.path.join(G.SCRIPTDIR, 'logs'))
    global WIN32FILEE
    WIN32FILEE = False
    if os.name == 'nt':
        try:
            import win32file
            if win32file:
                pass
            WIN32FILEE = True
        except ImportError:
            out('ERROR', 'The module win32file is not installed. '
                'Please download it from '
                'http://sourceforge.net/projects/pywin32/files/')
            out('ERROR', 'The program will continue to function normally '
                'except where win32file is needed.')
            WIN32FILEE = False
    out('DEBUG', 'Starting report thread.')
    thread.start_new_thread(writeReport, (20,))
    out('DEBUG', 'Report thread started.')

    out('DEBUG', 'Starting DB thread.')
    # Create the DB object
    DB = db.sqlDB(G.SCRIPTDIR, G.Q)
    DB.setDaemon(True)
    DB.start()
    out('DEBUG', 'DB thread started.')

    out('DEBUG', 'Starting web thread.')
    # Create the web object
    try:
        WEB = WebServer(G.SCRIPTDIR,
                        SETUP.get('setup', 'password'),
                        SETUP.get('setup', 'port'),
                        SETUP.get('setup', 'webserverip'))
    except Exception:
        outexception('Exception caught in main(), when starting webserver')
    WEB.setDaemon(True)
    WEB.start()
    out('DEBUG', 'Web thread started.')
    try:
        irc = irclib.IRC()
        out('INFO', 'Main program loaded. Starting bots.')

        if G.TESTING:
            startBots()
        else:
            thread.start_new_thread(startBots, tuple())
    except Exception:
        outexception('General exception in main():')
    Prompt(.5)


def Prompt(n):
    global log, log2
    while 1:
        time.sleep(n)
        if G.EXIT:
            print('Exiting.')
            if G.LOG:
                log.close()
                log2.close()
            sys.exit(1)


class DuplicateError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def loadConfigs():
    global SETUP

    if os.name == 'nt' and os.path.exists(os.path.join(G.SCRIPTDIR, 'nt')):
        print('Loading nt settings')
        SETUP = ConfigParser.RawConfigParser()
        SETUP.readfp(open(os.path.join(G.SCRIPTDIR, 'nt', 'setup.conf')))

        CRED = ConfigParser.RawConfigParser()
        CRED.readfp(open(os.path.join(G.SCRIPTDIR, 'nt', 'credentials.conf')))

        CUSTOM = ConfigParser.RawConfigParser()
        CUSTOM.readfp(open(os.path.join(G.SCRIPTDIR, 'nt', 'custom.conf')))

        FILTERS = ConfigParser.RawConfigParser()
        FILTERS.readfp(open(os.path.join(G.SCRIPTDIR, 'nt', 'filters.conf')))

    else:
        SETUP = ConfigParser.RawConfigParser()
        SETUP.readfp(open(os.path.join(G.SCRIPTDIR, 'setup.conf')))

        CRED = ConfigParser.RawConfigParser()
        CRED.readfp(open(os.path.join(G.SCRIPTDIR, 'credentials.conf')))

        CUSTOM = ConfigParser.RawConfigParser()
        CUSTOM.readfp(open(os.path.join(G.SCRIPTDIR, 'custom.conf')))

        FILTERS = ConfigParser.RawConfigParser()
        try:
            FILTERS.readfp(open(os.path.join(G.SCRIPTDIR, 'filters.conf')))
        except ConfigParser.ParsingError as e:
            out('ERROR', 'There is a problem with your filters.conf. '
                'If using newlines, please make sure that each new line is '
                'tabbed in once. Error: %s' % e)
            raw_input('This program will now exit (okay):')
            quit()

    REPORT = ConfigParser.RawConfigParser()
    REPORT.readfp(open(os.path.join(G.SCRIPTDIR, 'reports.conf')))

    REGEX = ConfigParser.RawConfigParser()
    REGEX.readfp(open(os.path.join(G.SCRIPTDIR, 'regex.conf')))

    if SETUP.has_option('debug', 'testing'):
        if SETUP.get('debug', 'testing').strip() == '1':
            G.TESTING = True

    if SETUP.has_option('setup', 'log'):
        if SETUP.get('setup', 'log').strip() == '1':
            G.LOG = True

    # Load the reports.
    # Since we re-write the entire file every time, we have to load them all.
    for site in REPORT.sections():
        G.REPORTS[site] = dict()
        G.REPORTS[site]['seen'] = int(REPORT.get(site, 'seen'))
        G.REPORTS[site]['downloaded'] = int(REPORT.get(site, 'downloaded'))

    # alias stuff
    G.FROMALIAS = dict()
    G.TOALIAS = dict()
    for configs in CRED.sections():
        try:
            if CUSTOM.has_option('aliases', configs):
                new = CUSTOM.get('aliases', configs)
                existing = G.FROMALIAS.get('new')
                if existing is not None:
                    dupe_message = ('The alias %s is defined for two sites, '
                                    '%s and %s.' % (new, existing, configs))
                    raise DuplicateError(dupe_message)
                G.FROMALIAS[new] = configs
                G.TOALIAS[configs] = new
            elif SETUP.has_option('aliases', configs):
                new = SETUP.get('aliases', configs)
                existing = G.FROMALIAS.get('new')
                if existing is not None:
                    dupe_message = ('The alias %s is defined for two sites, '
                                    '%s and %s.' % (new, existing, configs))
                G.FROMALIAS[new] = configs
                G.TOALIAS[configs] = new
            else:
                G.TOALIAS[configs] = configs
            if configs not in G.FROMALIAS.keys():
                G.FROMALIAS[configs] = configs
        except DuplicateError as e:
            if log:
                out('ERROR', e)
            else:
                print(e)
            G.EXIT = True
            sys.exit()

        if CUSTOM.has_option('sites', configs):
            G.TOSTART[configs] = CUSTOM.get('sites', configs)
        elif SETUP.has_option('sites', configs):
            G.TOSTART[configs] = SETUP.get('sites', configs)
        else:
            G.TOSTART[configs] = '0'

    G.ALIASLENGTH = 0
    longest = ''
    for val in G.TOALIAS.itervalues():
        if len(val) > G.ALIASLENGTH:
            G.ALIASLENGTH = len(val)
            longest = val
    if log:
        out('DEBUG', 'Longest alias is %s (%s) with length %d' % (
            longest,
            G.FROMALIAS[longest],
            G.ALIASLENGTH))
    else:
        print('Longest alias is %s (%s) with length %d' % (
              longest,
              G.FROMALIAS[longest],
              G.ALIASLENGTH))

    if REGEX.has_option('version', 'version'):
        G.REGVERSION = int(REGEX.get('version', 'version'))

    G.NETWORKS = dict()

    for configs in CRED.sections():  # for network in credentials.conf
        # if the REPORTS.conf is missing this network, add it!
        if configs not in G.REPORTS:
            G.REPORTS[configs] = {'seen': 0, 'downloaded': 0}

        # add the credentials for each network key
        G.NETWORKS[configs] = dict()
        G.NETWORKS[configs]['creds'] = dict()
        for key, value in CRED.items(configs):
            G.NETWORKS[configs]['creds'][key] = value

        #add the regex for each network
        G.NETWORKS[configs]['regex'] = dict()

        if REGEX.has_section(configs):
            for key, value in REGEX.items(configs):
                G.NETWORKS[configs]['regex'][key] = value

        if CUSTOM.has_section(configs):
            for key, value in CUSTOM.items(configs):
                G.NETWORKS[configs]['regex'][key] = value

        # add the setup to each network (they will all have the same info)
        G.NETWORKS[configs]['setup'] = dict()
        for key, value in SETUP.items('setup'):
            G.NETWORKS[configs]['setup'][key] = value

        G.NETWORKS[configs]['notif'] = dict()
        for key, value in SETUP.items('notification'):
            G.NETWORKS[configs]['notif'][key] = value

        # add aliases
        G.NETWORKS[configs]['fromalias'] = dict()
        for key, value in G.FROMALIAS.iteritems():
            G.NETWORKS[configs]['fromalias'][key] = value

        G.NETWORKS[configs]['toalias'] = dict()
        for key, value in G.TOALIAS.iteritems():
            G.NETWORKS[configs]['toalias'][key] = value

        # add filters the networks they belong to
        G.NETWORKS[configs]['filters'] = dict()
        for f in FILTERS.sections():
            if FILTERS.get(f, 'site') == configs:
                G.NETWORKS[configs]['filters'][f] = dict()
                for key, value in FILTERS.items(f):
                    G.NETWORKS[configs]['filters'][f][key] = value
                # load the filter state into the filters dictionary
                G.FILTERS[f.lower()] = FILTERS.get(f, 'active')
                # if the filter has been manually toggled,
                # load that value instead
                if f.lower() in G.FILTERS_CHANGED:
                    _new_val = G.FILTERS_CHANGED[f.lower()]
                    G.NETWORKS[configs]['filters'][f]['active'] = _new_val


def reloadConfigs():
    G.LOCK.acquire()
    loadConfigs()
    for bot in G.RUNNING.itervalues():
        bot.save_new_configs(G.NETWORKS[bot.get_bot_name()])
    G.LOCK.release()
    out('INFO', 'Configs re-loaded.')


def outexception(msg=False, site=False):
    exc = traceback.format_exc()
    if msg:
        out('ERROR', msg, site)
    for excline in exc.splitlines():
        out('ERROR', excline, site)


def out(level, msg, site=False):
    global last
    levels = ['error', 'warning', 'msg', 'info', 'cmd', 'filter', 'debug']
    # getting color output ready for when I decide to implement it
    colors = {'error': '%s',
              'warning': '%s',
              'msg': '%s',
              'info': '%s',
              'cmd': '%s',
              'filter': '%s',
              'debug': '%s'}

    verbosity = SETUP.get('setup', 'verbosity').lower()
    if levels.index(level.lower()) <= levels.index(verbosity):
        _now = datetime.datetime.now()
        if site:
            if site != last and last is not False:
                if G.LOG:
                    logging('')
            msg = '%s %-*s %-*s %s' % (_now.strftime("%m/%d-%H:%M:%S"),
                                       7,
                                       level,
                                       G.ALIASLENGTH,
                                       G.TOALIAS[site],
                                       msg)
            print(colors[level.lower()] % msg)
            last = site
        else:
            msg = '%s %-*s %-*s %s' % (_now.strftime("%m/%d-%H:%M:%S"),
                                       7,
                                       level,
                                       G.ALIASLENGTH,
                                       '',
                                       msg)
            print(msg)
        if G.LOG:
            logging(msg)


def logging(msg):
    global log, log2, logdate
    # Create the log file
    logdir = os.path.join(G.SCRIPTDIR, 'logs')
    _now = datetime.datetime.now()
    if not log:
        logdate = _now.strftime("%m.%d.%Y-%H.%M")
        log = open(os.path.join(logdir, 'pyWALog-' + logdate + '.txt'), 'w')
        log2 = open(os.path.join(logdir, 'pyWALog.txt'), 'w')

    difference = _now - datetime.datetime.strptime(logdate, "%m.%d.%Y-%H.%M")
    if difference > datetime.timedelta(hours=24):
        log.close()
        logdate = _now.strftime("%m.%d.%Y-%H.%M")
        filename = os.path.join(logdir, 'pyWALog-' + logdate + '.txt')
        log = open(filename, 'w')
    log.write(msg + '\n')
    log.flush()
    log2.write(msg + '\n')
    log2.flush()


def startBots():
    global irc
    try:
        for key, value in G.TOSTART.items():
            if value == '1':
                establishBot(key)
        irc.process_forever()
    except Exception:
        outexception('General exception caught, startBots()')
        G.EXIT = True


def establishBot(sitename):
    '''Does some preliminary checks.
    Creates a new AutoBot instance and connects it to irc.
    '''

    # Need to check if there is sufficient regexp and credentials present

    if sitename in G.RUNNING.keys():
        out('INFO', 'The AutoBot for this site is already running')
        return 'The AutoBot for this site is already running'

    _re = G.NETWORKS[sitename]['regex']
    server = _re.get('server', '')
    port = _re.get('port', '')
    announcechannel = _re.get('announcechannel', '')
    if not (server != '' and port != '' and announcechannel != ''):
        _msg = 'This site does not have an irc announce channel.'
        out('INFO', _msg, site=sitename)
        return 'Cannot connect to irc network: %s' % _msg
    cr = G.NETWORKS[sitename]['creds']
    botnick = cr.get('botnick', '')
    nickservpass = cr.get('nickservpass', '')
    if not (botnick != '' and 'nickowner' in cr and nickservpass != ''):
        _msg = ('The credentials given are not sufficient to connect to the '
                'irc server.')
        out('ERROR', _msg, site=sitename)
        return 'ERROR: %s' % _msg

    shared = False

    # tempbotnick overrides botnick
    botnick = cr.get('tempbotnick', botnick)
    ircpw = cr.get('ircpassword')

    for key in G.RUNNING.keys():
        sre = G.NETWORKS[key]['regex']
        scr = G.NETWORKS[key]['creds']
        if sre['server'].lower() == _re['server'].lower():
            out('DEBUG',
                'Matching servers found between %s and %s (old), %s' % (
                    sitename,
                    key, _re['server']),
                site=sitename)
            sbotnick = scr.get('tempbotnick', scr['botnick'])
            sircpw = cr.get('ircpassword')
            if botnick.lower() == sbotnick.lower() and ircpw == sircpw:
                _msg = ('servers and nicks are matching the full way! '
                        'Piggybacking...')
                out('DEBUG', _msg, site=sitename)
                shared = key
                break

    G.LOCK.acquire()
    G.RUNNING[sitename] = AutoBot(sitename, G.NETWORKS[sitename])
    G.LOCK.release()

    if shared:
        G.RUNNING[sitename].set_shared_connection(G.RUNNING[shared])
        return 'Connecting to %s by piggybacking on %s\'s connection' % (
            sitename,
            shared)
    else:
        G.RUNNING[sitename].connect()
        return 'Connecting to %s' % sitename


def writeReport(n):
    last = 0
    while True:
        now = 0
        G.LOCK.acquire()
        for key in G.REPORTS.itervalues():
            now += int(key['seen'])
        if last != now:
            config = ConfigParser.RawConfigParser()
            for section in sorted(G.REPORTS.iterkeys()):
                config.add_section(section)
                config.set(section, 'seen', G.REPORTS[section]['seen'])
                config.set(section,
                           'downloaded',
                           G.REPORTS[section]['downloaded'])

            # release the lock before we waste time writing the config.
            G.LOCK.release()
            # Writing our configuration file to 'reports.conf'
            try:
                with open('reports.conf', 'wb') as configfile:
                    config.write(configfile)
                last = now
            except IOError as e:
                out('ERROR', e)
        else:
            G.LOCK.release()
        time.sleep(n)


def getDriveInfo(drive):
    if os.name == 'nt' and WIN32FILEE:
        import win32file
        drive = drive.replace(':\\', '')
        drive_info = win32file.GetDiskFreeSpace(drive + ":\\")
        sections, bytes_per, free_clusters, total_clusters = drive_info
        total_space = total_clusters * sections * bytes_per
        free_space = free_clusters * sections * bytes_per
        return free_space, float(free_space) / float(total_space)

    elif os.name == 'posix':
        if SETUP.has_option('setup', 'limit'):
            limit = SETUP.get('setup', 'limit').strip()
        else:
            limit = ''
        if limit not in ('', '0'):
            import shlex
            import subprocess
            args = shlex.split('du -s --bytes %s' % drive)
            du = subprocess.Popen(args, stdout=subprocess.PIPE)
            dureturn = du.communicate()[0]
            m = re.search('(\d+).*', dureturn)
            used = float(m.group(1)) / (1024 * 1024 * 1024)
            free = float(limit) - used
            return free, free / float(limit)
        else:
            out('ERROR', 'Unknown filesystem as it seems...')

    return 1.00, 1.00


def dlCookie(downloadID, site, cj, target, network=False, name=''):
    '''download using login/cookie technique.
    Returns 'preset' if a presetcookie is missing or malformatted,
    Returns 'password' if the password seems to be wrong
    Returns 'moved' if the download of the torrent file retrieves a redirect
    Returns 'httperror' for any httperror encountered
    Returns 'downloadtype' if the downloadtype is not set in regex.conf
    Returns 'passkey' if the passkey is not set in credentials.conf
    Returns an urllib2.urlopen object if a 200/ok was received.
    '''
    #see if there is a cookie already created.
    G.LOCK.acquire()

    if 'downloadtype' in G.NETWORKS[site]['regex']:
        downloadType = G.NETWORKS[site]['regex']['downloadtype']
    else:
        out('ERROR',
            'Download type is not set in regex.conf for %s' % site,
            site)
        G.LOCK.release()
        return 'downloadtype'

    if downloadType != '5':
        cookie_file = os.path.join(G.SCRIPTDIR, 'cookies', '%s.cookie' % site)
        if not os.path.isfile(cookie_file):
            G.LOCK.release()
            # check to make sure this isn't a site that needs a preset cookie.
            if G.NETWORKS[site]['regex'].get('presetcookie') == '1':
                _msg = ('This tracker requires you to manually create a '
                        'cookie file before you can download.')
                out('ERROR', _msg, site)
                return 'preset'
            else:
                # if not, log in and create one
                cj = createCookie(site, cj)
                if not cj:
                    return 'password'
        else:
            # load the cookie since it exists already
            try:
                cj.load(cookie_file, ignore_discard=True, ignore_expires=True)
                G.LOCK.release()
            except cookielib.LoadError:
                if G.NETWORKS[site]['regex'].get('presetcookie') == '1':
                    out('ERROR',
                        'The cookie for %s is the wrong format' % site,
                        site)
                    G.LOCK.release()
                    return 'preset'
                else:
                    G.LOCK.release()
                    cj = createCookie(site, cj)
                    if not cj:
                        return 'password'
    else:
        G.LOCK.release()
        if not G.NETWORKS[site]['creds'].get('passkey'):
            _msg = ('This site requires the passkey to be set in '
                    'credentials.conf')
            out('ERROR', _msg, site)
            return 'passkey'

    # create the downloadURL based on downloadType
    downloadURL = G.NETWORKS[site]['regex']['downloadurl']
    if downloadType == '1':  # request a download ID, and get a filename
        downloadURL = downloadURL + downloadID
    elif downloadType == '2':
        downloadURL = '%s/%s/%s.torrent' % (downloadURL,
                                            downloadID,
                                            downloadID)
    elif downloadType == '3':
        downloadURL = '%s/%s/%s' % (downloadURL,
                                    downloadID,
                                    G.NETWORKS[site]['regex']['urlending'])
    elif downloadType == '4':
        url_ending = G.NETWORKS[site]['regex']['urlending']
        downloadURL = '%s%s%s%s.torrent' % (downloadURL,
                                            downloadID,
                                            url_ending,
                                            downloadID)
    elif downloadType == '5':
        passkey = G.NETWORKS[site]['creds']['passkey']
        downloadURL = '%s/%s/%s/%s.torrent' % (downloadURL,
                                               downloadID,
                                               passkey,
                                               name)

    socket.setdefaulttimeout(25)

    handle = None
    try:
        handle = getFile(downloadURL, cj)
    except urllib2.HTTPError as e:
        if int(e.code) in (301, 302, 303, 307):
            _msg = ('Caught a redirect. '
                    'Code: %s, url: %s, headers %s, others: %s')
            _msg = _msg % (e.code, e.url, e.headers.dict, e.__dict__.keys())
            out('ERROR', _msg, site)
            return 'moved'
        else:
            _msg = ('Caught another http error. '
                    'Code: %s, url: %s, headers: %s, others: %s')
            _msg = _msg % (e.code, e.url, e.headers.dict, e.__dict__.keys())
            out('ERROR', _msg, site)
            return 'httperror'
    else:
        return handle


def download(downloadID, site, location=False, network=False, target=False,
             retries=0, email=False, notify=False, filterName=False,
             announce=False, formLogin=False, sizeLimits=False, name=False,
             fromweb=False):
    """Take an announce download ID and the site to download from.
    Do some magical stuff with cookies.
    Download the torrent into the watch folder.
    Returns a tuplet with (True/False, statusmsg).
    """
    _msg = ('Downloading ID: %s, site: %s, filter: %s, location: %s, '
            'network: %s, target: %s, retries: %s, email: %s, announce %s, '
            'name %s')
    _msg = _msg % (downloadID,
                   site,
                   filterName,
                   location,
                   network,
                   target,
                   retries,
                   email,
                   announce,
                   name)

    out('DEBUG', _msg)
    success = False
    error = ''

    G.LOCK.acquire()

    # load where we should be saving the torrent if not already set
    if not location:
        location = SETUP.get('setup', 'torrentdir')
        _watch = G.NETWORKS[site]['creds'].get('watch')
        if _watch:
            location = _watch

    # 'network' is only sent if it's a manual download,
    # so if it's false that means this is an automatic dl
    # if it's automatic, then check to see if the delay exists
    sleepi = None
    if retries == 0 and not network and not fromweb:
        _delay = ''
        if SETUP.has_option('setup', 'delay'):
            _delay = SETUP.get('setup', 'delay').strip()
        if _delay != '':
            sleepi = int(_delay)

    # check if the network requires a torrentname for downloading
    if G.NETWORKS[site]['regex'].get('downloadtype') == '5':
        _nameregexp = G.NETWORKS[site]['regex'].get('nameregexp')
        if _nameregexp:
            if not name:
                if announce:
                    name = re.match(_nameregexp, announce).group(1)
                else:
                    error = ('The download function for this site can only '
                             'be used for the button and automatic downloads.')
        else:
            error = ('This site requires the variable \'nameregexp\' to be '
                     'set in regex.conf.')

    G.LOCK.release()

    file_info = False
    retrieved = ''
    if not error:
        if sleepi:
            time.sleep(sleepi)
        # if this is a retry, then wait 3 seconds.
        if retries > 0:
            if not network and not fromweb:
                time.sleep(3)
            else:
                time.sleep(0.5)

        cj = cookielib.LWPCookieJar()

        # use the cookie to download the file
        retrieved = dlCookie(downloadID, site, cj, target, network, name)
        if str(type(retrieved)) == "<type 'instance'>":
            file_info = retrieved.info()

    retry = False

    if file_info:
        if file_info.type == 'text/html':
            # This could either mean the torrent doesn't exist
            # or we are not logged in
            G.LOCK.acquire()
            statusmsg = ('There was an error downloading torrent %s from %s. '
                         'Either it was deleted, or the %s you entered '
                         'is incorrect.')
            if G.NETWORKS[site]['regex'].get('presetcookie') == '1':
                statusmsg = statusmsg % (downloadID, site, 'cookie')
            else:
                statusmsg = statusmsg % (downloadID, site, 'credentials')
            G.LOCK.release()
            retry = True

        elif file_info.type == 'application/x-bittorrent':
            # figure out the filename
            # see if the file has content disposition, if it does read it.
            info = retrieved.read()
            try:
                tp = torrentparser(debug=False, content=info)
                mbsize = tp.mbsize()
                tpname = tp.name()
            except SyntaxError as e:
                _msg = ('The torrentparser was unable to parse the torrent '
                        'file. Please let blubba know: %s')
                out('ERROR', _msg % e, site)
                mbsize = None
                tpname = None

            if not name:
                if tpname:
                    filename = tpname
                else:
                    if 'Content-Disposition' in file_info:
                        for cd in G.CD:
                            if cd in file_info['Content-Disposition']:
                                filename = file_info['Content-Disposition']
                                filename = filename.replace(cd, '')
                                filename = filename.replace('"', '')
                    if filename == '':
                        filename = downloadID + '.torrent'
            else:
                filename = name

            if '.torrent' not in filename:
                filename += '.torrent'
            filename = urllib.unquote(filename)

            sizeOK = True
            if sizeLimits and not (network or fromweb):
                sizerange = sizeLimits.split(',')
                if mbsize:
                    G.LOCK.acquire()
                    if ((len(sizerange) == 1
                            and mbsize > float(sizerange[0]))
                            or (len(sizerange) == 2
                                and mbsize > float(sizerange[1]))):
                        _msg = ('(%s) Torrent is larger than required by '
                                'filter "%s".')
                        _msg = _msg % (downloadID, filterName)
                        out('INFO', _msg, site)
                        sizeOK = False
                    elif len(sizerange) == 2 and mbsize < float(sizerange[0]):
                        sizeOK = False
                        _msg = ('(%s) Torrent is smaller than required by '
                                'filter "%s".')
                        _msg = _msg % (downloadID, filterName)
                        out('INFO', _msg, site)
                    else:
                        _msg = ('(%s) Torrent is within size range required '
                                'by filter "%s".')
                        _msg = _msg % (downloadID, filterName)
                        out('INFO', _msg, site)
                    G.LOCK.release()
            elif not (network or fromweb):
                G.LOCK.acquire()
                out('INFO', '(%s) No Size check.' % downloadID, site)
                G.LOCK.release()
            if sizeOK:
                G.LOCK.acquire()
                try:
                    local_file = open(os.path.join(location, filename), 'wb')
                    local_file.write(info)
                    local_file.close()
                except IOError:
                    # If there's no room on the hard drive
                    _msg = ('(%s) !! Disk quota exceeded. Not enough room '
                            'for the torrent!') % downloadID
                    out('ERROR', _msg, site)
                    statusmsg = ('Can\'t write the torrent file on the disk, '
                                 'as there is not enough free space left!')
                    retry = True
                else:
                    # if the filesize of the torrent is too small
                    # then retry in a moment
                    _size = os.path.getsize(os.path.join(location, filename))
                    if 100 > int(_size):
                        statusmsg = ('The size of the torrent is too small. '
                                     'Maybe try a different torrent of this '
                                     'tracker to see if this is a local or '
                                     'global occurance.')
                        retry = True
                    else:
                        success = True
                        if mbsize:
                            statusmsg = ('Torrent (id: %s) successfully '
                                         'downloaded! Size %.2f MB, '
                                         'retries: %d, filename: %s')
                            statusmsg = statusmsg % (downloadID,
                                                     mbsize,
                                                     retries,
                                                     filename)
                        else:
                            statusmsg = ('Torrent (id: %s) successfully '
                                         'downloaded! Retries: %d, '
                                         'filename: %s') % (downloadID,
                                                            retries,
                                                            filename)
                G.LOCK.release()
            else:
                statusmsg = 'The torrent size did not fit the filter.'

        else:
            out('ERROR',
                'unknown filetype received: %s' % file_info.type,
                site)
            retry = True

    elif error:
        statusmsg = error
    else:
        if retrieved == 'preset':
            statusmsg = ('This site requires a cookie to be preset, '
                         'called \'%s.torrent\' in the folder \'cookies\'. '
                         'Either this cookie is missing or '
                         'malformatted.') % site

        elif retrieved == 'password':
            statusmsg = ('The login credentials set in credentials.conf '
                         'for %s are incorrect or missing.') % site

        elif retrieved == 'moved':
            statusmsg = ('Either the torrent id (%s) does not exist or your '
                         'credentials for %s are wrong or '
                         'missing') % (downloadID, site)
            retry = True

        elif retrieved == 'httperror':
            statusmsg = ('An http error occured. Please check if the site is '
                         'online, and check the log for more details if this '
                         'problem persists.')
            retry = True

        elif retrieved == 'downloadtype':
            statusmsg = ('The key \'downloadType\' is not set in '
                         'regex.conf. Aborting.')

        elif retrieved == 'passkey':
            statusmsg = ('This site requires the passkey to be set in '
                         'credentials.conf. Please set it and try again.')

    if retry and retries <= 0:
        G.LOCK.acquire()
        _presetcookie = G.NETWORKS[site]['regex'].get('presetcookie')
        if not _presetcookie or _presetcookie != '1':
            cookie_path = os.path.join(G.SCRIPTDIR,
                                       'cookies',
                                       site + '.cookie')
            if os.path.isfile(cookie_path):
                os.remove(cookie_path)
            else:
                _msg = ('The cookie file doesn\'t exist here... '
                        'this should not happen!')
                out('ERROR', _msg, site)

        _msg = ('(%s) !! Torrent file is not ready to be downloaded. '
                'Trying again in a moment. Reason: %s')
        out('INFO', _msg % (downloadID, statusmsg), site)
        G.LOCK.release()
        return download(downloadID,
                        site,
                        location=location,
                        network=network,
                        target=target,
                        retries=retries+1,
                        email=email,
                        notify=notify,
                        filterName=filterName,
                        announce=announce,
                        formLogin=formLogin,
                        sizeLimits=sizeLimits,
                        name=name,
                        fromweb=fromweb)

    elif success:
        G.LOCK.acquire()
        out('INFO', '%s to %s' % (statusmsg, location), site)
        if email:
            sendEmail(site, announce, filterName, filename)
        if notify:
            sendNotify(site, announce, filterName, filename)
        if network:
            network.send_msg(statusmsg, target)
        G.LOCK.release()
        return (True, statusmsg)
    else:
        # did not succeed in downloading!
        G.LOCK.acquire()
        _msg = 'Download error (%s): %s' % (downloadID, statusmsg)
        out('ERROR', _msg, site)
        if network:
            _msg = 'Download error (%s:%s): %s' % (site, downloadID, statusmsg)
            network.send_msg(_msg, target)
        G.LOCK.release()
        return (False, statusmsg)


def getFile(downloadURL, cj):
    # create the opener
    if SETUP.get('setup', 'verbosity').lower() == 'debug':
        opener = build_opener(cj, debug=1)
    else:
        opener = build_opener(cj)
    urllib2.install_opener(opener)
    req = urllib2.Request(downloadURL)
    req.add_header("User-Agent", USER_AGENT)
    return urllib2.urlopen(req)


def createCookie(site, cj):
    cookie_path = os.path.join(G.SCRIPTDIR, 'cookies', '%s.cookie' % site)

    if SETUP.get('setup', 'verbosity').lower() == 'debug':
        opener = build_opener(cj, debug=1)
    else:
        opener = build_opener(cj)
    urllib2.install_opener(opener)

    userpost = G.NETWORKS[site]['regex'].get('loginuserpost', 'username')
    passpost = G.NETWORKS[site]['regex'].get('loginpasswordpost', 'password')

    httpdict = {
        userpost: G.NETWORKS[site]['creds']['username'],
        passpost: G.NETWORKS[site]['creds']['password']
    }

    extra_post_data = G.NETWORKS[site]['regex'].get('morepostdata', '')
    if extra_post_data != '':
        try:
            newdict = eval('{' + extra_post_data + '}')
        except SyntaxError:
            _msg = 'morepostdata variable raised a syntax error: %s'
            _msg = _msg % extra_post_data
            out('ERROR', _msg, site)
        httpdict.update(newdict)

    if site == 'passthepopcorn':
        httpdict['passkey'] = G.NETWORKS[site]['creds']['passkey']

    http_args = urllib.urlencode(httpdict)

    req = urllib2.Request(G.NETWORKS[site]['regex']['loginurl'], http_args)
    req.add_header('User-Agent', USER_AGENT)

    if site == 'whatcd':
        req.add_header('Referer', 'https://what.cd/login.php')

    _msg = ('Logging into %s because a cookie was not previously saved or is '
            'outdated.') % site
    out('INFO', _msg, site)

    handle = None
    try:
        handle = urllib2.urlopen(req)
    except urllib2.HTTPError as e:
        _msg = 'Caught a redirect. Code: %s, url: %s, headers %s, others: %s'
        _msg = _msg % (e.code, e.url, e.headers.dict, e.__dict__.keys())
        out('DEBUG', _msg, site)

        G.LOCK.acquire()
        cj.save(cookie_path, ignore_discard=True, ignore_expires=True)
        G.LOCK.release()
        return cj

    login200 = G.NETWORKS[site]['regex'].get('login200')
    loginjson = G.NETWORKS[site]['regex'].get('loginjson')

    if handle and login200 == '1':
        G.LOCK.acquire()
        cj.save(cookie_path, ignore_discard=True, ignore_expires=True)
        G.LOCK.release()
        return cj

    elif handle and loginjson == '1':
        import json
        try:
            json_data = json.loads(handle.read())
        except ValueError:
            out('ERROR', 'Invalid JSON returned on login attempt', site)
            return
        result = json_data.get('Result')

        if result == 'Error':
            message = json_data.get('Message', 'unknown')
            _msg = 'Login error: %s' % message
            out('ERROR', _msg, site)

        elif result == 'Ok':
            G.LOCK.acquire()
            cj.save(cookie_path, ignore_discard=True, ignore_expires=True)
            G.LOCK.release()
            return cj

    elif handle:
        out('ERROR', 'Password seems to be incorrect', site)
        return False
    else:
        out('ERROR',
            'We don\'t have a redirect but still data? How can that happen?',
            site)


class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        out('DEBUG',
            'Redirect received. stuff: %s, %s, %s' % (code, msg, newurl))
        return None


def build_opener(cj, debug=False):
    http_handler = urllib2.HTTPHandler(debuglevel=debug)
    https_handler = urllib2.HTTPSHandler(debuglevel=debug)
    cookie_handler = urllib2.HTTPCookieProcessor(cj)

    opener = urllib2.build_opener(http_handler,
                                  https_handler,
                                  cookie_handler,
                                  SmartRedirectHandler())
    opener.cookie_jar = cj
    return opener


def sendEmail(site, announce, filter, filename):
    from email.mime import text as mimetext
    import smtplib

    _msg = ('pyWA has detected a new download.\n\n'
            'Site: %(site)s\n'
            'Captured Announce: %(announce)s\n'
            'Matched Filter: %(filter)s\n'
            'Saved Torrent: %(filename)s')
    _msg = _msg % ({
        'filename': filename,
        'filter': filter,
        'site': site,
        'announce': announce
    })
    msg = mimetext.MIMEText(_msg)
    gmail = SETUP.get('notification', 'gmail')
    msg['Subject'] = 'pyWA: New %s download!' % site

    s = smtplib.SMTP("smtp.gmail.com", 587)
    s.ehlo()
    s.starttls()
    s.ehlo()

    try:
        out('INFO', 'Emailing %s with a notification.' % gmail, site)
        s.login(gmail, SETUP.get('notification', 'password'))
        s.sendmail(gmail, gmail, msg.as_string())
        s.quit()
    except Exception as e:
        out('ERROR',
            'Could not send notify email. Error: %s' % e.smtp_error,
            site)


def sendNotify(site, announce, filter, filename):
    sent = False
    notify_server = SETUP.get('notification', 'server')
    for net in G.RUNNING.itervalues():
        if net.get_bot_name() == notify_server:
            _msg = 'Messaging %s with an IRC notification.'
            out('INFO', _msg % SETUP.get('notification', 'nick'), site)

            _msg = 'New DL! Site: %(site)s, Filter: %(filter)s, File: %(file)s'
            _msg = _msg % ({
                'site': site,
                'filter': filter,
                'file': filename
            })
            net.send_msg(_msg, SETUP.get('notification', 'nick'))
            sent = True

    if not sent:
        _msg = ('Could not send notification via %s, because I am not '
                'connected to that network.') % notify_server
        out('ERROR', _msg, site)


class WebServer(threading.Thread):
    def __init__(self, loadloc, pw, port, ip=''):
        global webpass
        super(WebServer, self).__init__()

        self.loadloc = loadloc
        try:
            self.port = int(port)
        except ValueError:
            out('ERROR', 'Invalid web UI port. Using default of 8999')
            self.port = 8999
        self.ip = ip
        if pw != '':
            webpass = pw
        else:
            webpass = str(random.randint(10**5, 10**9))
            _msg = 'No webserver password set. Assigning a random one: %s'
            _msg = _msg % webpass
            out('ERROR', _msg)

    def run(self):
        global CONN, C
        CONN = sqlite3.connect(os.path.join(self.loadloc, 'example.db'))
        C = CONN.cursor()

        self.server = ThreadedHTTPServer((self.ip, self.port), MyHandler)
        out('INFO', 'Starting web server.')
        self.server.serve_forever()


class ThreadedHTTPServer(SocketServer.ThreadingMixIn,
                         BaseHTTPServer.HTTPServer):
    """Handles requests in threads."""


class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        self.routes = {
            'dl.pywa': self.download,
        }
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def parse_path(self):
        path = self.path[1:]
        parts = path.split('?')
        path = parts[0]
        args = {}
        if len(parts) > 1:
            params = ''.join(parts[1:])
            params = parts[1].split('&')
            for param in params:
                pieces = param.split('=')
                if len(pieces) > 1:
                    args[pieces[0]] = ''.join(pieces[1:])
                else:
                    args[pieces[0]] = None

        return path, args

    def route(self, path):
        out('DEBUG', 'getting path %s' % path)
        return self.routes.get(path)

    def download(self, args):
        id_ = args.get('id')
        site = args.get('site', '').lower()
        password = args.get('pass')
        name = args.get('name')

        if not id_:
            self.send_error(400, 'Torrent ID missing.')
            return
        if not site or site not in G.FROMALIAS:
            self.send_error(400, 'Unknown site')
            return
        if password is None or password != webpass:
            self.send_error(403, 'Incorrect password')
            return

        site = G.FROMALIAS[site]

        try:
            if 'buttonwatch' in G.NETWORKS[site]['creds']:
                loc = G.NETWORKS[site]['creds']['buttonwatch']
            elif (SETUP.has_option('setup', 'buttonwatch')
                  and SETUP.get('setup', 'buttonwatch') != ''):
                loc = SETUP.get('setup', 'buttonwatch')
            else:
                loc = None
            output = download(id_, site, location=loc, name=name, fromweb=True)

        except Exception as e:
            _msg = 'Error while downloading %s from web, error: %s'
            outexception(_msg % (id_, e), site)
            raise

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        if output[0]:
            self.wfile.write('<html><head><script>t = null;function moveMe()'
                             '{t = setTimeout("self.close()",10000);}'
                             '</script></head><body onload="moveMe()">')
            self.wfile.write('%s' % output[1])
            self.wfile.write('</body></html>')
        else:
            self.wfile.write('<html><head></head>')
            self.wfile.write('<body>%s</body></html>' % output[1])

    def do_GET(self):
        try:
            path, args = self.parse_path()
            handler_func = self.route(path)
            if handler_func is None:
                self.send_error(404)
                return
            handler_func(args)
        except Exception as e:
            outexception('web request handling error: %s' % e)
            self.send_error(500)


class AutoBot(object):
    """A class for connecting to an IRC network,
    joining an announce channel,
    and watching for releases to download.
    """

    def __init__(self, name, info):
        out('DEBUG', 'AutoBot: %s started' % name, site=name)
        self.name = name
        self.lastannounce = None
        self.lastannouncetext = ""
        self.attempt = 0
        self.ownernetwork = None
        self.ownertarget = None
        self.havesendwhois = False
        self.havesendwhoami = False
        self.havesendwhoisall = []
        self.piggyback = [self.name]
        self.pingsent = False
        self.lastdata = datetime.datetime.now()
        self.regex = info['regex']
        self.creds = info['creds']
        self.setup = info['setup']
        self.notif = info['notif']
        self.filters = info['filters']
        self.toalias = info['toalias']
        self.fromalias = info['fromalias']
        self.announcehistory = []
        self.threads = []
        self.connection = None
        self.who = []
        self.partPhrase = ':I leave because I want to!'
        # have we already joined the channels we're supposed to after connect?
        self.joined = False
        self.reg = {}
        self.resistant = False
        self.ircreg = re.compile(
            "\x0f|\x1f|\x02|\x03(?:[\d]{1,2}(?:,[\d]{1,2})?)?",
            re.UNICODE)

        for announce in info['regex']['announces'].split(', '):
            self.reg[announce] = re.compile(info['regex'][announce])

        self.checkTorrentFolders(False)

        nickowner = self.creds['nickowner']
        if '!' in nickowner:
            self.creds['nickowner'] = nickowner[nickowner.index('!') + 1:]

        G.LOCK.acquire()
        irc.add_global_handler('pubmsg', self.handle_pub_message)
        irc.add_global_handler('privmsg', self.handle_priv_message)
        irc.add_global_handler('welcome', self.handle_welcome)
        irc.add_global_handler('nicknameinuse', self.handleNickInUse)
        irc.add_global_handler('invite', self.handle_invite)
        irc.add_global_handler('whoisuser', self.handleWhoIs)
        irc.add_global_handler('whoischannels', self.handleWhoIs)
        irc.add_global_handler('whoisserver', self.handleWhoIs)
        irc.add_global_handler('endofwhois', self.handleWhoIs)
        irc.add_global_handler('privnotice', self.handlePrivNotice)
        irc.add_global_handler('namreply', self.handleNameReply)
        irc.add_global_handler('action', self.handleAction)
        irc.add_global_handler('currenttopic', self.handleCurrentTopic)
        irc.add_global_handler('error', self.handleError)
        irc.add_global_handler('pong', self.handlePong)
        irc.add_global_handler('nosuchnick', self.handlenosuchnick)
        for value in G.ALL_EVENTS:
            irc.add_global_handler(value, self.handleAllDebug)

        # Warn if nickowner is empty!
        if self.creds['nickowner'] == '':
            out('WARNING',
                'Nickowner on network "%s" is blank!' % self.name,
                site=self.name)

        # Create a server object, connect and join the channel
        self.connection = irc.server()
        G.LOCK.release()

    def save_new_configs(self, info):
        self.regex = info['regex']
        self.creds = info['creds']
        self.setup = info['setup']
        self.notif = info['notif']
        self.filters = info['filters']
        self.toalias = info['toalias']
        self.fromalias = info['fromalias']
        for announce in info['regex']['announces'].split(', '):
            self.reg[announce] = re.compile(info['regex'][announce])

        self.checkTorrentFolders(None)

    def set_shared_connection(self, other_network):
        #this means we are using another bot's connection, so don't bother
        self.piggyback = other_network.piggyback
        self.piggyback.append(self.name)
        self.connection = other_network.connection
        have_joined = False
        for site in self.piggyback:
            if G.RUNNING[site].joined:
                have_joined = True
        if have_joined:
            self.logintochannels(self.connection, None)

    def get_bot_name(self):
        return self.name

    def checkTorrentFolders(self, target):
        for key, _filter in self.filters.iteritems():
            if _filter['active'] == '1':
                _watch = _filter.get('watch', '')
                if _watch != '':
                    try:
                        if not os.path.isdir(_watch):
                            os.makedirs(_watch)
                    except Exception as e:
                        out('ERROR', e)
                        if target:
                            _msg = ('Error: There was a problem with the '
                                    'custom watch folder for filter "%s". '
                                    'It will be ignored. : "%s"' % (key,
                                                                    _watch))
                            self.send_msg(_msg, target)
                            _filter['watch'] = ''

        _watch = self.creds.get('watch', '')
        if _watch != '':
            try:
                if not os.path.isdir(_watch):
                    os.makedirs(_watch)
            except Exception as e:
                out('ERROR', e)
                if target:
                    _msg = ('Error: There was a problem with the custom watch '
                            'folder for site "%s". It will be ignored. '
                            ': "%s"') % (key, _watch)
                    self.send_msg(_msg, target)
                    self.creds['watch'] = ''

        torrentdir = self.setup.get('torrentdir')
        if torrentdir is None:
            _msg = ('Setup option "torrentDir" is missing from setup.conf. '
                    'So let\'s put it in there, mmmmkay?')
            out('ERROR', _msg)
            raw_input('This program will now exit (okay): ')
            G.EXIT = True
            sys.exit()

        try:
            if not os.path.isdir(torrentdir):
                os.makedirs(torrentdir)

        except os.error as e:
            out('ERROR', 'torrentDir: %s caused %s' % (torrentdir, e))
            raw_input('This program will now exit (okay): ')
            G.EXIT = True
            sys.exit()

        except Exception as e:
            out('ERROR', e)
            raw_input("This program will now exit (okay): ")
            G.EXIT = True
            sys.exit()

    def connect(self):
        """Connect to the IRC network and join the appropriate channels."""
        if self.name not in G.RUNNING.keys():
            return

        out('DEBUG', 'piggyback is %s' % self.piggyback, site=self.name)
        for key in self.piggyback:
            if key in G.RUNNING:
                G.RUNNING[key].joined = False
                out('DEBUG', 'Reset self.joined for %s' % key, site=self.name)

        self.attempt += 1
        connerr = False
        self.pingsent = False
        if self.attempt > 1:
            out('INFO',
                'Connection attempt number %d' % self.attempt,
                site=self.name)

        try:
            cssl = (self.regex.get('ssl') == '1')
            if 'port' in self.regex and self.regex['port'].isdigit():
                cport = int(self.regex['port'])
            else:
                cport = 6667

            _msg = 'Connecting to the server: %s on port: %s SSL: %s'
            _msg = _msg % (self.regex['server'], cport, cssl)
            out('INFO', _msg, site=self.name)

            botnick = self.creds.get('tempbotnick') or self.creds['botnick']
            password = self.creds.get('ircpassword')

            if 'ircusesignon' in self.creds:
                self.connection.connect(self.regex['server'],
                                        cport,
                                        botnick,
                                        password,
                                        ircname=self.creds['username'],
                                        ssl=cssl)
            else:
                self.connection.connect(self.regex['server'],
                                        cport,
                                        botnick,
                                        ircname=self.creds['username'],
                                        ssl=cssl)

        except irclib.ServerConnectionError as e:
            out('ERROR', 'Server Connection Error: %r' % e, site=self.name)
            connerr = True
        except irclib.ServerNotConnectedError as e:
            out('ERROR',
                'Server Not Connected Error: %r' % e.message(),
                site=self.name)
            connerr = True

        if connerr:
            if self.attempt > 10:
                connerr = False
                _msg = ('Failed to connect to server %s:%s after retrying %s '
                        'times, aborting connecting.') % (self.regex['server'],
                                                          cport,
                                                          self.attempt)
                out('ERROR', _msg, site=self.name)

                for site in self.piggyback:
                    out('DEBUG',
                        'Removing %s from the running networks' % site,
                        site=self.name)

                    if site in G.RUNNING:
                        G.RUNNING[site].disconnect()
                        G.LOCK.acquire()
                        del G.RUNNING[site]
                        G.LOCK.release()
                    else:
                        out('ERROR',
                            'Site name %s was not found in G.RUNNING' % site,
                            site=self.name)

            else:
                _retry_time = int(math.pow(2, self.attempt))
                out('INFO',
                    'Retrying in %d seconds' % _retry_time,
                    site=self.name)
                self.connection.execute_delayed(_retry_time, self.connect)

        else:
            self.attempt = 0
            self.connection.execute_delayed(10, self.testtimeout)

    def disconnect(self):
        if len(self.piggyback) == 1:
            self.connection.disconnect(
                'pyWHATauto %s - http://bot.whatbarco.de' % VERSION)

        irc.remove_global_handler('pubmsg', self.handle_pub_message)
        irc.remove_global_handler('privmsg', self.handle_priv_message)
        irc.remove_global_handler('welcome', self.handle_welcome)
        irc.remove_global_handler('nicknameinuse', self.handleNickInUse)
        irc.remove_global_handler('invite', self.handle_invite)
        irc.remove_global_handler('whoisuser', self.handleWhoIs)
        irc.remove_global_handler('whoischannels', self.handleWhoIs)
        irc.remove_global_handler('whoisserver', self.handleWhoIs)
        irc.remove_global_handler('endofwhois', self.handleWhoIs)
        irc.remove_global_handler('privnotice', self.handlePrivNotice)
        irc.remove_global_handler('namreply', self.handleNameReply)
        irc.remove_global_handler('action', self.handleAction)
        irc.remove_global_handler('currenttopic', self.handleCurrentTopic)
        irc.remove_global_handler('error', self.handleError)
        irc.remove_global_handler('pong', self.handlePong)
        irc.remove_global_handler('nosuchnick', self.handlenosuchnick)
        for value in G.ALL_EVENTS:
            irc.remove_global_handler(value, self.handleAllDebug)

        self.pingsent = False

    def should_download(self, m, filtertype):
        release = {}
        group_names = self.regex[filtertype + 'format'].split(', ')
        for i, group_name in enumerate(group_names):
            # create the announcement/release format loaded from regex.conf
            release[group_name] = m.group(i)

        # these will save the key/values that cause the filter to fail
        badkey = ''
        for filter_name, _filter in self.filters.iteritems():
            filter_section_ok = True
            out('FILTER',
                'Checking filter section \'%s\'' % filter_name,
                site=self.name)

            if _filter['active'] == '1':
                _type = _filter.get('filtertype')
                if _type == filtertype or len(group_names) == 1:
                    # for each filter option within each filter section
                    for key, value in _filter.items():
                        # this will be set to False if any filters are not met
                        if filter_section_ok:
                            tags = self.regex['tags']
                            not_tags = self.regex['not_tags']
                            # if the filter tag is an allowed tag
                            if key in tags or key in not_tags:
                                # is the release item matched in this filter?
                                tag_ok = self.is_tag_ok(key,
                                                        value,
                                                        release,
                                                        filtertype)
                                if not tag_ok:
                                    #if a filter option doesn't match,
                                    # then the filter section does not match
                                    filter_section_ok = False
                                    badkey = key
                                    break

                    # if every filter option has passed within this filter,
                    # then the section is ok.
                    if filter_section_ok:
                        out('INFO',
                            'Filter %s matches' % filter_name,
                            site=self.name)
                        torrentdir = self.setup['torrentdir']
                        if _filter.get('watch') is not None:
                            torrentdir = _filter['watch']
                        return torrentdir, key

                    # Format the output of the failed filter
                    try:
                        _msg = None
                        if badkey == 'all_tags':
                            tag = m.group(group_names.index('tags') + 1)
                            _msg = ('Filter \'%s\' failed because the release '
                                    'did not match %s with \'%s\'')
                            _msg = _msg % (filter_name,
                                           badkey,
                                           tag)

                        elif badkey in self.regex['tags']:
                            _index = group_names.index(
                                badkey.replace('not_', ''))
                            bad_value = m.group(_index + 1)
                            _msg = ('Filter \'%s\' failed because the release '
                                    'did not match %s with \'%s\'')
                            _msg = _msg % (filter_name,
                                           badkey,
                                           bad_value)

                        elif badkey in self.regex['not_tags']:
                            _index = group_names.index(
                                badkey.replace('not_', ''))
                            bad_value = m.group(_index + 1)
                            _msg = ('Filter \'%s\' failed because the release '
                                    'contained \'%s\' which is in %s')
                            _msg = _msg % (filter_name,
                                           bad_value,
                                           badkey)

                        if _msg:
                            out('INFO', _msg, site=self.name)

                    except ValueError as e:
                        _msg = ('There was an error trying to output why the '
                                'filter did not match. %s') % e
                        out('ERROR', _msg)

                else:
                    _msg = 'Filter \'%s\' is not of type: %s' % (filter_name,
                                                                 filtertype)
                    out('INFO', _msg, site=self.name)

            else:
                out('INFO',
                    'Filter \'%s\' is not active' % (filter_name),
                    site=self.name)

        return False, False

    def is_tag_ok(self, key, value, release, filtertype):
        """Checks a given `key` in a filter and its `value`.
        Returns True if the release matches the filter key, otherwise False.
        """
        # we check size later on
        if key == 'size':
            return True

        keys = release.keys()

        if key in keys or (key == 'all_tags' and 'tags' in keys):
            # test to make sure that the values for the filter option exist,
            # if it's just blank then return true
            if not value.strip():
                return True

            release_val = release[key]
            if release_val is not None:
                release_val = release_val.strip().lower()

            # looking for option exists in the release
            if value == '1':
                if release_val is not None:
                    out('FILTER',
                        'Detected "%s", which you wanted.' % release_val,
                        site=self.name)
                    return True

            # looking for option does not exist in release
            elif value == '0':
                if release_val is None:
                    out('FILTER',
                        'Detected "%s", which you did not want.' % release_val,
                        site=self.name)
                    return True

            # if the filter option is "tags", search through it for that tag
            elif key == 'tags' and release_val is not None:
                tags = []
                for commastr in value.split(','):
                    tags.extend(commastr.split('\n'))

                try:
                    for tag in tags:
                        tag = tag.strip().lower()
                        if not tag:
                            continue

                        if tag[0] == '@':
                            tag = tag[1:]
                            val = release_val.strip()
                            if re.search(tag, val):
                                _msg = 'Detected %s match using "%s" in %s'
                                _msg = _msg % (key, tag, release_val)
                                out('FILTER', _msg, site=self.name)
                                return True
                            else:
                                continue

                        else:
                            retags = re.findall('[\w\._-]+', release_val)
                            for xt in retags:
                                if tag == xt:
                                    _msg = 'Detected %s match using "%s" in %s'
                                    _msg = _msg % (key, tag, release_val)
                                    out('FILTER', _msg, site=self.name)
                                    return True
                            continue

                        _msg = 'Did not detect %s match using "%s" in %s'
                        _msg = _msg % (key, tag, release_val)
                        out('FILTER', _msg, site=self.name)

                except Exception as e:
                    _msg = ('Tag error; tag: %s; key: %s; release_val: %s; '
                            'value: %s; error: %s')
                    _msg = _msg % (tag, key, release_val, value, e)
                    out('ERROR', _msg, site=self.name)

            # all tags match
            elif key == 'all_tags' and release['tags'] is not None:
                release_tags = release['tags'].lower()
                tags = []
                for commastr in value.split(','):
                    tags.extend(commastr.split('\n'))

                try:
                    for tag in tags:
                        tag = tag.strip().lower()
                        if not tag:
                            continue

                        if tag not in release_tags:
                            _msg = ('Did not detect match using %s. '
                                    'Announcement is missing "%s"')
                            _msg = _msg % (key, tag)
                            out('FILTER', _msg, site=self.name)
                            return False

                    out('FILTER',
                        'Detected match using all_tags.',
                        site=self.name)
                    return True

                except Exception as e:
                    _msg = ('Tag error; tag: %s; key: %s; release_val: %s; '
                            'value: %s; error: %s')
                    _msg = _msg % (tag, key, release_val, value, e)
                    out('ERROR', _msg, site=self.name)

            # if it's not a toggle option, size option, or tags option,
            # just check to make sure the values match
            elif release_val is not None:
                vals = []
                for commastr in value.split(','):
                    vals.extend(commastr.split('\n'))

                try:
                    for val in vals:
                        val = val.strip().lower()
                        if not val:
                            continue

                        if (val[0] == '@' and
                                re.match(val[1:], release_val)):
                            _msg = 'Detected %s match using "%s" in %s'
                            _msg = _msg % (key, val, release_val)
                            out('FILTER', _msg, site=self.name)
                            return True

                        elif val == release_val:
                            _msg = 'Detected %s match using "%s" in %s'
                            _msg = _msg % (key, val, release_val)
                            out('FILTER', _msg, site=self.name)
                            return True

                        else:
                            _msg = ('Did not detect %s match using "%s" '
                                    'in %s')
                            _msg = _msg % (key, val, release_val)
                            out('FILTER', _msg, site=self.name)

                    out('FILTER',
                        'Did not detect match in %s' % key,
                        site=self.name)

                except Exception as e:
                    _msg = ('Tag error; val: %s; key: %s; release_val: %s; '
                            'value: %s; error: %s')
                    _msg = _msg % (val, key, release_val, value, e)
                    out('ERROR', _msg, site=self.name)

        # not_filter options
        elif 'not_' in key:
            nkey = key.replace('not_', '')
            release_val = release.get(nkey)
            if release_val is not None:
                release_val = release_val.strip().lower()

                vals = []
                for commastr in value.split(','):
                    vals.extend(commastr.split('\n'))

                # if the not_filter option is not_tags,
                # search the values don't match them
                if nkey == 'tags':
                    try:
                        for tag in vals:
                            tag = tag.strip.lower()

                            if tag[0] == '@':
                                tag = tag[1:]
                                val = release_val.strip()
                                if re.search(tag, val):
                                    _msg = ('Detected %s present in %s, which '
                                            'is disallowed by %s')
                                    _msg = _msg % (tag, nkey, key)
                                    out('FILTER', _msg, site=self.name)
                                    return False
                                else:
                                    continue

                            else:
                                retags = re.findall('[\w\._-]+', release_val)
                                for xt in retags:
                                    if tag == xt:
                                        _msg = ('Detected %s present in %s, '
                                                'which is disallowed by %s')
                                        _msg = _msg % (tag, nkey, key)
                                        out('FILTER', _msg, site=self.name)
                                        return False
                                continue

                    except Exception as e:
                        _msg = ('Tag error; tag: %s; key: %s; '
                                'release_val: %s; value: %s; error: %s')
                        _msg = _msg % (tag, key, release_val, value, e)
                        out('ERROR', _msg, site=self.name)

                else:
                    try:
                        for val in vals:
                            val = val.strip().lower()
                            if not val:
                                continue

                            if (val[0] == '@' and
                                    re.match(val[1:], release_val)):
                                _msg = ('Detected %s present in %s, which is '
                                        'disallowed by %s')
                                _msg = _msg % (val, nkey, key)
                                out('FILTER', _msg, site=self.name)
                                return False

                            elif val == release_val:
                                _msg = ('Detected %s present in %s, which is '
                                        'disallowed by %s')
                                _msg = _msg % (val, nkey, key)
                                out('FILTER', _msg, site=self.name)
                                return False

                    except Exception as e:
                        _msg = ('Tag error; val: %s; key: %s; '
                                'release_val: %s; value: %s; error: %s')
                        _msg = _msg % (val, key, release_val, value, e)
                        out('ERROR', _msg, site=self.name)

            out('FILTER',
                'Did not detect any values present in "%s"' % key,
                site=self.name)
            return True
        else:
            out('FILTER',
                '"%s" was required but not found in this release' % key,
                site=self.name)
            return False

    def handle_announce(self, connection, e, cleanedmsg):
        global temp
        self.announcehistory.append(cleanedmsg)

        announce_lines = int(self.regex['announcelines'])
        while len(self.announcehistory) >= announce_lines:
            msg = ''
            for i in range(announce_lines):
                msg += self.announcehistory[i]

            args = {}
            args['text'] = msg
            args['type'] = e.eventtype()
            args['source'] = e.source()
            args['channel'] = e.target()
            args['event'] = e

            if G.TESTING:
                self.process_messages(msg, args)

            else:
                for th in self.threads:
                    if not th.isAlive():
                        del self.threads[self.threads.index(th)]

                th = threading.Thread(target=self.process_messages,
                                      args=(msg, args),
                                      name='pubmsg subthread')
                self.threads.append(th)
                self.threads[-1].setDaemon(1)
                self.threads[-1].start()

            del self.announcehistory[0]

    def handle_pubmsg(self, connection, e, cleanedmsg):
        source = e.source().lower()
        short_source = source[source.index('!') + 1:]
        nick_source = source[:source.index('!')]
        nickowner = self.creds['nickowner'].lower()
        message = e.arguments()[0]

        is_owner = (short_source == nickowner) or re.search(nickowner, source)
        if is_owner and nickowner != '' and message.startswith('%'):
            self.handleOwnerMessage(message, e.target(), nick_source)
        elif self.setup.get('chatter', '').lower() in ('1', 'true'):
            _msg = '%s:%s:%s:%s' % (self.name,
                                    e.target(),
                                    nick_source,
                                    message)
            out('DEBUG', _msg)

    def process_messages(self, announce, args):
        matched = False
        download_id = None

        for filtertype, reg in self.reg.items():
            m = reg.search(announce)
            if not m:
                break

            matched = True
            groups = self.regex[filtertype+'format'].split(', ')
            download_id = m.group(groups.index('downloadID') + 1)

            # throw announcement into database
            G.Q.put((self.name,
                     announce,
                     download_id))

            out('INFO', '**** Announce found: %s' % m.group(0), site=self.name)
            out('FILTER',
                'This is a(n) %s release' % filtertype,
                site=self.name)

            location, filter_key = self.should_download(m, filtertype)
            if location:
                _msg = '(%s) >> Download starting from %s'
                _msg = _msg % (download_id, self.name)
                out('INFO', _msg, self.name)

                filter_ = self.filters[filter_key]

                gmail = False
                filter_email = filter_.get('email')
                # if the filter is set to send an email on capture
                if filter_email == '1':
                    gmail = True

                # or the global email toggle is set,
                # and the filter email option exists and isn't disabled
                elif self.notif['email'] == '1' and filter_email != '0':
                    gmail = True

                notifi = False
                filter_notify = filter_.get('notify')
                # if the filter is set to send a notification on capture
                if filter_notify == '1':
                    notifi = True
                elif self.notif['message'] == '1' and filter_notify != '0':
                    notifi = True

                # does the announcement include a size limit?
                size_limit = False
                filter_limit = filter_['size'].strip()
                if filter_limit:
                    size_limit = filter_limit

                ret = download(download_id,
                               self.name,
                               location=location,
                               email=gmail,
                               filterName=filter_key,
                               announce=announce,
                               notify=notifi,
                               sizeLimits=size_limit)

                G.LOCK.acquire()
                G.REPORTS[self.name]['seen'] += 1
                if ret[0]:
                    G.REPORTS[self.name]['downloaded'] += 1
                G.LOCK.release()

            else:
                G.LOCK.acquire()
                G.REPORTS[self.name]['seen'] += 1
                G.LOCK.release()
                out('FILTER',
                    'There was no match with any %s filters' % filtertype,
                    site=self.name)

        if not matched:
            # why isn't this an announce?
            try:
                naughty = False
                intro_val = self.regex.get('intro')

                if intro_val is None:
                    naughty = True

                else:
                    intros = []
                    for commastr in intros:
                        intros.extend(commastr.split('\n'))

                    for intro in intros:
                        intro = intro.strip().lower()
                        clean_announce = announce.strip().lower()
                        if not intro:
                            continue

                        if (intro[0] != '@' and
                                clean_announce.startswith(intro)):
                            naughty = True
                        elif (intro[0] == '@' and
                                re.match(intro[1:], clean_announce)):
                            naughty = True

                if naughty:
                    out('DEBUG',
                        'Naughty announce: %s' % announce,
                        site=self.name)
                    if 'whatcd' in G.RUNNING:
                        G.RUNNING['whatcd'].naughty_announce(announce,
                                                             self.name)

                else:
                    out('DEBUG', 'NOT naughty: %s' % announce, site=self.name)

            except Exception as e:
                _msg = ('Exception raised when proccessing naughty announce '
                        '%s, error: %r') % (announce, e)
                out('ERROR', _msg)

        else:
            self.lastannounce = datetime.datetime.now()
            if download_id:
                self.lastannouncetext = download_id
            else:
                self.lastannouncetext = ''
                _msg = ('Did not find the download ID in the following '
                        'announce: %s') % announce
                out('ERROR', _msg, site=self.name)

    def strip_irc_colors(self, msg):
        msg = self.ircreg.sub('', msg)
        return msg

    def naughty_announce(self, announce, network):
        self.send_msg('#whatbot-debug', network + ":" + announce)

    def send_msg(self, msg, target):
        try:
            self.connection.privmsg(target, msg)
        except irclib.ServerNotConnectedError as e:
            _msg = 'Could not send "%s" to %s. Error: %r'
            _msg = _msg % (msg, target, e)
            out('ERROR', _msg, site=self.name)

    def send_whois(self, whonick, ownernetwork, ownertarget):
        self.ownernetwork = ownernetwork
        self.ownertarget = ownertarget
        self.havesendwhois = True

        if self.connection.is_connected():
            try:
                self.connection.whois((whonick,))
            except irclib.ServerConnectionError as e:
                out('ERROR', 'Server connection error: %r' % e, site=self.name)
            except irclib.ServerNotConnectedError as e:
                out('ERROR',
                    'Server not connected error: %r' % e.message(),
                    site=self.name)

        else:
            G.RUNNING[ownernetwork].send_msg('Cannot send whois as the bot is '
                                             'currently not connected to the '
                                             'network, try again later.',
                                             self.ownertarget)

    def send_whois_all(self, whonick, ownernetwork, ownertarget):
        self.ownernetwork = ownernetwork
        self.ownertarget = ownertarget
        self.havesendwhoisall.append(whonick.lower())

        if self.connection.is_connected():
            try:
                self.connection.whois((whonick,))
            except irclib.ServerConnectionError as e:
                out('ERROR', 'Server connection error: %r' % e, site=self.name)
            except irclib.ServerNotConnectedError as e:
                out('ERROR',
                    'Server not connected error: %r' % e.message(),
                    site=self.name)

    def send_whoami(self, ownernetwork, ownertarget):
        self.ownernetwork = ownernetwork
        self.ownertarget = ownertarget
        self.havesendwhoami = True

        if self.name == self.piggyback[0]:
            if self.connection.is_connected():
                try:
                    self.connection.whois((self.connection.real_nickname,))
                except irclib.ServerConnectionError as e:
                    out('ERROR',
                        'Server connection error: %r' % e,
                        site=self.name)
                except irclib.ServerNotConnectedError as e:
                    out('ERROR',
                        'Server not connected error: %r' % e.message(),
                        site=self.name)

    def part_channel(self, channel):
        try:
            if not channel.startswith('#'):
                channel = '#' + channel
            self.connection.part(channel, self.partPhrase)

        except irclib.ServerConnectionError as e:
            out('ERROR', 'Server connection error: %r' % e, site=self.name)
        except irclib.ServerNotConnectedError as e:
            out('ERROR',
                'Server not connected error: %r' % e.message(),
                site=self.name)

    def join_channel(self, channel):
        try:
            if not channel.startswith('#'):
                channel = '#' + channel
            self.connection.join(channel, self.partPhrase)

        except irclib.ServerConnectionError as e:
            out('ERROR', 'Server connection error: %r' % e, site=self.name)
        except irclib.ServerNotConnectedError as e:
            out('ERROR',
                'Server not connected error: %r' % e.message(),
                site=self.name)

    def join_other_channels(self):
        # Join the what.cd-debug channel if you're on the what-network
        if self.name == 'whatcd':
            self.join_channel('#whatbot-debug')

        extra_channels = self.creds.get('chanfilter')
        if extra_channels:
            for xchannel in extra_channels.split(','):
                for channel in xchannel.split('\n'):
                    channel = channel.strip()
                    if channel:
                        out('INFO',
                            'Joining channel: %s' % channel,
                            site=self.name)
                        self.join_channel(channel)

    def handle_welcome(self, connection, e):
        if connection == self.connection and self.piggyback[0] == self.name:
            self.lastdata = datetime.datetime.now()
            if self.connection.is_connected():
                if 'tempbotnick' in self.creds:
                    _ghost_msg = 'GHOST %s %s' % (self.creds['botnick'],
                                                  self.creds['nickservpass'])
                    self.connection.privmsg('nickserv', _ghost_msg)
                    self.connection.nick(self.creds['botnick'])
                    del self.creds['tempbotnick']

                _msg = 'Connected to %s, server calls itself %s.'
                _msg = _msg % (self.regex['server'],
                               self.connection.get_server_name())
                out('INFO', _msg, site=self.name)

            else:
                _msg = ('Connection was lost. Maybe you were g-lined? '
                        'Trying again.')
                out('ERROR', _msg, site=self.name)
                self.connect()

            _msg = ('Your bot\'s nickname MUST be registered with nickserv, '
                    'otherwise it will sit here and do nothing!')
            out('INFO', _msg, site=self.name)

    def handle_invite(self, connection, e):
        if connection == self.connection:
            self.lastdata = datetime.datetime.now()
            source = e.source()
            clean_src = source[source.index('!') + 1:].lower()
            botwho = self.regex['botwho'].lower()
            announce_chan = self.regex['announcechannel'].lower()
            invited_chan = e.arguments()[0]

            _msg = 'Invited by %s (%s, %s) to join %s (announce channel is %s)'
            _msg = _msg % (source,
                           clean_src,
                           botwho,
                           invited_chan,
                           announce_chan)
            out('DEBUG', _msg, site=self.name)

            if clean_src == botwho and invited_chan == announce_chan:
                out('DEBUG',
                    'Joining %s after invite.' % invited_chan,
                    site=self.name)
                self.connection.join(invited_chan)
                self.joined = True

    def handle_pub_message(self, connection, e):
        """Handles all non-PM messages received by the bot."""
        if connection == self.connection:
            self.lastdata = datetime.datetime.now()
            cleanedmsg = self.strip_irc_colors(e.arguments()[0])
            source = e.source()
            clean_src = source[source.index('!') + 1:].lower()
            target = e.target().lower()
            announce_chan = self.regex['announcechannel'].lower()

            if 'announcebotwho' in self.regex:
                who = self.regex['announcebotwho'].lower()
            else:
                who = self.regex['botwho'].lower()

            if clean_src == who and target == announce_chan:
                self.handle_announce(connection, e, cleanedmsg)
            else:
                self.handle_pubmsg(connection, e, cleanedmsg)

    def handle_priv_message(self, connection, e):
        """Handle messages sent through PM."""
        if connection == self.connection and self.piggyback[0] == self.name:
            self.lastdata = datetime.datetime.now()
            source = e.source()
            source_nick = source[:source.index('!')]
            clean_src = source[source.index('!') + 1:].lower()
            owner = self.creds['nickowner'].lower()
            message = e.arguments[0]

            if owner and (clean_src == owner or re.search(owner, source)):
                self.handleOwnerMessage(message, source_nick, source_nick)

            else:
                _msg = '%s:PM:%s:%s' % (self.name, source_nick, message)
                out('DEBUG', _msg, site=self.name)

    def handleAction(self, connection, e):
        """Handle messages sent as actions."""
        if connection == self.connection:
            self.lastdata = datetime.datetime.now()
            cleanedmsg = self.strip_irc_colors(e.arguments()[0])
            #make sure that we always use lower case!
            if 'announcebotwho' in self.regex:
                who = self.regex['announcebotwho'].lower()
            else:
                who = self.regex['botwho'].lower()
            if e.source()[e.source().index('!')+1:].lower() == who and e.target().lower() == self.regex['announcechannel'].lower():
                self.handle_announce(connection, e, cleanedmsg)
            else:
                self.handle_pubmsg(connection, e, cleanedmsg)

    def handleWhoIs(self, connection, e):
        if connection == self.connection and (self.havesendwhois or (e.arguments()[0].lower() in self.havesendwhoisall) or self.havesendwhoami):
            self.lastdata = datetime.datetime.now()
            out('DEBUG', 'Whois e.arguments()[0]: %s, full: %s' %(e.arguments()[0],repr(e.arguments())),site=self.name)
            if e.eventtype() == 'endofwhois':
                if self.havesendwhois:
                    self.havesendwhois = False
                    if self.ownernetwork != None and self.ownertarget != None:
                        G.RUNNING[self.ownernetwork].send_msg(self.who,self.ownertarget)
                        self.ownernetwork = None
                        self.ownertarget = None
                        self.who = list()
                elif self.havesendwhoisall:
                    try:
                        self.havesendwhoisall.remove(e.arguments()[0].lower())
                    except:
                        out('ERROR', 'Could not remove from havesendwhoisall, its now: %s' %repr(self.havesendwhoisall), site=self.name)
                    if self.ownernetwork != None and self.ownertarget != None:
                        info = None
                        if self.who != []:
                            try:
                                info = eval('{' + self.who[0] + '}')
                            except SyntaxError, e:
                                out('ERROR', 'Whoisall parsing error: %s' %e.arguments)
                                info = None
                                pass
                            if info:
                                botnick = info['User']
                                botident = "@".join(info['Info'][0:2])
                        if not info:
                            botnick = ""
                            botident = ""
                        if self.regex['botname'].lower() == botnick.lower():
                            botwho = self.regex['botwho']
                        elif 'announcebotname' in self.regex and 'announcebotwho' in self.regex and self.regex['announcebotname'].lower() == botnick.lower():
                            botwho = self.regex['announcebotwho']
                        else:
                            botwho = ''
                        if botident.lower() == botwho.lower() and info:
                            status = "OK"
                        elif not info:
                            status = "Bot is not online"
                        else:
                            status = "%s (whois) != %s (regex.conf)" %(botident, botwho)

                        msg = '%-16s %-15s %-s' %(self.name, botnick, status)

                        G.RUNNING[self.ownernetwork].send_msg(msg,self.ownertarget)
                        if not self.havesendwhoisall:
                            self.ownernetwork = None
                            self.ownertarget = None
                        self.who = list()
                elif self.havesendwhoami:
                    self.havesendwhoami = False
                    if self.ownernetwork != None and self.ownertarget != None:
                        if self.who != []:
                            try:
                                info = eval('{' + self.who[1] + '}')
                            except SyntaxError, e:
                                out('ERROR', 'WhoAmI parsing error: %s' %e.arguments)
                                info = None
                                pass
                            except IndexError, e:
                                info = None
                                out('ERROR', 'WhoAmI IndexError parsing error: %s' %e.arguments)
                                pass
                            if info:
                                if 'Channels' in info:
                                    channellist = info['Channels'][0].lower().split('#')
                                    isin = False
                                    for lita in channellist:
                                        litb = lita.split(' ')
                                        if self.regex['announcechannel'].lower().replace('#','') in litb:
                                            isin = True
                                    if isin:
                                        status = 'Ok'
                                    else:
                                        status = 'NOT in announce channel, channels are: %s' %info['Channels'][0]
                                else:
                                    status = 'NOT in announce channel'
                            else:
                                status = 'NOT in announce channel'
                        else:
                            status = ''
                        msg = '%-16s %-20s %-s' %(self.name, self.regex['announcechannel'], status)

                        G.RUNNING[self.ownernetwork].send_msg(msg,self.ownertarget)
                        self.ownernetwork = None
                        self.ownertarget = None
                        self.who = list()

            elif e.eventtype() == 'whoisuser':
                self.who.append("'User': '%s', 'Info': %s"%(e.arguments()[0],e.arguments()[1:]))
            elif e.eventtype() == 'whoischannels':
                self.who.append("'Channels': %s"%e.arguments()[1:])
            elif e.eventtype() == 'whoisserver':
                self.who.append("'Server info': %s"%e.arguments()[1:])
            else:
                self.who.append(e.arguments())

    def handleNameReply(self, connection, e):
        if self.connection == connection:
            self.lastdata = datetime.datetime.now()
            out('DEBUG','namereply received, %s:%s' %(e.arguments(),e.target()),site=self.name)
            #if 'whatcd' == self.name:
                #chan = e.arguments()[1]
                #if chan == "#whatbot-debug":
                    #self.send_msg("SuperSecretPW","pyWhatBot")
            #elif chan == "#whatbot":
            #    self.send_msg("SuperSecretPW","pyWhatBot")

    def handlePrivNotice(self, connection, e):
        if connection == self.connection:
            self.lastdata = datetime.datetime.now()
            out('INFO',"%s:%s" %(e.arguments(),e.target()),site=self.name)
            if 'password accepted' in e.arguments()[0].lower() and self.joined == False or 'you are now identified for' in e.arguments()[0].lower() and self.joined == False:
                if self.piggyback[0] == self.name:
                    out('INFO','You have identified with nickserv successfully.',site=self.name)
                self.logintochannels(connection, e)
            elif self.piggyback[0] == self.name:
                if (('please choose a different nick' in e.arguments()[0].lower() ) or ( 'You need to be identified to a registered account to join this channel' in e.arguments()[0].lower() )) and self.joined == False:
                    out('INFO',"Ident request received. Sending identify.",site=self.name)
                    if self.creds['nickservpass']:
                        self.connection.privmsg("nickserv","identify " + self.creds['nickservpass'])
                elif 'this nick is owned by someone else' in e.arguments()[0].lower() and self.joined == False:
                    out('INFO',"Ident request received. Sending identify.",site=self.name)
                    if self.creds['nickservpass']:
                        self.connection.privmsg("nickserv","identify " + self.creds['nickservpass'])
                elif 'You were forced to join' in e.arguments()[0]:
                    channel = e.arguments()[0][e.arguments()[0].index('#'):]
                    out('INFO','You were forced to join %s'%channel,site=self.name)
            else:
                out('DEBUG',"(%s)%s:%s" %(e.eventtype(),e.arguments(),e.target()),site=self.name)

    def logintochannels(self, connection, e):
        try: #if we are registered with ident
            if 'requiresauth' in self.regex and self.regex['requiresauth'] == '1':
                authstring = self.regex['authstring'].strip().rstrip()
                try:
                    if '$username' in authstring:
                        authstring = authstring.replace('$username', self.creds['username'])
                    if '$irckey' in authstring:
                        authstring = authstring.replace('$irckey', self.creds['irckey'])
                    if '$password' in authstring:
                        authstring = authstring.replace('$password', self.creds['password'])
                    if '$authchan' in authstring:
                        authstring = authstring.replace('$authchan', self.regex['authchan'])
                    if '$announcechan' in authstring:
                        authstring = authstring.replace('$announcechan', self.regex['announcechannel'])
                except KeyError, e:
                    #spit out an error because that site is missing a certain requirement
                    out('ERROR', 'authstring is incomplete: Error %s' %str(e.message),site=self.name)
                    pass
                if 'authchan' in self.regex:
                    out('INFO',"Joining channel: %s by logging in with %s" %(self.regex['authchan'],self.regex['botname']),site=self.name)
                else:
                    out('INFO',"Joining channel: %s by logging in with %s" %(self.regex['announcechannel'],self.regex['botname']),site=self.name)
                self.connection.privmsg(self.regex['botname'],"%s" %authstring)
            elif 'requiresauth' in self.regex and self.regex['requiresauth'] == '2':
                if 'channelpassword' in self.creds and self.creds['channelpassword'] != '':
                    irckey = self.creds['channelpassword']
                    out('INFO','Joining channel %s' %(self.regex['announcechannel']),site=self.name)
                    self.connection.join(self.regex['announcechannel'], irckey)
                else:
                    out('ERROR', 'Cannot join announce channel, this site requires to have the channelpassword set in creds.conf.',site=self.name)
            else:
                out('INFO',"Joining channel: %s" %(self.regex['announcechannel']),site=self.name)
                self.connection.join(self.regex['announcechannel'])
            if 'cmd' in self.creds and self.creds['cmd'] != '':
                self.connection.send_raw(self.creds['cmd'])
            self.joined = True

            self.connection.execute_delayed(1, self.join_other_channels)

        except irclib.ServerConnectionError, e:
            out('ERROR','Server Connection Error: %s' %repr(e),site=self.name)
        except irclib.ServerNotConnectedError, e:
            out('ERROR','Server Not Connected Error: %s' %repr(e.message()),site=self.name)


    def handleCurrentTopic(self, connection, e):
        if connection == self.connection:
            self.lastdata = datetime.datetime.now()
            channel = e.arguments()[0]
            topic = self.strip_irc_colors(e.arguments()[1])
            out('INFO','handleCurrentTopic: %s: %s'%(channel, topic),site=self.name)

    def handleNickInUse(self, connection, e):
        if connection == self.connection and self.piggyback[0] == self.name:
            self.lastdata = datetime.datetime.now()
            if 'ircallowednick' in self.creds and self.joined == False:
                out('ERROR','The nickname %s was already in use. I cannot join the announce channel without it, so I am disconnecting.' %(self.creds['ircallowednick']),site=self.name)
                self.disconnect()
            else:
                newnick = self.creds['botnick'] +'|' + str(random.randint(1000,3000))
                out('ERROR','The nickname %s was already in use. You have been renamed as %s.' %(self.creds['botnick'],newnick),site=self.name)
                self.connection.nick(newnick)
                self.creds['tempbotnick'] = newnick

    def handleError(self, connection, e):
        if connection == self.connection and self.piggyback[0] == self.name:
            self.lastdata = datetime.datetime.now()
            out('ERROR',"%s:%s:%s" %(e.arguments(),e.target(),repr(e)),site=self.name)
            con = self.connection.is_connected()
            if con:
                pass
            #this is all here cause for some reason python's SSL or TCP or whatever header checksums are bad, therefore causing the bot to disconnect after sending a NICK command during an initial connection if the current nick is already used. This is to get around that.

            if 'closing link' in e.target().lower():
                self.connection.disconnect('Cause it broke')
                out('INFO',"Waiting a few seconds before reconnect.",site=self.name)
                self.connection.execute_delayed(15, self.connect)

    def handlePong(self, connection, e):
        #pong received. Shall we bother calculating the lag?
        if connection == self.connection and self.piggyback[0] == self.name:
            self.lastdata = datetime.datetime.now()
            if self.pingsent:
                timediff = datetime.datetime.now() - self.pingsent
                self.pingsent = False
                out('DEBUG','Pong received from %s, roundtrip time %.2f s' %(e.arguments()[0],(timediff.microseconds + (timediff.seconds + timediff.days * 24 * 3600) * 10**6) / 10**6),site=self.name)
            else:
                out('DEBUG','Pong received from %s, NOT ASKED FOR'  %(e.arguments()[0]),site=self.name)

    def handlenosuchnick(self, connection, e):
        #nosuchnick received. Possible reasons: whois / msg someone.
        if connection == self.connection:
            out('DEBUG','nosuchnick received, arguments are %s' %e.arguments(),site=self.name)


    def handleAllDebug(self, connection, e):
        if connection == self.connection and self.piggyback[0] == self.name:
            self.lastdata = datetime.datetime.now()
            args = {}
            args["type"] = e.eventtype()
            args["source"] = e.source()
            args["channel"] = e.target()
            args["event"] = e
            if e.eventtype() == 'error':
                out('ERROR',"%s:%s" %(e.arguments(),e.target()),site=self.name)
            else:
                if e.eventtype() == 'nosuchnick' and e.arguments()[0].lower() == 'pywhatbot':
                    pass
                else:
                    out('DEBUG',"(%s)%s:%s:%s" %(e.eventtype(),e.source(),e.arguments(),e.target()),site=self.name)

    def testtimeout(self):
        if self.name in G.RUNNING.keys() or self.connection.is_connected():
            if self.piggyback[0] == self.name:
                if self.pingsent:
                    self.pingsent= False
                    out('ERROR','Connection timed out, PONG was not received within 30s. Disconnecting, wait(15), and reconnect',site=self.name)
                    self.connection.disconnect('Cause it broke')
                    self.connection.execute_delayed(15, self.connect)
                else:
                    #out('DEBUG','Testtimeout function called, adding new timer',site=self.name)
                    td =  datetime.datetime.now() - self.lastdata
                    tds = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

                    err = False
                    if tds > 120:
                        out('DEBUG','ping server as 120 seconds without data have passed',site=self.name)

                        try:
                            self.connection.ping(self.connection.server)
                        except irclib.ServerNotConnectedError, e:
                            out('ERROR', 'Lost connection to server, %s. Disconnecting, wait(15), and reconnect' %e, site=self.name)
                            err = True
                        if err:
                            self.connection.disconnect('Cause it broke')
                            self.connection.execute_delayed(15, self.connect)
                        else:
                            self.pingsent = datetime.datetime.now()

                    if not err: self.connection.execute_delayed(10, self.testtimeout)
            else:
                out('DEBUG','Piggybacks have shifted: %s - moving execute_delayed to %s' %(repr(self.piggyback),self.piggyback[0]),site=self.name)
                G.RUNNING[self.piggyback[0]].testtimeout()
        else:
            out('DEBUG','Can\'t ping, as we are currently not connected to the network',site=self.name)
            self.pingsent = False


    def handleOwnerMessage(self, msg, target, ownernick):
        """Take commands from the operator. That's right, bow down."""
        if self.piggyback[0] == self.name:
            quit = {
                    'help':'Disconnects from all NETWORKS and closes all threads.   [pyWHATauto]',
                    'cmd':self.fquit
                    }
            whois = {
                        'help':'Returns a whois on the target name and network. Format %whois <network/alias> <nickname>   [pyWHATauto]',
                        'cmd':self.fwhois
                        }
            whoisall = {
                        'help':'Returns a whois on the announcebots in all networks. Careful, its quite spammy.   [pyWHATauto]',
                        'cmd':self.fwhoisall
                        }
            whoami = {
                        'help':'Returns a whois of all bots in all networks. Careful, its quite spammy.   [pyWHATauto]',
                        'cmd':self.fwhoami
                        }
            update = {
                    'help':'Updates your regex.conf to the newest version.   [pyWHATauto]',
                    'cmd':self.fupdate
                    }
            cmd = {
                'help':'Sends a raw IRC command through the bot. Format %cmd <network/alias> <IRCCOMMAND> <values>. Please use the pyWHATauto commands if available, otherwise use this. For a list of IRC Commands and how to use them: http://en.wikipedia.org/wiki/List_of_Internet_Relay_Chat_commands.   [pyWHATauto]',
                'cmd':self.fcmd
                }
            ragequit = {
                        'help':"You're angry, and you're gonna let them know it!",
                        'cmd':self.fragequite
                        }
            filter = {
                    'help':'Allows you to control filter states, as well as list enabled/disabled filters. Type %filter <enable/disable> <filtername> to toggle a filter.    [pyWHATauto]',
                    'cmd':self.ffilter
                    }
            filters = {
                    'help':'Allows you to control filter states, as well as list enabled/disabled filters.   [pyWHATauto]',
                    'cmd':self.ffilter
                    }
            connect = {
                    'help':'Connects to a network. Format %connect <network> <network2> ....   [pyWHATauto]',
                    'cmd':self.fconnect
                    }
            free = {
                    'help':'Outputs the amount of free space on the drive specified in setup.conf.   [pyWHATauto]',
                    'cmd':self.ffree
                    }
            reload = {
                    'help':'Reloads all configs.   [pyWHATauto]',
                    'cmd':self.freload
                    }
            nick = {
                    'help':'Changes the bots nickname to whatever you pass it. Does not change what the bot thinks it calls itself, so a %ghost command will ignore your changes.   [pyWHATauto]',
                    'cmd':self.fnick
                    }
            join = {
                    'help':'Joins the specified channel(s). You can join local channels as well as cross-network. Format %join <network/alias> #<channel> #<channel> ...   [pyWHATauto]',
                    'cmd':self.fjoin
                    }
            part = {
                    'help':'Parts the specified channel(s). You can part local channels as well as cross-network. Format %part <network/alias> #<channel> #<channel> ...   [pyWHATauto]',
                    'cmd':self.fpart
                    }
            stats = {
                    'help':'Gives seen and download statistics on each enabled network.   [pyWHATauto]',
                    'cmd':self.fstats
                    }
            time = {
                    'help':'Outputs the local system time from where the bot resides.   [pyWHATauto]',
                    'cmd':self.ftime
                    }
            cycle = {
                    'help':'Rejoins a channel. Syntax: \'%cycle\' rejoins the current channel, \'%cycle <channel>\' rejoins <channel>, \'%cycle <network/alias> <channel>\' rejoins <channel> on <network/alias>.   [pyWHATauto]',
                    'cmd':self.fcycle
                    }
            sites = {
                    'help':'Lists the currently enabled NETWORKS/sites and their WHATauto names.   [pyWHATauto]',
                    'cmd':self.fsites
                    }
            disconnect = {
                        'help':'Disconnects from the specified network. Format: %disconnect <site>. Ex: %disconnect whatcd.   [pyWHATauto]',
                        'cmd':self.fdisconnect
                        }
            download = {
                        'help':'Downloads torrents manually from a network. Format: %download <site/alias> <torrentID> (<torrentID>) ..... For a list of site names try %sites.   [pyWHATauto]',
                        'cmd':self.fdownload
                        }
            version = {
                    'help':'Outputs the current running version to the channel.   [pyWHATauto]',
                    'cmd':self.fversion
                    }
            ghost = {
                    'help':'Ghosts the nickname set in config.   [pyWHATauto]',
                    'cmd':self.fghost
                    }
            current = {
                    'help':'Sends you a private message outputting your current filters.   [pyWHATauto]',
                    'cmd':self.fcurrent
                    }
            statsreset = {
                        'help':'Resets the stats on seen/downloaded.   [pyWHATauto]',
                        'cmd':self.fstatsreset
                        }
            uptime = {
                    'help':'Outputs how long the bot has been running.   [pyWHATauto]',
                    'cmd':self.fuptime
                    }
            help = {
                    'help':'You sir, are an idiot.   [pyWHATauto]',
                    'cmd':self.fhelp
                    }

            #The dictionary of commands
            commands = {
                'quit':quit,
                'free':free,
                'drive':free,
                'join':join,
                'part':part,
                'stats':stats,
                'update':update,
                'cycle':cycle,
                'download':download,
                'disconnect':disconnect,
                'time':time,
                'cmd':cmd,
                'whois':whois,
                'whoisall':whoisall,
                'whoami':whoami,
                'statsreset':statsreset,
                'ghost':ghost,
                'ragequit':ragequit,
                'filter':filter,
                'filters':filters,
                'status':stats,
                'help':help,
                'connect':connect,
                'uptime':uptime,
                'reload':reload,
                'current':current,
                'nick':nick,
                'sites':sites,
                'version':version,
                }

            cmds = msg.rstrip().split(' ')
            if cmds[0] != '' and cmds[0][0] ==  '%': #test if the msg is a potential command
                rootcmd = cmds[0][1:]
                if rootcmd in commands: #test if it's a real command
                    if len(cmds) > 1: #is this a single part command, or does it have options?
                        if cmds[1] == 'help':
                            #dic.get('a',default)('WHAT','noob')
                            self.send_msg(commands[rootcmd]['help'], target)
                        else:
                            switches = list()
                            for item in cmds[1:]:
                                switches.append(item)
                            var = [target, switches, commands, ownernick]
                            stupid = commands[rootcmd]
                            stupid.get('cmd')(var)
                    else: #this is a single-part message
                        var = [target, None, commands, ownernick]
                        stupid = commands[rootcmd]
                        stupid.get('cmd')(var)
                else:
                    self.send_msg('That is not a valid command. Try %help for the list of available commands.',target)

    def fquit(self, vars):
        out('CMD','quit',site=self.name)
        out('INFO','I have received the quit command!',site=self.name)
        for bot in G.RUNNING.itervalues():
            bot.disconnect()
        G.LOCK.acquire()
        #global EXIT
        G.EXIT = True
        G.LOCK.release()
        sys.exit()

    def fragequite(self, vars):
        self.partPhrase=":AND I'M NEVER COMING BACK!"
        out('CMD','quit',site=self.name)
        out('INFO','I have received the quit command!',site=self.name)
        target = vars[0]
        angorz = ["RRRRrrraaaaggggeee.", "I'm backtracing your IPs right now. You're so dead.", "I'm calling the FBI on you. What's the number, do you know?","I'm going to tell my daddy on you. He's real big where he works. Like an elephant.", "I'm so hacking through your ports right nao!", "FFFFFFFUUUUUUUUUUUUUUU", "You guys are fucking assholes!", "I'M SO ANG0RZ RIGHT NAO!", "STOP TOUCHING ME!", "Fuck this place. I'm way cooler than you.", "Who you gonna call?"]
        from random import choice
        self.send_msg(choice(angorz), target)
        self.send_msg("BTW, here's a link to my blog: http://perezhilton.com/", target)
        self.part_channel(target)
        for bot in G.RUNNING.itervalues():
            bot.disconnect()
        G.LOCK.acquire()
        #global EXIT
        G.EXIT = True
        G.LOCK.release()
        sys.exit()

    def ffilter (self,vars):
        target = vars[0]
        if vars[1] != None:
            if vars[1][0].lower() == 'list':
                #print out the list of filters that have been toggled
                G.LOCK.acquire()
                #if there are any items in the changed filters list
                if len(G.FILTERS_CHANGED) > 0:
                    self.send_msg('Manually toggled filters:',target)
                    for key, value in G.FILTERS_CHANGED.items():
                        self.send_msg('%s: %s'%(key, value), target)
                self.send_msg('Unchanged filters:',target)
                for key, value in G.FILTERS.items():
                    if key not in G.FILTERS_CHANGED:
                        self.send_msg('%s: %s'%(key, value), target)
                G.LOCK.release()
            elif vars[1][0].lower() == 'enable' and len(vars[1]) == 2:
                #toggle the filter to enable it
                G.LOCK.acquire()
                if vars[1][1].lower() in G.FILTERS: #does the filter exist?
                    #then the filter is legit, so enable it
                    G.FILTERS_CHANGED[vars[1][1].lower()] = '1'
                    #Does changing the filter state put it back to it's original value? If so, delete it from the changed list
                    if G.FILTERS_CHANGED[vars[1][1].lower()] == G.FILTERS[vars[1][1].lower()]:
                        del G.FILTERS_CHANGED[vars[1][1].lower()]
                    reloadConfigs()
                    self.send_msg('Filter %s has been toggled on.   [pyWHATauto]'%vars[1][1].lower(), target)
                else:
                    #then tell them the filter doesn't exist and how to get a list of filters
                    self.send_msg("That filter doesn't exist. Try again!", target)
                    pass
                G.LOCK.release()
            elif vars[1][0].lower() == 'disable' and len(vars[1]) == 2:
                #toggle the filter to disable it
                G.LOCK.acquire()
                if vars[1][1].lower() in G.FILTERS: #does the filter exist?
                    #then the filter is legit, so disable it
                    G.FILTERS_CHANGED[vars[1][1].lower()] = '0'
                    #Does changing the filter state put it back to it's original value? If so, delete it from the changed list
                    if G.FILTERS_CHANGED[vars[1][1].lower()] == G.FILTERS[vars[1][1].lower()]:
                        del G.FILTERS_CHANGED[vars[1][1].lower()]
                    reloadConfigs()
                    self.send_msg('Filter %s has been toggled off.   [pyWHATauto]'%vars[1][1].lower(), target)
                else:
                    #the filter doesn't exist
                    self.send_msg("That filter doesn't exist. Try again!   [pyWHATauto]", target)
                G.LOCK.release()
            else:
                #incorrect command, give info
                self.send_msg('Incorrect command structure. What does that even mean?   [pyWHATauto]', target)
        else:
            out('CMD','filter, incomplete',site=self.name)
            self.send_msg('Filters. Like on cigarettes, except a lot healthier. Try typing %help filter to see how they are used.   [pyWHATauto]', target)

    def fdisconnect(self, vars):
        target = vars[0]
        if vars[1] is not None:
            network = vars[1][0]
            out('CMD', 'disconnect %s' %network,site=self.name)
            #if it's an alias
            if network.lower() in self.fromalias.keys():
                network = self.fromalias[network.lower()]

                if network in G.RUNNING:
                    G.RUNNING[network].disconnect()
                    out('DEBUG','piggyback before: %s' %repr(G.RUNNING[network].piggyback),self.name)
                    if len(G.RUNNING[network].piggyback) > 1:
                        G.RUNNING[network].piggyback.remove(network)
                        G.RUNNING[network].part_channel(G.RUNNING[network].regex['announcechannel'])
                        self.send_msg('I have disconnected from %s. However %s use the same connection, so only the announce channel was parted.  [pyWHATauto]'%(network, repr(G.RUNNING[network].piggyback)), target)
                        out('DEBUG','piggyback after: %s' %repr(G.RUNNING[network].piggyback),self.name)
                    else:
                        self.send_msg('I have disconnected from %s.   [pyWHATauto]'%network, target)
                        out('DEBUG','piggyback after: %s, %s will be removed' %(repr(G.RUNNING[network].piggyback), network),self.name)
                    G.LOCK.acquire()
                    del G.RUNNING[network]
                    G.LOCK.release()
                else:
                    self.send_msg('I cannot disconnect from %s since the network is not running.   [pyWHATauto]'%network, target)

            else:
                self.send_msg('I do not know the network/alias %s. Format: %%disconnect <network>   [pyWHATauto]' %network, target)
        else:
            self.send_msg('That is not a full command. Format: %disconnect <network>   [pyWHATauto]', target)

    def fnick(self, vars):
        if vars[1] != None:
            name = vars[1][0]
            out('CMD','nick change from %s to %s' %(self.connection.nickname, name),site=self.name)
            self.connection.nick(name)

    def fwhois(self, vars):
        if vars[1] != None:
            out('DEBUG', 'whois send, number of vars: %d, vars 0, 1: %s, %s ' %(len(vars),repr(vars[0]), repr(vars[1])),site=self.name)
            target = vars[0]
            if len(vars[1]) < 2:
                self.send_msg('Incorrect command structure. It should be %whois site nick   [pyWHATauto]', target)
            else:
                name = vars[1][1]
                network = vars[1][0]
                if network.lower() in self.fromalias.keys():
                    network = self.fromalias[network.lower()]

                    out('CMD','Whois sent for %s on %s'%(name, network),site=self.name)
                    if network in G.RUNNING:
                        G.RUNNING[network].send_whois(name,self.name,target)
                    else:
                        self.send_msg('You are currently not connected to %s, so I cannot send the whois request.   [pyWHATauto]' %network ,target)
                else:
                    self.send_msg('I do not know the network/alias %s. Format: %%disconnect <network>   [pyWHATauto]' %network, target)


    def fwhoisall(self,vars):
        out('DEBUG','Whoisall was sent.',site=self.name)
        target = vars[0]
        self.send_msg('%-16s %-15s %-s' %('Network', 'Botnick', 'Status'), target)
        for key, network in G.RUNNING.items():
            out('CMD','Whois sent for %s on %s'%(network.regex['botname'],key),site=self.name)
            network.send_whois_all(network.regex['botname'],self.name,target)
            if 'announcebotname' in network.regex:
                out('CMD','Whois sent for %s on %s'%(network.regex['announcebotname'],key),site=self.name)
                network.send_whois_all(network.regex['announcebotname'],self.name,target)

    def fwhoami(self,vars):
        out('DEBUG','whoami was sent.',site=self.name)
        target = vars[0]
        self.send_msg('%-16s %-20s %-s' %('Network', 'Announce Channel', 'Status'), target)
        for key, network in G.RUNNING.items():
            out('CMD','Whois whoami on %s'%key,site=self.name)
            network.send_whoami(self.name,target)

    def ffree(self, vars):
        target = vars[0]
        msg = vars[1]
        out('CMD','free',site=self.name)
        if os.name == 'nt':
            if WIN32FILEE:
                free, percent = getDriveInfo(self.setup['drive'])
                msg = '**Free Space on %s: %s GB (%s%%)   [pyWHATauto]' %(self.setup['drive'], round(free/1024/1024/1024,2), round(float(percent*100),2))
            else:
                msg = 'Uhh.. I need to install win32file for this to work.'
        elif os.name == 'posix':
            try:
                free, percent = getDriveInfo(self.setup['drive'])
                msg = '**Free Space on %s: %s GB (%s%%)   [pyWHATauto]' %(self.setup['drive'], round(free,2), round(float(percent*100),2))
            except TypeError, e:
                out('ERROR',"There was an error. Double check 'drive' in setup.conf. Error: %s" %repr(e),site=self.name)
                msg = "There was an error. Double check 'drive' in setup.conf."
        if msg != None:
            self.send_msg(msg, target)

    def freload(self, vars):
        target = vars[0]
        out('CMD','reload',site=self.name)
        reloadConfigs()
        self.send_msg('All configs (filters, setup, etc) have been reloaded.   [pyWHATauto]', target)

    def fupdate(self, vars):
        target = vars[0]
        out('CMD','update',site=self.name)
        try:
            webFile = urllib.urlopen('http://bot.whatbarco.de/update/version')
            x=webFile.read().split('\n')
            webFile.close()
            minversion=x[0]
            regversion=x[1]
            if float(minversion) <= float(VERSION.replace('v','')):
                if int(regversion) > G.REGVERSION:
                    regUpdate = urllib.urlopen('http://bot.whatbarco.de/update/regex.conf')
                    localFile = open(os.path.join(G.SCRIPTDIR,'regex.conf'), 'w')
                    localFile.write(regUpdate.read())
                    regUpdate.close()
                    localFile.close()
                    reloadConfigs()
                    self.send_msg("Your regex.conf file has been updated to the latest version.   [pyWHATauto]", target)
                else:
                    self.send_msg("You are currently running the latest regex.conf file.   [pyWHATauto]", target)
            else:
                self.send_msg("You need to update pyWA before you can use the new regex. You are using %s, but %s is required.   [pyWHATauto]"%(VERSION,"v"+str(minversion)), target)
        except Exception, e:
            out('ERROR',"Something happened when trying to update. %s"%e,site=self.name)

    def fjoin(self, vars):
        target= vars[0]
        cmds = vars[1]
        out('CMD','join %s' %cmds,site=self.name)
        if cmds and len(cmds) >1:
            if cmds[0].lower() in self.fromalias.keys():
                network = self.fromalias[cmds[0].lower()]
                if network in G.RUNNING:
                    self.send_msg('I am attempting to join %s on %s'%(cmds[1:],network), target)
                    out('INFO','Joining channels %s on %s'%(cmds[1:],network), site=self.name)
                    for channel in cmds[1:]:
                        G.RUNNING[network].join_channel(channel)
                else:
                    out('INFO','You tried to join a channel on a network (%s) that is not currently running' %network,self.name)
                    self.send_msg('I cannot join %s on %s since it is not currently connected   [pyWHATauto]'%(cmds[1:],network), target)
            else:
                self.send_msg('I do not recognise the network/alias. Try %sites for all available networks   [pyWHATauto]', target)
        else:
            self.send_msg('Incorrect format for %join. The format should be %join <network/alias> #<channel> #<channel> ...  [pyWHATauto]', target)


    def fconnect(self, vars):
        target = vars[0]
        network = vars[1]

        out('CMD','connect %s'%network,site=self.name)
        if network is not None:
            for net in network:
                if net.lower() in self.fromalias.keys():
                    msg = establishBot(self.fromalias[net.lower()])
                    self.send_msg(msg, target)
                else:
                    self.send_msg('I do not recognise the network/alias %s' %net, target)
                    out('DEBUG','Unknown network/alias: %s' %net,site=self.name)
        else:
            self.send_msg('Incorrect command structure for %connect, it should be %connect <network> <network2> ....   [pyWHATauto]', target)

    def fpart(self, vars):
        target= vars[0]
        cmds = vars[1]
        out('CMD','part %s' %cmds,site=self.name)
        if cmds != None and len(cmds) >1:
            if cmds[0].lower() in self.fromalias.keys():
                network = self.fromalias[cmds[0].lower()]
                if network in G.RUNNING:
                    self.send_msg('I am attempting to part %s on %s'%(cmds[1:],network), target)
                    out('INFO','Parting channels %s on %s'%(cmds[1:],network), self.name)
                    for channel in cmds[1:]:
                        G.RUNNING[network].part_channel(channel)
                else:
                    out('INFO','You tried to part a channel on a network (%s) that is not currently running' %network,self.name)
                    self.send_msg('I cannot part %s on %s since it is not currently connected   [pyWHATauto]'%(cmds[1:],network), target)
            else:
                self.send_msg('I do not recognise the network/alias. Try %sites for all available networks   [pyWHATauto]', target)
        else:
            self.send_msg('Incorrect format for %part. The format should be %part <network/alias> #<channel> #<channel> ...   [pyWHATauto]', target)

    def fstats(self, vars):
        target = vars[0]
        #msg = vars[1]
        out('CMD','stats to %s' %target,site=self.name)
        G.LOCK.acquire()
        seenlen = 4
        downlen = 4
        sitelen = 4
        lastlen = len('Last Announce')
        idlen = len('DownloadID')

        for site, link in G.RUNNING.iteritems():
            try:
                seen = G.REPORTS[site]['seen']
                downloaded = G.REPORTS[site]['downloaded']
                if len(str(seen)) > seenlen:
                    seenlen = len(str(seen))
                if len(str(downloaded)) > downlen:
                    downlen = len(str(downloaded))
                if len(site) > sitelen:
                    sitelen = len(site)
                if len(link.lastannouncetext) > idlen:
                    idlen = len(link.lastannouncetext)
            except KeyError, e:
                out('ERROR','No reports yet for %s'%e,site=self.name)

        self.send_msg('%-*s %*s %*s %*s %*s' %(sitelen+1, 'Site', seenlen +2, 'Seen', downlen +2, 'Down', lastlen +2, 'Last Announce', idlen+2, 'DownloadID'), target)
        for site in sorted(G.RUNNING.iterkeys()):
            try:
                if G.RUNNING[site].lastannounce:
                    diff = datetime.datetime.now() - G.RUNNING[site].lastannounce
                    seconds = (diff.microseconds + (diff.seconds + diff.days * 24 * 3600) * 10**6) / 10**6
                    hours = int( seconds // (60*60) )
                    minutes = int((seconds - hours*60*60) // 60)
                    seconds = int(math.floor((seconds - hours*60*60 - minutes*60)))
                    string = ""
                    if hours > 0: string += " %d" %hours + "h"
                    if minutes >0 or hours >0: string += " %d" %minutes +"m"
                    string += " %d" %seconds + "s"
                else:
                    string = ""
                self.send_msg('%-*s %*s %*s %*s %*s' %(sitelen+1, site, seenlen+2, str(G.REPORTS[site]['seen']), downlen +2, str(G.REPORTS[site]['downloaded']), lastlen +2, string, idlen+2, G.RUNNING[site].lastannouncetext), target)
            except KeyError, e:
                out('ERROR','No reports yet for %s'%e,site=self.name)
        G.LOCK.release()

    def ftime(self, vars):
        target = vars[0]
        out('CMD','time',site=self.name)
        self.send_msg(datetime.datetime.now().strftime("The date is %A %d/%m/%Y and the time is %H:%M:%S.   [pyWHATauto]"), target)

    def fcycle(self, vars):
        target = vars[0]
        if not vars[1]:
            out('CMD','cycle '+target,site=self.name)
            self.connection.part(target)
            self.connection.join(target)
        elif len(vars[1]) == 1:
            out('CMD','cycle '+ vars[1][0],site=self.name)
            self.send_msg('Cycling channel %s   [pyWHATauto]'%vars[1][0], target)
            self.connection.part(vars[1][0])
            self.connection.join(vars[1][0])
        else:
            if vars[1][0].lower() in self.fromalias.keys():
                network = self.fromalias[vars[1][0].lower()]
                if network in G.RUNNING:
                    self.send_msg('Cycling channel %s on %s   [pyWHATauto]' %(vars[1][1], network), target)
                    G.RUNNING[network].part(vars[1][1])
                    G.RUNNING[network].join(vars[1][1])
                else:
                    self.send_msg('I cannot cycle %s on %s since it is not currently connected.   [pyWHATauto]'%(vars[1][1],network), target)
            else:
                self.send_msg('Incorrect command structure. Syntax: \'%cycle\' rejoins the current channel, \'%cycle <channel>\' rejoins <channel>, \'%cycle <network/alias> <channel>\' rejoins <channel> on <network/alias>.    [pyWHATauto]', target)



    def fsites(self, vars):
        target = vars[0]
        out('CMD','sites',site=self.name)
        G.LOCK.acquire()
        self.send_msg('Site Names: ', target)
        run = '[RUNNING] '
        for site in G.RUNNING.iterkeys():
            runo = run
            if self.toalias[site] == site:
                run += "%s, " %site
            else:
                run += "%s=%s, " %(site,self.toalias[site])
            if len(run) >= 350:
                self.send_msg(runo[0:-2], target)
                run = run[len(runo):]
        self.send_msg(run[0:-2], target)
        avail = '[AVAILABLE] '
        for site in G.NETWORKS.iterkeys():
            if not site in G.RUNNING:
                ava = avail
                if site == self.toalias[site]:
                    avail += "%s, " %site
                else:
                    avail += "%s=%s, " %(site, self.toalias[site])
            if len(avail) >= 350:
                self.send_msg(ava[0:-2], target)
                avail = avail[len(ava):]
        avail = avail[0:-2] + '   [pyWHATauto]'
        G.LOCK.release()
        self.send_msg(avail, target)

    def fcmd(self,vars):
        target = vars[0]
        if vars[1] and len(vars[1]) >= 2:
            network = vars[1][0]
            cmd = ' '.join(vars[1][1:])
            out('CMD','cmd: %s'%cmd,site=self.name)
            if network.lower() in self.fromalias:
                network = self.fromalias[network.lower()]
                if network in G.RUNNING.keys():
                    G.RUNNING[network].connection.send_raw(cmd)
                else:
                    self.send_msg('I cannot send the raw command \'%s\' on %s since it is not currently connected.   [pyWHATauto]'%(cmd,network), target)
            else:
                self.send_msg('I do not know the network/alias %s.   [pyWHATauto]'%network, target)
        else:
            self.send_msg('That is not a full command. Syntax: \'%cmd <network> <cmd>\' Example: \'%cmd whatcd privmsg :johnnyfive Are you alive?\' Will send a private message to johnnyfive on whatcd.',target)

    def fdownload(self, vars):
        target = vars[0]
        if vars[1] and len(vars[1]) >= 2:
            if vars[1][0].lower() in self.fromalias.keys():
                site = self.fromalias[vars[1][0].lower()]
                ids = vars[1][1:]
                for id in ids:
                    self.send_msg('Downloading %s from %s.    [pyWHATauto]'%(id, site), target)
                    if G.TESTING:
                        download(id, site, network=self, target=target)
                    else:
                        kwargs = {'network':self,'target':target}
                        thread.start_new_thread(download, (id, site), kwargs)
            else:
                self.send_msg('That site name does not seem valid. Type %sites to see a full list.   [pyWHATauto]', target)
        else:
            self.send_msg('That is not a full command. Format: %download <site/alias> <torrentID> (<torrentID>) ....    [pyWHATauto]' , target)

    def fhelp(self, vars):
        target = vars[0]
        switch = vars[1]
        commands = vars[2]
        out('CMD','help %s'%(switch),site=self.name)
        if switch is None:
            self.send_msg('Commands: %help <topic>, %current, %update, %filter, %quit, %connect, %disconnect, %time, %uptime, %stats, %statsreset, %version, %sites, %free/%drive, %join, %whois, %part, %download, %reload, %whoisall, %whoami, %update, %cycle, %ghost, %nick, %cmd   [pyWHATauto]', target)
        else:
            try:
                self.send_msg(commands[switch[0]]['help'], target)
            except KeyError:
                self.send_msg('That command does not exist. Try %help to see a list of commands.   [pyWHATauto]', target)

    def fversion(self, vars):
        target = vars[0]
        out('CMD','version',site=self.name)
        self.send_msg('I am currently running pyWA version %s and regex.conf version %s by johnnyfi·ve and blub·ba.'%(VERSION, G.REGVERSION), target)

    def fghost(self, vars):
        target = vars[0]
        out('CMD','ghost',site=self.name)
        self.connection.privmsg('nickserv', "GHOST %s %s" %(self.creds['botnick'], self.creds['nickservpass']))
        self.connection.nick(self.creds['botnick'])
        self.connection.privmsg("nickserv","identify " + self.creds['nickservpass'])
        self.send_msg('Ghost command sent.   [pyWHATauto]',target)

    def fuptime(self, vars):
        out('CMD','uptime',site=self.name)
        target = vars[0]
        diff = datetime.datetime.now() - G.STARTTIME
        seconds = (diff.microseconds + (diff.seconds + diff.days * 24 * 3600) * 10**6) / 10**6
        days = int( seconds // (60*60*24))
        hours = int( seconds // (60*60) )
        minutes = int((seconds - hours*60*60) // 60)
        seconds = int(math.floor((seconds - hours*60*60 - minutes*60)))
        string = ""
        if days > 0: string += " %d" %days + " days"
        if hours > 0: string += " %d" %hours + "h"
        if minutes >0 or hours >0: string += " %d" %minutes +"m"
        string += " %d" %seconds + "s   [pyWHATauto]"
        self.send_msg('I have been running for%s.'%string,target)

    def fstatsreset(self, vars):
        target = vars[0]
        out('CMD','statsreset',site=self.name)
        G.LOCK.acquire()
        for section in G.REPORTS.keys():
            G.REPORTS[section]['seen'] = 0
            G.REPORTS[section]['downloaded'] = 0
        G.LOCK.release()
        self.send_msg('The stats reset command has been issued.   [pyWHATauto]', target)

    def fcurrent(self, vars):
        nick = vars[3]

        out('CMD','current to %s' %nick,site=self.name)
        #quickly copy the current config to local memory, and release it.
        keylength = 0
        G.LOCK.acquire()
        fils = dict()
        for site in G.NETWORKS.iterkeys():
            for filter in G.NETWORKS[site]['filters'].keys():
                fils[filter] = dict()
                for key, val in G.NETWORKS[site]['filters'][filter].iteritems():
                    fils[filter][key]=val
                    if len(key) > keylength: keylength = len(key)
        G.LOCK.release()


        #then go through the lengthy process of sending the filters to IRC
        #timer = 0
        #for every section
        order = {'site':0,'active':1,'filtertype':2,'size':3,'resolution':4,'source':5,'season':6,'episde':7,'artist':8,'album':9}
        def compare(x,y):
            if x in order and y in order:
                return order[x]-order[y]
            elif x in order:
                return -1
            elif y in order:
                return 1
            else:
                return 0

        lenbnd = 500 - len(nick) - keylength - 20
        for filter in sorted(fils.iterkeys()):
            self.send_msg('***Section: '+ filter, nick)
            for key in sorted(fils[filter].iterkeys(),cmp=compare):
                #print fils[filter][key]
                splits = fils[filter][key].split('\n')
                msg = '   %-*s  %-s' %(keylength+2, key + ':', splits.pop(0))
                if len(msg) > lenbnd:
                    self.send_msg(msg[0:lenbnd - 20], nick)
                    msg = '   %-*s  %-s' %(keylength+2, '',msg[lenbnd - 20:])
                    while len(msg) >lenbnd:
                        self.send_msg(msg[0:lenbnd - 20], nick)
                        msg = '   %-*s  %-s' %(keylength+2, '',msg[lenbnd - 20:])
                for split in splits:
                    oldmsg = msg
                    msg += ', ' + split
                    if len(msg) > lenbnd:
                        self.send_msg(oldmsg, nick)
                        msg = '   %-*s  %-s' %(keylength+2, '',split)
                        if len(msg) > lenbnd:
                            self.send_msg(msg[0:lenbnd - 20], nick)
                            msg = '   %-*s  %-s' %(keylength+2, '',msg[lenbnd - 20:])
                            while len(msg) >lenbnd:
                                self.send_msg(msg[0:lenbnd - 20], nick)
                                msg = '   %-*s  %-s' %(keylength+2, '',msg[lenbnd - 20:])

                self.send_msg(msg, nick)



if __name__ == "__main__":
    main()
