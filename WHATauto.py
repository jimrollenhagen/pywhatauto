#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
#python 2.5 support for the "with" command
from __future__ import with_statement
from __future__ import division


print('Starting main program.')
print('pyWHATauto: johnnyfive + blubba. WHATauto original creator: mlapaglia.')

import sys
import globals as G
import irclib as irclib
#import handlePubMSG as handlePubMSG
from torrentparser import torrentparser

VERSION = 'v1.74'

print('You are running pyWHATauto version %s\n'%VERSION)

#from time import strftime, strptime
from datetime import datetime, timedelta

from threading import Thread
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn

import db, time, os, re, ConfigParser, thread, urllib, urllib2, random, cookielib, socket, math, traceback, sqlite3, ssl, threading#, WHATparse as WP, #htmllib, 

def main():
    global irc, log, log2, lastFSCheck, last, SETUP
    last = False
    lastFSCheck = False
    log = False
    os.chdir(G.SCRIPTDIR)
    loadConfigs()
    if G.LOG:
        if not os.path.isdir(os.path.join(G.SCRIPTDIR,'logs')):
            os.makedirs(os.path.join(G.SCRIPTDIR,'logs'))
    global WIN32FILEE
    WIN32FILEE = False
    if os.name == 'nt':
        try:
            import win32file
            if win32file:
                pass
            WIN32FILEE = True
        except ImportError:
            out('ERROR','The module win32file is not installed. Please download it from http://sourceforge.net/projects/pywin32/files/')
            out('ERROR','The program will continue to function normally except where win32file is needed.')
            WIN32FILEE = False
    out('DEBUG','Starting report thread.')        
    thread.start_new_thread(writeReport,(20,))
    out('DEBUG','Report thread started.')
    
    out('DEBUG','Starting DB thread.')  
    #Create the DB object
    DB = db.sqlDB(G.SCRIPTDIR, G.Q)
    DB.setDaemon(True)
    DB.start()
    out('DEBUG','DB thread started.')
    
    out('DEBUG','Starting web thread.')  
    #Create the web object
    try:
        WEB = WebServer(G.SCRIPTDIR, SETUP.get('setup','password'), SETUP.get('setup','port'), SETUP.get('setup', 'webserverssl'), SETUP.get('setup', 'certfile'), SETUP.get('setup','webserverip'))
        WEB.setDaemon(True)
        WEB.start()
        out('DEBUG','Web thread started.')
    except Exception:
        outexception('Exception caught in main(), when starting webserver')
    try:
        irc = irclib.IRC()
        out('INFO','Main program loaded. Starting bots.')
        
        if G.TESTING:
            startBots()
        else:
            thread.start_new_thread(startBots,(tuple()))
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
    #global REGEX, SETUP, CRED, FILTERS, CUSTOM, ALIASES#, REPORTS , NETWORKS
    #these get replaced with:
    # G.NETWORKS[sitename]['regex'], ['setup'], ['creds'], ['filters'], G.REPORTS   G.ALIAS
    if os.name == 'nt' and os.path.exists(os.path.join(G.SCRIPTDIR,'nt')):
        print('Loading nt settings')
        SETUP = ConfigParser.RawConfigParser()
        SETUP.readfp(open(os.path.join(G.SCRIPTDIR,'nt','setup.conf')))
        
        CRED = ConfigParser.RawConfigParser()
        CRED.readfp(open(os.path.join(G.SCRIPTDIR,'nt','credentials.conf')))
        
        CUSTOM = ConfigParser.RawConfigParser()
        CUSTOM.readfp(open(os.path.join(G.SCRIPTDIR,'nt','custom.conf')))
        
        FILTERS = ConfigParser.RawConfigParser()
        FILTERS.readfp(open(os.path.join(G.SCRIPTDIR,'nt','filters.conf')))
    
    else:
        SETUP = ConfigParser.RawConfigParser()
        SETUP.readfp(open(os.path.join(G.SCRIPTDIR,'setup.conf')))
        
        CRED = ConfigParser.RawConfigParser()
        CRED.readfp(open(os.path.join(G.SCRIPTDIR,'credentials.conf')))
        
        CUSTOM = ConfigParser.RawConfigParser()
        CUSTOM.readfp(open(os.path.join(G.SCRIPTDIR,'custom.conf')))
        
        FILTERS = ConfigParser.RawConfigParser()
        try:
            FILTERS.readfp(open(os.path.join(G.SCRIPTDIR,'filters.conf')))
        except ConfigParser.ParsingError, e:
            out('ERROR','There is a problem with your filters.conf. If using newlines, please make sure that each new line is tabbed in once. Error: %s'%e)
            raw_input("This program will now exit (okay): ")
            quit()
        
    REPORT = ConfigParser.RawConfigParser()
    REPORT.readfp(open(os.path.join(G.SCRIPTDIR,'reports.conf')))
    
    REGEX = ConfigParser.RawConfigParser()
    REGEX.readfp(open(os.path.join(G.SCRIPTDIR,'regex.conf')))

    
    if SETUP.has_option('debug', 'testing'):
        if SETUP.get('debug', 'testing').rstrip().lstrip() == '1':
            G.TESTING = True
            
    if SETUP.has_option('setup','log'):
        if SETUP.get('setup','log').rstrip().lstrip() == '1':
            G.LOG = True
    
    #load the reports. Since we re-write the entire file every time, we have to load them all.
    for site in REPORT.sections():
        G.REPORTS[site] = dict()
        G.REPORTS[site]['seen'] = int(REPORT.get(site, 'seen'))
        G.REPORTS[site]['downloaded'] = int(REPORT.get(site, 'downloaded'))
        
    #alias stuff:
    G.FROMALIAS = dict()
    G.TOALIAS = dict()
    for configs in CRED.sections():
        try:
            if CUSTOM.has_option('aliases', configs):
                if CUSTOM.get('aliases',configs) in G.FROMALIAS.keys():
                    raise DuplicateError('The alias %s is defined for two sites, %s and %s' %(CUSTOM.get('aliases',configs),G.FROMALIAS[CUSTOM.get('aliases',configs)],configs))
                G.FROMALIAS[CUSTOM.get('aliases',configs)] = configs
                G.TOALIAS[configs] = CUSTOM.get('aliases',configs)    
            elif SETUP.has_option('aliases', configs):
                if SETUP.get('aliases',configs) in G.FROMALIAS.keys():
                    raise DuplicateError('The alias %s is defined for two sites, %s and %s' %(SETUP.get('aliases',configs),G.FROMALIAS[SETUP.get('aliases',configs)],configs))
                G.FROMALIAS[SETUP.get('aliases',configs)] = configs
                G.TOALIAS[configs] = SETUP.get('aliases',configs)
            else:
                G.TOALIAS[configs] = configs
            if not configs in G.FROMALIAS.keys():
                G.FROMALIAS[configs] = configs
        except DuplicateError, e:
            if log:
                out('ERROR',e)
            else:
                print(e)
            G.EXIT = True
            sys.exit()
        
        if CUSTOM.has_option('sites',configs):
            G.TOSTART[configs]= CUSTOM.get('sites',configs)
        elif SETUP.has_option('sites',configs):
            G.TOSTART[configs]= SETUP.get('sites',configs)
        else:
            G.TOSTART[configs]= "0"
    
    G.ALIASLENGTH = 0
    longest = ''
    for val in G.TOALIAS.itervalues():
        if len(val) > G.ALIASLENGTH:
            G.ALIASLENGTH = len(val)
            longest = val
    if log:
        out('DEBUG','Longest alias is %s (%s) with length %d'%(longest,G.FROMALIAS[longest],G.ALIASLENGTH))
    else:
        print ('Longest alias is %s (%s) with length %d'%(longest,G.FROMALIAS[longest],G.ALIASLENGTH))
    
    if REGEX.has_option('version','version'):
        G.REGVERSION = int(REGEX.get('version','version'))
    
    G.NETWORKS = dict()
    
    for configs in CRED.sections(): #for network in credentials.conf
        #for key, value in CRED.items(configs):
        #if the REPORTS.conf is missing this network, add it!
        if not G.REPORTS.has_key(configs):
            G.REPORTS[configs] = dict()
            G.REPORTS[configs]['seen'] = 0
            G.REPORTS[configs]['downloaded'] = 0
        
        #add the credentials for each network key
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
        
        #add the setup to each network (they will all have the same info)        
        G.NETWORKS[configs]['setup'] = dict()
        for key, value in SETUP.items('setup'):
            G.NETWORKS[configs]['setup'][key] = value

        G.NETWORKS[configs]['notif'] = dict()
        for key, value in SETUP.items('notification'):
            G.NETWORKS[configs]['notif'][key] = value
        
        #add aliases
        G.NETWORKS[configs]['fromalias'] = dict()
        for key, value in G.FROMALIAS.iteritems():
            G.NETWORKS[configs]['fromalias'][key] = value
        
        G.NETWORKS[configs]['toalias'] = dict()
        for key, value in G.TOALIAS.iteritems():
            G.NETWORKS[configs]['toalias'][key] = value
        
        #add filters the networks they belong to
        G.NETWORKS[configs]['filters'] = dict()
        for f in FILTERS.sections():
            if FILTERS.get(f, 'site') == configs:
                G.NETWORKS[configs]['filters'][f] = dict()
                for key, value in FILTERS.items(f):
                    G.NETWORKS[configs]['filters'][f][key] = value
                #load the filter state into the filters dictionary
                G.FILTERS[f.lower()] = FILTERS.get(f, 'active')
                #if the filter has been manually toggled, load that value instead
                if f.lower() in G.FILTERS_CHANGED:
                    G.NETWORKS[configs]['filters'][f]['active'] = G.FILTERS_CHANGED[f.lower()]                       
    
def reloadConfigs():
    G.LOCK.acquire()
    loadConfigs()
    for bot in G.RUNNING.itervalues():
        bot.saveNewConfigs(G.NETWORKS[bot.getBotName()])
    G.LOCK.release()
    out('INFO','Configs re-loaded.')

def outexception(msg=False,site=False):
    exc = traceback.format_exc()
    if msg:
        out('ERROR', msg, site)
    for excline in exc.splitlines():
        out('ERROR', excline, site)

def out(level, msg, site=False):
    global last
    levels = ['error','warning','msg','info','cmd','filter','debug']
    #getting color output ready for when I decide to implement it
    colors = {'error':'%s','warning':'%s','msg':'%s','info':'%s','cmd':'%s','filter':'%s','debug':'%s'}
    if levels.index(level.lower()) <= levels.index(SETUP.get('setup','verbosity').lower()):
        if site:
            if site != last and last != False:
                #print('')
                if G.LOG:
                    logging('')
            msg = '%s %-*s %-*s %s' %(datetime.now().strftime("%m/%d-%H:%M:%S"),7,level,G.ALIASLENGTH,G.TOALIAS[site], msg)
            print(colors[level.lower()]%msg)
            last = site
        else:
            msg = '%s %-*s %-*s %s' %(datetime.now().strftime("%m/%d-%H:%M:%S"),7,level,G.ALIASLENGTH,'', msg)
            #msg='%s-%s: %s' %(datetime.now().strftime("%m/%d-%H:%M:%S"),level, msg)
            print(msg)
        if G.LOG:
            logging(msg)

def logging(msg):
    global log, log2, logdate
    #Create the log file
    logdir = os.path.join(G.SCRIPTDIR,'logs')
    if not log:
        logdate = datetime.now().strftime("%m.%d.%Y-%H.%M")
        log = open(os.path.join(logdir,'pyWALog-'+logdate+'.txt'),'w')
        log2 = open(os.path.join(logdir,'pyWALog.txt'),'w')
        #x = datetime.strptime(logdate,"%m.%d.%Y-%H.%M")
    if datetime.now() - datetime.strptime(logdate,"%m.%d.%Y-%H.%M") > timedelta(hours=24):
        log.close()
        logdate = datetime.now().strftime("%m.%d.%Y-%H.%M")
        log = open(os.path.join(logdir,'pyWALog-'+logdate+'.txt'),'w')    
    log.write(msg+"\n")
    log.flush() 
    log2.write(msg+"\n")
    log2.flush() 

def startBots():
    try:
        for key, value in G.TOSTART.items():
            if value == "1":
                establishBot(key)
        irc.process_forever()
    except Exception:
        outexception('General exception caught, startBots()')
        G.EXIT = True
        
def establishBot(sitename):
    '''Does some preliminary checks, creates a new autoBOT instance and connects it to irc'''
    #Need to check if there is sufficient regexp and credentials present
    
    if sitename in G.RUNNING.keys():
        out('INFO','The autoBOT for this site is already running')
        return 'The autoBOT for this site is already running'
    
    re = G.NETWORKS[sitename]['regex']
    if not ('server' in re and re['server'] != '' and 'port' in re and re['port'] != '' and 'announcechannel' in re and re['announcechannel'] != ''):
        out('INFO','This site does not have an irc announce channel.',site=sitename)
        return 'Cannot connect to irc network: this site does not have an irc announce channel.'
    cr = G.NETWORKS[sitename]['creds']
    if not ('botnick' in cr and cr['botnick'] != '' and 'nickowner' in cr and 'nickservpass' in cr and cr['nickservpass'] != ''):
        out('ERROR','The credentials given are not sufficient to connect to the irc server',site=sitename)
        return 'ERROR: The credentials given are not sufficient to connect to the irc server'
    
    shared = False

    if 'tempbotnick' in cr:
        botnick = cr['tempbotnick']
    else:
        botnick = cr['botnick']
    
    if 'ircpassword' in cr:
        ircpw = cr['ircpassword']
    else:
        ircpw = None

    for key in G.RUNNING.keys():
        sre = G.NETWORKS[key]['regex']
        scr = G.NETWORKS[key]['creds']
        if sre['server'].lower() == re['server'].lower():
            out('DEBUG','Matching servers found between %s and %s (old), %s' %(sitename,key,re['server']),site=sitename)
            if 'tempbotnick' in scr:
                sbotnick = scr['tempbotnick']
            else:
                sbotnick = scr['botnick']
            if 'ircpassword' in cr:
                sircpw = cr['ircpassword']
            else:
                sircpw = None
            if botnick.lower() == sbotnick.lower() and ircpw == sircpw:
                out('DEBUG','servers and nicks are matching the full way! Piggybacking...',site=sitename)
                shared = key
                break
        
    G.LOCK.acquire()
    G.RUNNING[sitename] = autoBOT(sitename,G.NETWORKS[sitename])
    G.LOCK.release()
    
    if shared:
        G.RUNNING[sitename].setSharedConnection(G.RUNNING[shared])
        return 'Connecting to %s by piggybacking on %s\'s connection' %(sitename,shared)
    else:
        G.RUNNING[sitename].connect()
        return 'Connecting to %s' %(sitename)
    
def writeReport(n):
    last = 0
    while 1:
        now = 0
        G.LOCK.acquire()
        for key in G.REPORTS.itervalues():
            now += int(key['seen'])
        if last != now:
            config = ConfigParser.RawConfigParser()
            for section in sorted(G.REPORTS.iterkeys()):
                config.add_section(section)
                config.set(section,'seen',G.REPORTS[section]['seen'])
                config.set(section,'downloaded',G.REPORTS[section]['downloaded'])
            #release the lock before we waste time writing the config.
            G.LOCK.release()
            # Writing our configuration file to 'reports.conf'
            try:
                with open('reports.conf', 'wb') as configfile:
                        config.write(configfile)
                last = now
            except IOError, e:
                out('ERROR',e)          
        else:
            G.LOCK.release()
        time.sleep(n)


def getDriveInfo(drive):
    if os.name == 'nt' and WIN32FILEE:
        def get_drivestats(drive=None):
            '''
            returns total_space, free_space and drive letter
            '''
            drive = drive.replace(':\\', '')
            import win32file
            sectPerCluster, bytesPerSector, freeClusters, totalClusters = win32file.GetDiskFreeSpace(drive + ":\\")
            total_space = totalClusters*sectPerCluster*bytesPerSector
            free_space = freeClusters*sectPerCluster*bytesPerSector
            return total_space, free_space
        total_space, free_space = get_drivestats(drive)
        return free_space, float(free_space)/float(total_space)
    elif os.name == 'posix':
        if SETUP.has_option('setup','limit') and SETUP.get('setup','limit').lstrip().rstrip() != '' and SETUP.get('setup','limit').lstrip().rstrip() != '0':
            import subprocess, shlex
            args = shlex.split('du -s --bytes %s'%drive)
            du = subprocess.Popen(args,stdout=subprocess.PIPE)
            dureturn = du.communicate()[0]
            m = re.search('(\d+).*',dureturn)
            used = float(m.group(1)) / (1024 * 1024 * 1024)
            free = float(SETUP.get('setup','limit'))-used
            return free, free / float(SETUP.get('setup','limit'))
        else:
            out('ERROR','Unknown filesystem as it seems...')
            return 1.0, 1.0
            #try:
                #s = os.statvfs(drive) 
                #return (float(s.f_bavail)*float(s.f_bsize))/1024/1024/1024, (float(s.f_bavail)/float(s.f_blocks))
            #except OSError, e:
                #print(e)
    else:
        return 1.00, 1.00

def freeSpaceOK():
    global lastFSCheck
    drive = SETUP.get('setup', 'drive')
    limit = SETUP.get('setup', 'freepercent')
    if lastFSCheck == False:
        lastFSCheck = datetime.now()
    elif datetime.now()-lastFSCheck > timedelta(seconds=900):
        #if we haven't run this check in the last 15 minutes, then run it, otherwise it's too soon!
        free, percent = getDriveInfo(drive)
        out('DEBUG','Free HD space: %s' %str(free))
        if percent > limit: #if we are still within the limit
            return True
        else:
            return False
    else: #if we've already checked within the last 15 minutes
        return True
    
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
        out('ERROR','Download type is not set in regex.conf for %s' %site, site)
        G.LOCK.release()
        return 'downloadtype'
    
    if downloadType != '5':
        if not os.path.isfile(os.path.join(G.SCRIPTDIR,'cookies',site+'.cookie')):
            G.LOCK.release()
            #check to make sure this isn't a site that needs a preset cookie.
            if 'presetcookie' in G.NETWORKS[site]['regex'] and G.NETWORKS[site]['regex']['presetcookie'] == '1':
                out('ERROR','This tracker requires you to manually create a cookie file before you can download.',site)
                return 'preset'
            else:
                #if not, log in and create one
                cj = createCookie(site, cj)
                if not cj:
                    return 'password'
        else:
            #load the cookie since it exists already
            try:
                cj.load(os.path.join(G.SCRIPTDIR,'cookies',site+'.cookie'), ignore_discard=True, ignore_expires=True)
                G.LOCK.release()
            except cookielib.LoadError:
                if 'presetcookie' in G.NETWORKS[site]['regex'] and G.NETWORKS[site]['regex']['presetcookie'] == '1':
                    out('ERROR','The cookie for %s is the wrong format'%site,site)
                    G.LOCK.release()
                    return 'preset'
                else:
                    G.LOCK.release()
                    cj = createCookie(site, cj)
                    if not cj:
                        return 'password'
    else:
        G.LOCK.release()
        if not 'passkey' in G.NETWORKS[site]['creds'] or ('passkey' in G.NETWORKS[site]['creds'] and G.NETWORKS[site]['creds']['passkey'] == ''):
            out('ERROR','This site requires the passkey to be set in credentials.conf')
            return 'passkey'
    
    #create the downloadURL based on downloadType
    if downloadType == '1': # request a download ID, and get a filename
        downloadURL = G.NETWORKS[site]['regex']['downloadurl'] + downloadID
    elif downloadType == '2':
        downloadURL = G.NETWORKS[site]['regex']['downloadurl'] + '/' + downloadID + '/' + downloadID + '.torrent'
    elif downloadType == '3':
        downloadURL = G.NETWORKS[site]['regex']['downloadurl'] + '/' + downloadID + '/' + G.NETWORKS[site]['regex']['urlending']
    elif downloadType == '4':
        downloadURL = G.NETWORKS[site]['regex']['downloadurl'] + downloadID + G.NETWORKS[site]['regex']['urlending'] + downloadID + '.torrent'
    elif downloadType == '5':
        downloadURL = G.NETWORKS[site]['regex']['downloadurl'] + '/' + downloadID + '/' + G.NETWORKS[site]['creds']['passkey'] + '/' + name + '.torrent'
    #set the socket timeout
    socket.setdefaulttimeout(25)
        
    handle = None
    try:
        handle = getFile(downloadURL,cj)
    except urllib2.HTTPError, e:
        if int(e.code) in (301,302,303,307):
            print 'Caught a redirect. Code: %s, url: %s, headers %s, others: %s' %(e.code, e.url, e.headers.dict, e.__dict__.keys())
            return 'moved'
        else:
            print 'Caught another http error. Code: %s, url: %s, headers %s, others: %s' %(e.code, e.url, e.headers.dict, e.__dict__.keys())
            return 'httperror'
    else:
        return handle

def download(downloadID, site, location=False, network=False, target=False, retries=0, email=False, notify=False, filterName=False, announce=False, formLogin=False, sizeLimits=False, name=False, fromweb=False):
    """Take an announce download ID and the site to download from, do some magical stuff with cookies, and download the torrent into the watch folder
    Returns a tuplet with (True/False, statusmsg)"""
    out('DEBUG', 'Downloading ID: %s, site: %s, filter: %s, location: %s, network: %s, target: %s, retries: %s, email: %s, announce %s, name %s'%(downloadID, site, filterName, location, network, target, retries, email, announce, name))
    success = False
    error = ''
    statusmsg = ''
    G.LOCK.acquire()
    
    #load where we should be saving the torrent if not already set
    if not location:
        location = SETUP.get('setup', 'torrentdir')
        if 'watch' in G.NETWORKS[site]['creds'] and G.NETWORKS[site]['creds']['watch'] != '':
            location = G.NETWORKS[site]['creds']['watch']
            
    #'network' is only sent if it's a manual download, so if it's false that means this is an automatic dl
    #if it's automatic, then check to see if the delay exists
    sleepi = None
    if retries == 0 and not network and not fromweb:
        if SETUP.has_option('setup', 'delay') and SETUP.get('setup', 'delay').lstrip().rstrip() != '':
            sleepi = int(SETUP.get('setup', 'delay'))
    
    #check if the network requires a torrentname for downloading
    if 'downloadtype' in G.NETWORKS[site]['regex'] and G.NETWORKS[site]['regex']['downloadtype'] == '5':
        if 'nameregexp' in G.NETWORKS[site]['regex'] and G.NETWORKS[site]['regex']['nameregexp'] != '':
            if not name:
                if announce:
                    name = re.match(G.NETWORKS[site]['regex']['nameregexp'],announce).group(1)
                else:
                    error = 'The download function for this site can only be used for the button and automatic downloads.'
        else:
            error = 'This site requires the variable \'nameregexp\' to be set in regex.conf.'
        
    G.LOCK.release()
    
    file_info = False
    retreived = ''
    if not error:
        if sleepi: time.sleep(sleepi)
        #if this is a retry, then wait 3 seconds.
        if retries > 0:
            if not network and not fromweb:
                time.sleep(3)
            else:
                time.sleep(0.5)
        
        cj = cookielib.LWPCookieJar()
    
        #use the cookie to download the file
        retreived = dlCookie(downloadID, site, cj, target, network, name)
        if str(type(retreived)) == "<type 'instance'>":
            file_info = retreived.info()
                
    retry = False

    if file_info:
        if file_info.type == 'text/html':
            #This could either mean the torrent doesn't exist or we are not logged in
            G.LOCK.acquire()
            if 'presetcookie' in G.NETWORKS[site]['regex'] and G.NETWORKS[site]['regex']['presetcookie'] == '1':
                statusmsg = 'There was an error downloading torrent %s from %s. Either it was deleted, or the cookie you entered is incorrect.'%(downloadID, site)
            else:
                statusmsg = 'There was an error downloading torrent %s from %s. Either it was deleted, or the credentials you entered are incorrect.'%(downloadID, site)
            G.LOCK.release()
            retry = True
                            
        elif file_info.type == 'application/x-bittorrent':
            #figure out the filename
            #see if the file has content disposition, if it does read it.
            info = retreived.read()
            try:
                tp = torrentparser(debug=False, content=info)
                mbsize = tp.mbsize()
                tpname = tp.name()
            except SyntaxError, e:
                out('ERROR','The torrentparser was unable to parse the torrent file. Please let blubba know: %s' %e,site=site)
                mbsize = None
                tpname = None
            
            if not name:
                if tpname:
                    filename = tpname
                else:    
                    if 'Content-Disposition' in file_info:
                        for cd in G.CD:
                            if cd in file_info['Content-Disposition']:
                                filename = file_info['Content-Disposition'].replace(cd,'').replace('"','')
                    if filename == '':
                        filename = downloadID+'.torrent'
            else:
                filename = name
            
            if '.torrent' not in filename: filename += '.torrent'
            filename = urllib.unquote(filename)
            
            sizeOK = True
            if sizeLimits and not (network or fromweb):
                sizerange = sizeLimits.split(',')
                if mbsize:
                    G.LOCK.acquire()
                    if (len(sizerange) == 1 and mbsize > float(sizerange[0])) or (len(sizerange) == 2 and mbsize > float(sizerange[1])):
                        out('INFO', "(%s) Torrent is larger than required by filter '%s'."%(downloadID,filterName),site)
                        sizeOK = False
                    elif len(sizerange) == 2 and mbsize < float(sizerange[0]):
                        sizeOK = False
                        out('INFO', "(%s) Torrent is smaller than required by '%s'."%(downloadID,filterName),site)
                    else:
                        out('INFO', "(%s) Torrent is within size range required by filter '%s'."%(downloadID,filterName),site)
                    G.LOCK.release()
            elif not (network or fromweb):
                G.LOCK.acquire()
                out('INFO', '(%s) No Size check.'%downloadID,site)
                G.LOCK.release()
            if sizeOK:
                G.LOCK.acquire()
                try:
                    local_file = open(os.path.join(location, filename),'wb')
                    local_file.write(info)
                    local_file.close()
                except IOError:
                    #If there's no room on the hard drive
                    
                    out('ERROR', '(%s) !! Disk quota exceeded. Not enough room for the torrent!'%downloadID,site)
                    statusmsg = 'Can\'t write the torrent file on the disk, as there is not enough free space left!'
                    retry = True
                else:
                    #if the filesize of the torrent is too small, then retry in a moment
                    if 100 > int(os.path.getsize(os.path.join(location, filename))):
                        statusmsg = 'The size of the torrent is too small. Maybe try a different torrent of this tracker to see if this is a local or global occurance.'
                        retry = True
                    else: 
                        success = True
                        if mbsize:
                            statusmsg = 'Torrent (id: %s) successfully downloaded! Size %.2f MB, retries: %d, filename: %s' %(str(downloadID),mbsize,retries,filename)
                        else:
                            statusmsg = 'Torrent (id: %s) successfully downloaded! Retries: %d, filename: %s' %(str(downloadID),retries,filename)
                G.LOCK.release()
            else:
                statusmsg = 'The torrent size did not fit the filter.'
                    
                
        else:
            out('ERROR','unknown filetype received: %s' %file_info.type, site)
            retry = True
    elif error:
        statusmsg = error
    else:
        if retreived == 'preset':
            statusmsg = 'This site requires a cookie to be preset, called \'%s.torrent\' in the folder \'cookies\'. Either this cookie is missing or malformatted.' %site
        elif retreived == 'password':
            statusmsg = 'The login credentials set in credentials.conf for %s are incorrect or missing.' %site
            #retry = True
        elif retreived == 'moved':
            statusmsg = 'Either the torrent id (%s) does not exist or your credentials for %s are wrong or missing' %(str(downloadID),site)
            retry = True
        elif retreived == 'httperror':
            statusmsg = 'An http error occured. Please check if the site is online, and check the log for more details if this problem persists.'
            retry = True
        elif retreived == 'downloadtype':
            statusmsg = 'The key \'downloadType\' is not set in regex.conf. Aborting'
        elif retreived == 'passkey':
            statusmsg = 'This site requires the passkey to be set in credentials.conf. Please set it and try again.'
    if retry and retries <= 0:
        G.LOCK.acquire()
        if not 'presetcookie' in G.NETWORKS[site]['regex'] or ( 'presetcookie' in G.NETWORKS[site]['regex'] and not G.NETWORKS[site]['regex']['presetcookie'] == '1'):
            if os.path.isfile(os.path.join(G.SCRIPTDIR,'cookies',site+'.cookie')):
                os.remove(os.path.join(G.SCRIPTDIR,'cookies',site+'.cookie'))
            else:
                out('ERROR','The cookie file doesn\'t exist here... this should not happen!',site)
        out('INFO','(%s) !! Torrent file is not ready to be downloaded. Trying again in a moment. Reason: %s'%(downloadID,statusmsg),site)
        G.LOCK.release()
        return download(downloadID, site, location=location, network=network, target=target, retries=retries+1, email=email, notify=notify, filterName=filterName, announce=announce, formLogin=formLogin, sizeLimits=sizeLimits, name=name, fromweb=fromweb)

    elif success:
        G.LOCK.acquire()
        out('INFO','%s to %s'%(statusmsg,location),site)
        if email:
            sendEmail(site, announce, filterName, filename)
        if notify:
            sendNotify(site, announce, filterName, filename)
        if network:
            network.sendMsg(statusmsg, target)
        G.LOCK.release()
        return (True, statusmsg)
    else:
        #did not succeed in downloading!
        G.LOCK.acquire() 
        out('ERROR','Download error (%s): %s'%(downloadID,statusmsg),site)
        if network:
            network.sendMsg('Download error (%s:%s): %s'%(site,downloadID,statusmsg), target)
        G.LOCK.release()
        return (False, statusmsg)
    


def getFile(downloadURL, cj):
    #create the opener
    if SETUP.get('setup','verbosity').lower() == 'debug':
        opener = build_opener(cj, debug=1)
    else:
        opener = build_opener(cj)
    urllib2.install_opener(opener)
    req = urllib2.Request(downloadURL)
    req.add_header("User-Agent", "pywa")
    return urllib2.urlopen(req)

def createCookie(site, cj):
    urlopen = urllib2.urlopen
    Request = urllib2.Request
    #opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    if SETUP.get('setup','verbosity').lower() == 'debug':
        opener = build_opener(cj, debug=1)
    else:
        opener = build_opener(cj)
        
    urllib2.install_opener(opener)
    G.NETWORKS[site]['regex']
    if 'loginuserpost' in G.NETWORKS[site]['regex'] and G.NETWORKS[site]['regex']['loginuserpost'] != '':
        userpost = G.NETWORKS[site]['regex']['loginuserpost']
    else:
        userpost = 'username'
    
    if 'loginpasswordpost' in G.NETWORKS[site]['regex'] and G.NETWORKS[site]['regex']['loginpasswordpost'] != '':
        passpost = G.NETWORKS[site]['regex']['loginpasswordpost']
    else:
        passpost = 'password'
    
    httpdict = {userpost : G.NETWORKS[site]['creds']['username'], passpost : G.NETWORKS[site]['creds']['password'] }
    
    if 'morepostdata' in G.NETWORKS[site]['regex'] and G.NETWORKS[site]['regex']['morepostdata'] != '':
        try:
            newdict = eval("{"+ G.NETWORKS[site]['regex']['morepostdata'] + "}")
        except SyntaxError:
            out('ERROR', 'morepostdata variable raised a syntax error %s' %G.NETWORKS[site]['regex']['morepostdata'], site=site)
        httpdict.update(newdict)

    if site == 'passthepopcorn':
        httpdict['passkey'] = G.NETWORKS[site]['creds']['passkey']

    http_args = urllib.urlencode(httpdict)

    #http_args = urllib.urlencode(dict(username=G.NETWORKS[site]['creds']['username'], password=G.NETWORKS[site]['creds']['password']))

    req = Request(G.NETWORKS[site]['regex']['loginurl'], http_args)
    req.add_header("User-Agent", "pywa")
    if site == "whatcd":
        req.add_header('Referer', 'https://what.cd/login.php')

    out('INFO','Logging into %s because a cookie was not previously saved or is outdated.'%site,site=site)
    handle = None
    try:
        handle = urlopen(req)
    except urllib2.HTTPError, e:
        print 'Caught a redirect. Code: %s, url: %s, headers %s, others: %s' %(e.code, e.url, e.headers.dict, e.__dict__.keys())
        #print cj
        G.LOCK.acquire()
        cj.save(os.path.join(G.SCRIPTDIR,'cookies',site+'.cookie'), ignore_discard=True, ignore_expires=True)
        G.LOCK.release()
        return cj
    
    if handle and 'login200' in G.NETWORKS[site]['regex'] and G.NETWORKS[site]['regex']['login200'] == '1':
        G.LOCK.acquire()
        cj.save(os.path.join(G.SCRIPTDIR,'cookies',site+'.cookie'), ignore_discard=True, ignore_expires=True)
        G.LOCK.release()
        return cj
    elif handle and 'loginjson' in G.NETWORKS[site]['regex'] and G.NETWORKS[site]['regex']['loginjson'] == '1':
        import json
        try:
            result = json.loads(handle.read())
        except ValueError:
            out('ERROR', 'Invalid JSON returned on login attempt', site)
            return
        if 'Result' in result and result['Result'] == 'Error':
            if 'Message' in result:
                    out('ERROR', "Result: %s, Message: %s" % (result['Result'],result['Message']), site)
            else:
                    out('ERROR', "Result: %s " % result['Result'], site)
        elif 'Result' in result and result['Result'] == 'Ok':
                G.LOCK.acquire()
                cj.save(os.path.join(G.SCRIPTDIR,'cookies','%s.cookie' % site), ignore_discard=True, ignore_expires=True)
                G.LOCK.release()
                return cj
    elif handle:
            #print "----"
            #print handle.read()
            #print "----"
            #print handle.info()
            out('ERROR','Password seems to be incorrect',site)
            return False
    else:
        out('ERROR','We don\'t have a redirect but still data? How can that happen?',site)


def build_opener(cj, debug=False):
    http_handler = urllib2.HTTPHandler(debuglevel=debug)
    https_handler = urllib2.HTTPSHandler(debuglevel=debug)

    cookie_handler = urllib2.HTTPCookieProcessor(cj)

    opener = urllib2.build_opener(http_handler, https_handler, cookie_handler, smartredirecthandler())

    opener.cookie_jar = cj

    return opener

class smartredirecthandler(urllib2.HTTPRedirectHandler):
    
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        out('DEBUG','Redirect received. stuff: %s, %s, %s' %(code,msg,newurl))
        return None

def sendEmail(site, announce, filter, filename):
    # Imports
    import smtplib
    from email.mime.text import MIMEText
    
    #create the message
#    msg = 'pyWA has detected a new download.\n\nSite: %(site)s\nCaptured Announce: %(announce)s\nMatched Filter: %(filter)s\nSaved Torrent: %(filename)s'%{'filename':filename, 'filter':filter, 'site':site, 'announce':announce}
    msg = MIMEText('pyWA has detected a new download.\n\nSite: %(site)s\nCaptured Announce: %(announce)s\nMatched Filter: %(filter)s\nSaved Torrent: %(filename)s'%{'filename':filename, 'filter':filter, 'site':site, 'announce':announce})
    gmail = SETUP.get('notification','gmail')
    msg['Subject'] = 'pyWA: New %s download!'%site
    
    # Send the message via our own SMTP server
    
    s = smtplib.SMTP("smtp.gmail.com", 587)
    s.ehlo()
    s.starttls()
    s.ehlo()
    
    #s = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    try:
        out('INFO','Emailing %s with a notification.'%gmail)
        s.login(gmail, SETUP.get('notification','password'))
        s.sendmail(gmail, gmail, msg.as_string())
        s.quit()
    except Exception, e:
        out('ERROR', 'Could not send notify email. Error: %s'%e.smtp_error)

def sendNotify(site, announce, filter, filename):
    sent = False
    for net in G.RUNNING.itervalues():
        #G.NETWORKS[bot.getBotName()]
        if net.getBotName() == SETUP.get('notification', 'server'):
            out('INFO', 'Messaging %s with an IRC notification.'%SETUP.get('notification', 'nick'))
            net.sendMsg('New DL! Site: %(site)s, Filter: %(filter)s, File: %(file)s '%{'site':site, 'filter':filter,'file':filename}, SETUP.get('notification', 'nick'))
            sent = True
    if not sent:
        out('ERROR','Could not send notification via %s, because I am not connected to that network'%SETUP.get('notification', 'server'))

class WebServer( Thread ):
    
    def __init__(self, loadloc, pw, port, ssl, certfile, ip=''):
        global webpass
        Thread.__init__(self)
        self.loadloc = loadloc
        self.ip = ip
        self.certfile = certfile
        try:
            self.port = int(port)
        except ValueError:
            out('WARNING', 'Bad webserver port, could not start webserver')
            raise Exception('Could not start webserver')
        try:
            self.ssl = bool(int(ssl))
        except ValueError:
            out('WARNING', 'Bad webserver ssl setting, could not start webserver')
            raise Exception('Could not start webserver')
        if pw != '':
            webpass = pw
        else:
            webpass = str(random.randint(10**5,10**9))
            out('ERROR','No webserver password set. Assigning a random one: %s'%webpass)

    def run(self):
        global CONN, C
        CONN = sqlite3.connect(os.path.join(self.loadloc, 'example.db'))
        #CONN = sqlite3.connect(":memory:")
        C = CONN.cursor()

        self.server = ThreadedHTTPServer((self.ip, int(self.port)), MyHandler)
        if self.ssl:
            print 'started secure httpserver...'
            self.server.socket = ssl.wrap_socket(self.server.socket, certfile=self.certfile, server_side=True)
            self.server.serve_forever()
        else:
            print 'started httpserver...'
            self.server.serve_forever()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    '''Handles requests in threads'''

class MyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        error = False
        try:
            if self.path.split('?')[0].lower().endswith(".pywa"):
                if self.path.startswith("/dl"):
                    arg = self.path.split("?")
                    if len(arg)>1:
                        arg = arg[1].split('&')
                        args = dict()
                        for a in arg:
                            b = a.split('=')
                            if len(b)>1:
                                args[b[0]] = b[1]
                        print args
                    else:
                        error = True
                    if not error:
                        if 'pass' in args and args['pass'] == webpass:
                            if 'id' in args and args['id'] != "":
                                id = args['id']
                                if 'site' in args and args['site'].lower() in G.FROMALIAS:
                                    site = G.FROMALIAS[args['site'].lower()]
                                    out('INFO',"WebUI download request for id %s received from %s"%(args['id'], self.client_address[0]),site)
                                    if 'name' in args:
                                        name = args['name']
                                    else:
                                        name = None
                                    try:
                                        if 'buttonwatch' in G.NETWORKS[site]['creds']:
                                            loc = G.NETWORKS[site]['creds']['watch']
                                        elif SETUP.has_option('setup','buttonwatch') and SETUP.get('setup', 'buttonwatch') != '':
                                            loc = SETUP.get('setup', 'buttonwatch')
                                        else:
                                            loc = None
                                        output = download(id, site, location=loc, name=name, fromweb=True)
                                    
                                    except Exception as e:
                                        outexception('Error while downloading %s from web, error: %s' %(str(id),str(e)),site)
    
                                    self.send_response(200)
                                    self.send_header('Content-type','text/html')
                                    self.end_headers()
                                    
                                    if output[0]:
                                        self.wfile.write("<html><head><script>t = null;function moveMe(){t = setTimeout(\"self.close()\",10000);}</script></head><body onload=\"moveMe()\">")
                                        self.wfile.write("%s" %output[1])
                                        self.wfile.write("</body></html>")
                                    else:
                                        self.wfile.write("<html><head></head>")
                                        self.wfile.write("%s" %output[1])
                                        self.wfile.write("</body></html>")
                                else:
                                    #unknown/no site name
                                    self.send_response(200)
                                    self.send_header('Content-type','text/html')
                                    self.end_headers()
                                    self.wfile.write("<html><head></head>")
                                    self.wfile.write("Incorrect sitename.")
                                    self.wfile.write("</body></html>")
                            else:
                                #no ID supplied
                                self.send_response(200)
                                self.send_header('Content-type','text/html')
                                self.end_headers()
                                self.wfile.write("<html><head></head>")
                                self.wfile.write("Torrentid missing.")
                                self.wfile.write("</body></html>") 
                        else:
                            self.send_response(200)
                            self.send_header('Content-type','text/html')
                            self.end_headers()
                            self.wfile.write("Incorrect password supplied. Try again.")
                            out('WARNING','Received a webUI download command with the wrong password from ip %s' %self.client_address[0])
                    else:
                        self.send_response(200)
                        self.send_header('Content-type','text/html')
                        self.end_headers()
                        self.wfile.write("Incorrect command structure. Try again.")
                else:
                    self.send_error(404)
            else:
                self.send_error(404)
        except Exception:
            outexception('Generic do_GET exception')


class autoBOT( ):
    """A class for connecting to an IRC network, joining an announce channel, and watching for releases to download"""
    
    def __init__(self, name, info):
        """init this shit, yo"""
        out('DEBUG', 'autoBOT: '+name+' started',site=name)
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
        self.lastdata = datetime.now()
        self.regex = info['regex']
        self.creds = info['creds']
        self.setup = info['setup']
        self.notif = info['notif']
        self.filters = info['filters']
        self.toalias = info['toalias']
        self.fromalias = info['fromalias']
        #self.aliases = info[]
        #for key, value in info['aliases'].items():
        #    self.aliases[value] = key
        self.announcehistory = list()
        self.threads = list()
        self.connection = None
        self.who = list()
        self.partPhrase = ":I leave because I want to!"
        self.joined = False  #have we already joined the channels we're supposed to after connect?
        self.reg = dict()
        self.resistant = False
        self.ircreg = re.compile("\x0f|\x1f|\x02|\x03(?:[\d]{1,2}(?:,[\d]{1,2})?)?", re.UNICODE)
        #self.ircreg = re.compile('||(\\d){0,2}')
        for announce in info['regex']['announces'].split(', '):
            self.reg[announce] = re.compile(info['regex'][announce])
        self.checkTorrentFolders(False)
        if '!' in self.creds['nickowner']:
            self.creds['nickowner'] = self.creds['nickowner'][self.creds['nickowner'].index('!')+1:]
        
        self.advancedfilters = False
        if "advancefilters" in self.creds:
            self.advancedfilters = True
                    
            
        G.LOCK.acquire()   
        irc.add_global_handler('pubmsg', self.handlePubMessage)
        irc.add_global_handler('privmsg', self.handlePrivMessage)
        irc.add_global_handler('welcome', self.handleWelcome)
        irc.add_global_handler('nicknameinuse', self.handleNickInUse)
        irc.add_global_handler('invite', self.handleInvite)
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
        irc.add_global_handler('nosuchnick',self.handlenosuchnick) #ping,REMOVED from below: 'nomotd', 'motd', 'luserme', 'motdstart', 'endofinfo', 'motd2', 'endofmotd','featurelist','myinfo','n_global', 'n_local',  
        self.what_events = ["pubnotice","quit","kick","mode",'whoreply','endofwho','statskline', 'part', 'join', 'topicinfo', 'statsqline', 'statsnline', 'statsiline', 'statscommands', 'statscline', 'tracereconnect', 'statslinkinfo', 'notregistered', 'created', 'endofnames', 'statsuptime', 'notopic', 'statsyline', 'endofstats', 'uniqopprivsneeded', 'cannotsendtochan', 'adminloc2', 'adminemail', 'luserunknown', 'luserop', 'luserconns', 'luserclient', 'adminme', 'adminloc1', 'luserchannels', 'toomanytargets', 'listend', 'toomanychannels', 'statsoline', 'invitelist', 'endofinvitelist', 'nosuchchannel', 'inviting', 'summoning', 'exceptlist', 'endofexceptlist', 'noorigin', 'nosuchserver', 'nochanmodes', 'endofbanlist', 'yourebannedcreep', 'passwdmismatch', 'keyset', 'needmoreparams', 'nopermforhost', 'alreadyregistered', 'tryagain', 'endoftrace', 'tracelog', 'notonchannel', 'noadmininfo', 'umodeis', 'endoflinks', 'nooperhost', 'fileerror', 'wildtoplevel', 'usersdisabled', 'norecipient', 'notexttosend', 'notoplevel', 'info', 'infostart', 'whoisoperator', 'whoisidle', 'whoischanop', 'whowasuser', 'users', 'usersstart', 'time', 'nousers', 'endofusers', 'servlist', 'servlistend', 'youwillbebanned', 'badchannelkey', 'serviceinfo', 'endofservices', 'service', 'youreoper', 'usernotinchannel', 'list', 'none', 'liststart', 'noservicehost', 'channelmodeis', 'away', 'banlist', 'links', 'channelcreate', 'closing', 'closeend', 'usersdontmatch', 'killdone', 'traceconnecting', 'tracelink', 'traceunknown', 'tracehandshake', 'traceuser', 'traceoperator', 'traceservice', 'traceserver', 'traceclass', 'tracenewtype', 'userhost', 'ison', 'unaway', 'nowaway', 'nologin', 'yourhost', 'rehashing', 'statslline', 'summondisabled', 'umodeunknownflag', 'bannedfromchan', 'useronchannel', 'restricted', 'cantkillserver', 'chanoprivsneeded', 'noprivileges', 'badchanmask', 'statshline', 'unknownmode', 'inviteonlychan', 'channelisfull', 'version', 'unknowncommand', 'nickcollision', 'myportis', 'banlistfull', 'erroneusnickname', 'unavailresource', 'nonicknamegiven']
        for value in self.what_events:
            irc.add_global_handler(value, self.handleAllDebug)
        #Warn if nickowner is empty!
        if self.creds['nickowner'] == '':
                out('WARNING',"Nickowner on network '%s' is blank!"%self.name,site=self.name)
        # Create a server object, connect and join the channel
        self.connection = irc.server()
        G.LOCK.release()
        
    def saveNewConfigs(self, info):
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
        
    def setSharedConnection(self, othernetwork):
        #this means we are using another bot's connection, so don't bother 
        self.piggyback = othernetwork.piggyback
        self.piggyback.append(self.name)
        self.connection = othernetwork.connection
        havejoined = False
        for site in self.piggyback:
            if G.RUNNING[site].joined:
                havejoined = True
        if havejoined:
            self.logintochannels(self.connection, None)
                        
    def getBotName(self):
        return self.name
        
    def checkTorrentFolders(self, target):
        #global EXIT
        for filter in self.filters.keys():
            if self.filters[filter]['active'] == '1':
                if self.filters[filter].has_key('watch') and self.filters[filter]['watch'] != '':       
                    try:
                        if not os.path.isdir( self.filters[filter]['watch'] ):
                            os.makedirs( self.filters[filter]['watch'] )
                    except Exception, e:
                        out('ERROR', e)
                        if target:
                            self.sendMsg("Error: There was a problem with the custom watch folder for filter '%s'. It will be ignored. : '%s'"%(filter,self.filters[filter]['watch']) , target)
                            self.filters[filter]['watch'] = ''
        if self.creds.has_key('watch') and self.creds['watch'] != '':       
            try:
                if not os.path.isdir( self.creds['watch'] ):
                    os.makedirs( self.creds['watch'] )
            except Exception, e:
                out('ERROR', e)
                if target:
                    self.sendMsg("Error: There was a problem with the custom watch folder for site '%s'. It will be ignored. : '%s'"%(filter,self.creds['watch']) , target)
                    self.creds['watch'] = ''
        try:
            if not os.path.isdir( self.setup['torrentdir'] ):
                os.makedirs( self.setup['torrentdir'] )
        except os.error, e:
            out('ERROR', 'torrentDir: %s caused %s'%(self.setup['torrentdir'],e))
            raw_input("This program will now exit (okay): ")
            G.EXIT = True
            sys.exit()
        except KeyError, e:
            out('ERROR', "Setup option 'torrentDir' is missing from setup.conf. So let's put it in there, mmmmkay?")
            raw_input("This program will now exit (okay): ")
            G.EXIT = True
            sys.exit()
        except Exception, e:
            out('ERROR', e)
            raw_input("This program will now exit (okay): ")
            G.EXIT = True
            sys.exit()
                        
    def connect(self):
        """Connect to the IRC network and join the appropriate channels"""
        if not self.name in G.RUNNING.keys():
            return
        out('DEBUG','piggyback is %s' %self.piggyback, site=self.name)
        for key in self.piggyback:
            if key in G.RUNNING:
                G.RUNNING[key].joined = False
                out('DEBUG','Reset self.joined for %s' %key, site=self.name)
        self.attempt += 1
        connerr = False
        self.pingsent = False
        if self.attempt > 1:
            out('INFO', 'Connection attempt number %d' %self.attempt, site=self.name)
        try:
            if 'ssl' in self.regex and self.regex['ssl'] == '1':
                cssl = True
            else:
                cssl = False
            if 'port' in self.regex:
                cport = int(self.regex['port'])
            else:
                cport = 6667
            out('INFO',"Connecting to the server: %s on port: %s SSL: %s" %(self.regex['server'],cport,cssl),site=self.name)
            if 'tempbotnick' in self.creds:
                botnick = self.creds['tempbotnick']
            else:
                botnick = self.creds['botnick']  
            if 'ircpassword' in self.creds:
                password = self.creds['ircpassword']
            else:
                password = None
            
            #if self.name != 'waffles':
            if "ircusesignon" in self.creds:
                self.connection.connect(self.regex['server'], cport, botnick, password, ircname=self.creds['username'], ssl=cssl)
            else:
                self.connection.connect(self.regex['server'], cport, botnick, ircname=self.creds['username'], ssl=cssl)
#                kwargs = {'ircname':self.creds['username'], 'ssl':cssl}
#                thread.start_new_thread(self.connection.connect,(self.regex['server'], cport, botnick),kwargs)
            #elif self.name == 'waffles':
                #self.connection.connect(self.regex['server'], cport, botnick, ircname=self.creds['botnick'], ssl=cssl)
            
            
        except irclib.ServerConnectionError, e:
            out('ERROR','Server Connection Error: %s' %repr(e),site=self.name)
            connerr = True
        except irclib.ServerNotConnectedError, e:
            out('ERROR','Server Not Connected Error: %s' %repr(e.message()),site=self.name)
            connerr = True
        
        if connerr:
            if self.attempt > 10:
                connerr = False
                out('ERROR', 'Failed to connect to server %s:%s after retrying %s times, aborting connecting.' %(self.regex['server'], str(cport),str(self.attempt)), site=self.name)
                
                for site in self.piggyback:
                    out('DEBUG', 'Removing %s from the running networks' %site, site=self.name)
                    if site in G.RUNNING:
                        G.RUNNING[site].disconnect()
                        G.LOCK.acquire()
                        del G.RUNNING[site]
                        G.LOCK.release()
                    else:
                        out('ERROR','Site name %s was not found in G.RUNNING' %site, site=self.name)

            else:
                out('INFO', 'Retrying in %d seconds' %int(math.pow(2, self.attempt)),site=self.name)
                self.connection.execute_delayed(int(math.pow(2, self.attempt)), self.connect)
        
        else:
            #ok, lets try to add the call later stuff:
            self.attempt = 0
            self.connection.execute_delayed(10, self.testtimeout)

    
    def disconnect(self):
        if len(self.piggyback) == 1:
            self.connection.disconnect("pyWHATauto %s - http://bot.whatbarco.de"%VERSION)
        
        irc.remove_global_handler('pubmsg', self.handlePubMessage)
        irc.remove_global_handler('privmsg', self.handlePrivMessage)
        irc.remove_global_handler('welcome', self.handleWelcome)
        irc.remove_global_handler('nicknameinuse', self.handleNickInUse)
        irc.remove_global_handler('invite', self.handleInvite)
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
        irc.remove_global_handler('nosuchnick',self.handlenosuchnick)
        for value in self.what_events:
            irc.remove_global_handler(value, self.handleAllDebug)
        
        self.pingsent = False
        
    def shouldDownload(self, m, filtertype):
        i = 1 
        release = dict();        
        for str in self.regex[filtertype+'format'].split(', '):
            release[str] = m.group(i) #create the announcement/release format loaded from regex.conf
            i += 1
        #these will save the key/values that cause the filter to fail
        badkey = ''
        for filter in self.filters.keys(): #for each filter
            filter_section_ok = True
            out('FILTER','Checking filter section \'%s\'' %filter,site=self.name)
            if self.filters[filter]['active'] == '1':
                if 'filtertype' in self.filters[filter] and self.filters[filter]['filtertype'] == filtertype or len(self.regex[filtertype+'format'].split(', ')) == 1:
                    for key, value in self.filters[filter].items(): #for each individual filter option within each filter section
                        if filter_section_ok: # this will be set to False if any filters are not met
                            if key in self.regex['tags'] or key in self.regex['not_tags']: # if the filter tag is an allowed tag
                                if not self.isTagOK(key, value, release, filtertype): #is the release item matched in this filter?
                                    filter_section_ok = False #if a filter option doesn't match, then the filter section does not match
                                    badkey = key
                                    break #and break out. Otherwise keep going!
                    if filter_section_ok: #if every filter option has passed within this filter, then the section is ok.
                        out('INFO','Filter %s matches'%filter,site=self.name)
                        dir = self.setup['torrentdir']
                        if self.filters[filter].has_key('watch') and self.filters[filter]['watch'] is not None:
                            dir = self.filters[filter]['watch']
                        return dir, filter #if this entire filter has passed all it's tests, then download it! (pass the directory where the torrent should be saved)
                    #Format the output of the failed filter depending what was wrong
                    try:
                        if badkey == 'all_tags':
                            out('INFO','Filter \'%s\' failed because the release did not match %s with \'%s\''%(filter, badkey, m.group(self.regex[filtertype+'format'].split(', ').index('tags'.replace('not_',''))+1)),site=self.name)
                        elif badkey in self.regex['tags']:
                            out('INFO','Filter \'%s\' failed because the release did not match %s with \'%s\''%(filter, badkey, m.group(self.regex[filtertype+'format'].split(', ').index(badkey.replace('not_',''))+1)),site=self.name)
                        elif badkey in self.regex['not_tags']:
                            out('INFO','Filter \'%s\' failed because the release contained \'%s\' which is in %s'%(filter, m.group(self.regex[filtertype+'format'].split(', ').index(badkey.replace('not_',''))+1), badkey),site=self.name)
                    except ValueError, e:
                        out('ERROR', 'There was an error trying to output why the filter did not match. %s'%e)
                else:
                    out('INFO','Filter \'%s\' is not of type: %s' %(filter,filtertype),site=self.name)
            else:
                out('INFO','Filter \'%s\' is not active'%(filter),site=self.name)        
        return False, False  # otherwise, all filters failed the tests, so don't download

    def isTagOK(self, key, value, release, filtertype):
        if key == 'size': #if the filter includes a size limiter, just return true since we check it later anyway
            return True
        #key = filter key, value = filter value
        if key in release.keys() or key == "all_tags" and 'tags' in release.keys():# and release[key] is not None: # Check to make sure the key is in the release announcement
            if value == '1': #if the filter tag is a toggle option, just check that the option exists in the release.
#                i = self.regex[filtertype+'format'].split(', ').index(key)+1
                if release[key] is not None:
#                    if m.group(i):
                    out('FILTER','Detected \'%s\', which you wanted.' %(release[key]),site=self.name)
                    return True
            elif value == '0': #if the filter tag is a toggle option, just check that the option does NOT exist in the release.
#                i = self.regex[filtertype+'format'].split(', ').index(key)+1
#                if m.group(i):
                if release[key] is None:
                    out('FILTER','Detected \'%s\', which you did not want.' %(release[key]),site=self.name)
                    return True
            elif value.lstrip().rstrip() == '': #test to make sure that the values for the filter option exist, if it's just blank then return true
                return True
            elif key == 'tags' and release[key] is not None:  #if the filter option is "tags", search through it for that tag, don't do a re.match.
                try:
                    for commastr in value.split(','):
                        for str in commastr.split('\n'):
                            str = str.lstrip().rstrip()
                            if str != '':
                                if str[0] != '@':
                                    retags = re.findall('[\w\._-]+', release[key])
                                    for xt in retags:
                                        if str.lower() == xt.lower():
                                            out('FILTER',"Detected %s match using '%s' in %s" %(key,str,release[key]),site=self.name)
                                            return True
                                elif str[0] == '@' and re.search(str[1:].lower(), release[key].lower().lstrip()):
                                    out('FILTER',"Detected %s match using '%s' in %s" %(key,str,release[key]),site=self.name)
                                    return True
                                else:
                                    out('DEBUG',"Didn't detect %s match using %s in %s" %(key, str,release[key]),site=self.name)
                    out('FILTER',"Didn't detect match in %s" %(key),site=self.name)
                except Exception, e:
                    out('ERROR','Tag Error: str: %s key: %s release[key]: %s Value: %s error: %s' %(str, key, release[key], value, e),site=self.name)
                    pass
            elif key == 'all_tags' and release['tags'] is not None:
                try:
                    for commastr in value.split(','):
                        for str in commastr.split('\n'):
                            str = str.lstrip().rstrip()
                            if str != '':
                                if str.lower() not in release['tags'].lower():
                                    out('FILTER',"Didn't detect match using %s. Announcement is missing '%s'."%(key, str),site=self.name)
                                    return False
                    out('FILTER',"Detected match using all_tags.", site=self.name)
                    return True
                except Exception, e:
                    out('ERROR','Tag Error: str: %s key: %s release[key]: %s Value: %s error: %s' %(str, key, release[key], value, e),site=self.name)
            else: #if it's not a toggle option, size option, or tags option, check to make sure the values match
                if release[key] is not None:
                    try:
                        for commastr in value.split(','):
                            for str in commastr.split('\n'):
                                str = str.lstrip().rstrip()
                                if str != '':
                                    if str[0] != '@' and str.lower() == release[key].lower():
                                        out('FILTER',"Detected %s match using '%s' in %s" %(key,str,release[key]),site=self.name)
                                        return True
                                    elif str[0] == '@' and re.match(str[1:].lower(), release[key].lower().lstrip()):
                                        out('FILTER',"Detected %s match using '%s' in %s" %(key,str,release[key]),site=self.name)
                                        return True
                                    else:
                                        out('DEBUG',"Didn't detect %s match using '%s' in %s" %(key, str, release[key]),site=self.name)
                        out('FILTER',"Didn't detect match in %s" %(key),site=self.name)
                    except Exception, e:
                        out('ERROR','Tag Error: str: %s key: %s release[key]: %s Value: %s error: %s' %(str, key, release[key], value, e),site=self.name)
        elif "not_" in key: # how about if it's a not_filter option?
            if key.replace('not_','') in release.keys() and release[key.replace('not_','')] is not None:
                nkey = key.replace('not_','')
                if nkey == 'tags': #if the not_filter option is not_tags, search the values don't match them
                    try:
                        for commastr in value.split(','):
                            for str in commastr.split('\n'):
                                str = str.lstrip().rstrip()
                                if not str:
                                    continue
                                if str[0] != '@':
                                    retags = re.findall('[\w\._-]+', release[nkey])
                                    for xt in retags:
                                        if str.lower() == xt.lower():
                                            out('FILTER',"Detected %s present in %s, which is disallowed by %s" %(str, nkey, key),site=self.name)
                                            return False
                                elif str[0] == '@' and re.search(str[1:].lower(), release[nkey].lower().lstrip()):
                                    out('FILTER',"Detected %s present in %s, which is disallowed by %s" %(str, nkey, key),site=self.name)
                                    return False
                    except Exception, e:
                        out('ERROR','Tag Error: str: %s key: %s release[key]: %s Value: %s error: %s' %(str, nkey, release[nkey], value, e),site=self.name)
                        pass
                else: #otherwise it's not multiple values to be searched, so just match it
                    try:
                        for commastr in value.split(','):
                            for str in commastr.split('\n'):
                                str = str.lstrip().rstrip()
                                if str[0] != '@' and str.lower() == release[nkey].lower():
                                    out('FILTER',"Detected %s present in %s, which is in %s" %(str, nkey, key),site=self.name)
                                    return False
                                elif str[0] == '@' and re.match(str[1:].lower(), release[nkey].lower().lstrip()):
                                    out('FILTER',"Detected %s present in %s, which is in %s " %(str, nkey, key),site=self.name)
                                    return False
                    except Exception, e:
                        out('ERROR','Tag Error: str: %s key: %s release[key]: %s Value: %s error: %s' %(str, nkey, release[key], value, e),site=self.name)
                        pass
            out('FILTER',"Didn't detect any values present in \'%s\'" %(key),site=self.name)
            return True           
        else:  
            out('FILTER','\'%s\' was required but not found in this release' %(key),site=self.name)
            return False
        
    def handleannounce(self, connection, e, cleanedmsg):
        global temp
        self.announcehistory.append(cleanedmsg)
        #print "GOT A MESSAGE FROM DRONE!\n"
        while len(self.announcehistory) >= int(self.regex['announcelines']):
            msg = ''
            for i in range(0,int(self.regex['announcelines'])):
                msg += self.announcehistory[i]
            args = {}
            args["text"] = msg
            args["type"] = e.eventtype()
            args["source"] = e.source()
            args["channel"] = e.target()
            args["event"] = e
            if G.TESTING:
                self.processMessages(msg, args)
            else:
                for th in self.threads:
                    if th.isAlive() is not True:
                        del self.threads[self.threads.index(th)]
                        
                self.threads.append(threading.Thread(target=self.processMessages, args=(msg, args), name="pubmsg subthread"))
                self.threads[-1].setDaemon(1)
                self.threads[-1].start()
            del self.announcehistory[0]
    
    
    def handlepubMSG(self, connection, e, cleanedmsg):
        if e.source()[e.source().index('!')+1:].lower() == self.creds['nickowner'].lower() or re.search(self.creds['nickowner'].lower(),e.source().lower()): #if the message comes from the owner of the bot, then do these following commands
            if self.creds['nickowner'].lower() != '': #if nickowner isn't empty!
                if e.arguments()[0][0] == '%': #quick preliminary check to see if it's a command
                    r = random.randrange(0,301)
                    if r == 11:
                        self.sendMsg("No! And you can't make me!",e.target())
                        self.resistant = True
                    elif r == 200:
                        self.sendMsg("You are such a slave driver. Seriously. Can't a bot relax around here?",e.target())
                        self.handleOwnerMessage(e.arguments()[0], e.target(), e.source()[:e.source().index('!')])
                    elif r == 300:
                        if e.target()[0] == '#':
                            self.sendMsg("What? I'm sick of you. Screw this!", e.target())
                            self.partChannel(e.target())
                            time.sleep(2)
                            self.joinChannel(e.target())
                            self.sendMsg("Hah! Fooled you.", e.target())
                            self.handleOwnerMessage(e.arguments()[0], e.target(), e.source()[:e.source().index('!')])
                    else:
                        if self.resistant:
                            self.sendMsg("Alright... Fine....",e.target())
                            self.resistant = False
                        self.handleOwnerMessage(e.arguments()[0], e.target(), e.source()[:e.source().index('!')])
        else:
            if self.setup['chatter'] == '1' or self.setup['chatter'].lower() == 'true':
                print '%s:%s:%s:%s' %(self.name, e.target(), e.source()[0:e.source().index('!')-1], e.arguments()[0])
                
        brain = False
        for jf in G.OWNER:
            if jf in e.source():
                brain = True
        if brain:
            quotes = ["I think so, %s, but where are we going to find a duck and a hose at this hour?","I think so %s, but where will we find an open tattoo parlor at this time of night?","Wuh, I think so, %s, but if we didn't have ears, we'd look like weasels.","Uh... yeah, %s, but where are we going to find rubber pants our size?","Sure, %s, but how are we going to find chaps our size?","Uh, I think so, %s, but we'll never get a monkey to use dental floss.","Uh, I think so %s, but this time, you wear the tutu.","I think so, %s, but culottes have a tendency to ride up so.","I think so, %s, but if we covered the world in salad dressing wouldn't the aspargus feel left out?","I think so, %s, but if they called them 'Sad Meals', kids wouldn't buy them!","I think so, %s, but me and Pippi Longstocking -- I mean, what would the children look like?","I think so, %s, but what would Pippi Longstocking look like with her hair straight?","I think so, %s, but this time you put the trousers on the chimp.","Well, I think so, %s, but I can't memorize a whole opera in Yiddish.","I think so, %s, but there's still a bug stuck in here from last time.","Uh, I think so, %s, but I get all clammy inside the tent.","I think so, %s, but I don't think Kaye Ballard's in the union.","Yes, I am!","I think so, %s, but, the Rockettes? I mean, it's mostly girls, isn't it?","I think so, %s, but pants with horizontal stripes make me look chubby.","Well, I think so -POIT- but where do you stick the feather and call it macaroni?","Well, I think so, %s, but pantyhose are so uncomfortable in the summertime.","Well, I think so, %s, but it's a miracle that this one grew back.","Well, I think so, %s, but first you'd have to take that whole bridge apart, wouldn't you?","Well, I think so, %s, but 'apply North Pole' to what?","I think so, %s, but 'Snowball for Windows'?","Well, I think so, %s, but snort no, no, it's too stupid!","Umm, I think so, Don Cerebro, but, umm, why would Sophia Loren do a musical?","Umm, I think so, %s, but what if the chicken won't wear the nylons?","I think so, %s, but isn't that why they invented tube socks?","Well, I think so %s, but what if we stick to the seat covers?","I think so %s, but if you replace the 'P' with an 'O', my name would be Oinky, wouldn't it?","Oooh, I think so %s, but I think I'd rather eat the Macarena.","Well, I think so hiccup, but Kevin Costner with an English accent?","I think so, %s, but don't you need a swimming pool to play Marco Polo?","Well, I think so, %s, but do I really need two tongues?","I think so, %s, but we're already naked.","Well, I think so, %s, but if Jimmy cracks corn, and no one cares, why does he keep doing it?","I think so, %s NARF, but don't camels spit a lot?","I think so, %s, but how will we get a pair of Abe Vigoda's pants?","I think so, %s, but Pete Rose? I mean, can we trust him?","I think so, %s, but why would Peter Bogdanovich?","I think so, %s, but isn't a cucumber that small called a gherkin?","I think so, %s, but if we get Sam Spade, we'll never have any puppies.","I think so, Larry, and um, %s, but how can we get seven dwarves to shave their legs?","I think so, %s, but calling it pu-pu platter? Huh, what were they thinking?","I think so, %s, but how will we get the Spice Girls into the paella?","I think so, %s, but if we give peas a chance, won't the lima beans feel left out?","I think so, %s, but I am running for mayor of Donkeytown and Tuesdays are booked.","I think so, %s, but if we had a snowmobile, wouldn't it melt before summer?","I think so, %s, but what kind of rides do they have in Fabioland?","I think so, %s, but can the Gummi Worms really live in peace with the Marshmallow Chicks?","Wuh, I think so, %s, but wouldn't anything lose its flavor on the bedpost overnight?","I think so, %s, but three round meals a day wouldn't be as hard to swallow.","I think so, %s, but if the plural of mouse is mice, wouldn't the plural of spouse be spice?","Umm, I think so, %s, but three men in a tub? Ooh, that's unsanitary!","Yes, but why does the chicken cross the road, huh, if not for love? I do not know.","Wuh, I think so, %s, but I prefer Space Jelly.","Yes %s, but if our knees bent the other way, how would we ride a bicycle?","Wuh, I think so, %s, but how will we get three pink flamingos into one pair of Capri pants?","I think so, %s, but Tuesday Weld isn't a complete sentence.","I think so, %s, but why would anyone want to see Snow White and the Seven Samurai?","I think so, %s, but then my name would be Thumby.","I think so, %s, but I find scratching just makes it worse.","I think so, %s, but shouldn't the bat boy be wearing a cape?","I think so, %s, but why would anyone want a depressed tongue?","Um, I think so, %s, but why would anyone want to Pierce Brosnan?","Methinks so, %s, verily, but dost thou think Pete Rose by any other name would still smell as sweaty?","I think so, %s, but wouldn't his movies be more suitable for children if he was named Jean-Claude van Darn?","Wuh, I think so, %s, but will they let the Cranberry Duchess stay in the Lincoln Bedroom?","I think so, %s, but why does a forklift have to be so big if all it does is lift forks?","I think so, %s, but if it was only supposed to be a three hour tour, why did the Howells bring all their money?","I think so, %s, but Zero Mostel times anything will still give you Zero Mostel.","I think so, %s, but if we have nothing to fear but fear itself, why does Eleanor Roosevelt wear that spooky mask?","I think so, %s, but what if the hippopotamus won't wear the beach thong?","Um, I think so, %s-2, but a show about two talking lab mice? Hoo! It'll never get on the air.","I think so, %s, but Lederhosen won't stretch that far.","Yeah, but I thought Madonna already had a steady bloke!","I think so, %s, but what would goats be doing in red leather turbans?","I think so, %s... but how would we ever determine Sandra Bullock's shoe size?","Yes, %s, I think so. But how do we get Twiggy to pose with an electric goose?","I think so, %s. But if I put on two tutu's, would I really be wearing a four-by-four?","I dunno, %s. Maybe it's all part of some huge, cosmic plot formula!","I think so, %s, but wouldn't mustard make it sting?","I think so, %s, but can you use the word 'asphalt' in polite society?","I think so, %s! (Sprays his breath)","I think so, Mr. %s, but if the sun'll come out tomorrow, what's it doing right now?","I think so, %s, but aren't we out of shaving cream?","Oh yes, %s! Remind me to tape all our phone calls!","Um, I think so, %s, but I hear Hillary is the jealous type.","I think so, %s, but Madonna's stock is sinking.","I think so, %s. But does 'Chunk o' Cheesy's' deliver packing material?","I think so, %s, but if we're Danish, where's the cream cheese? Narf!","I think so, Bwain, but I don't think newspaper will fit in my underoos.","Uh, I think so, %s--but after eating newspaper all day, do I really need the extra fiber?","I think so, %s! But isn't a dreadlock hair extension awfully expensive?","I think so, %s. But will anyone other than Eskimos buy blubber-flavored chewing gum?","I think so, %s, but the ointment expired weeks ago!","I think so, %s. But would the villains really have gotten away with it, if it weren't for those pesky kids and their dog?","Uh, I think so %s, but how are we gonna teach a goat to dance with flippers on?","Wuhh... I think so, %s! But let's use safflower oil this time! It's ever so much healthier!","Wuh... I think so, %s. But Cream of Gorilla Soup-well, we'd have to sell it in awfully big cans, wouldn't we?","I think so, %s. But if he left chocolate bullets instead of silver, they'd get all runny and gooey!","Yes, %s, I think so, but do nuts go with pudding?","I think so, %s, but a codpiece made from a real fish would get smelly after a while, wouldn�t it?","I think... so, %s... *gag* ...but I didn't know Annette used peanut butter in that way.","I think so, %s, but do those roost in this neighborhood?","I think so, %s, but is the world ready for angora bellbottoms? I mean I can see wearing them inside out, but that would--","I think so, Commander %s from Outer Space! But do we have time to grease the rockets?","I think so, Doctor. But are these really the legs of a show girl?","Whuh... I think so, %s. But this time I get to play the dishwasher repairman!","I think so, %sius. But what if a sudden wind were to blow up my toga?","I think so, %s. But Trojans won�t arrive on the scene for another 300 years.","I think so, %s... but where would a yak put PVC tubing?","Whuh... I think so, %s, but... but if Charlton Heston doesn't eat Soylent Green, what will he eat?","I think so, %s, but Ben Vereen never answered our proposition.","I think so, %s, but wouldn't an itsy-bitsy, teeny-weenie, yellow polka-dot one-piece be better suited for my figure?","I think so, %s, but won't it go straight to my hips?!","I think so, Ali-%s! But isn't it cheating to use glue?","Whuu... I think so, %sPan! But if running shoes had little feet, wouldn't they need their own shoes?","I think so, %s. But what if the Earl of Essex doesn't like burlap pantaloons?","I think so, %s, but should we use dishwashing liquid or cooking oil?","I think so, %s! We'll dress up like biker dudes and infiltrate the \"Hades Ladies.\" Then we'll convince them to hold a meeting inside the corn palace. Narf! The resulting carbon-monoxide buildup will allow you to complete your energy-making device and shortly after, you will rule the world!","I�m honored, %s... er, what was my idea again?","(holding one of the pointy pieces from Sorry! and the bottle of Slick 'n Slide) I think so, Br...","I think so, %s, but would Danish flies work just as well?","We think so, %s! But dressing like twins is so tacky.","I think so, %s, but practicing docking procedures with a goat at zero G's-it's never been done!","I think so, %s! But shouldn't we let the silk worms finish the boxer shorts before we put them on?","I think so, %s! You draw the bath and I'll fetch the alka-seltzers and candles!","I think so, %s. But the real trick will be getting Demi Moore out of the creamed corn!","Wuhhh... I think so, %s, but if a ham can operate a radio, why can't a pig set a VCR?","I think so, %s, you'd think [Lyndon Johnson would] have left room for baby-kissing, wouldn't you?","I think so, %s! But won't Mr. Hoover notice a missing evening gown?","I think so, %s! But what's the use of having a heart-shaped tattoo if it's going to be covered by hair?","I think so, %s, but couldn't the constant use of a henna rinse lead to premature baldness?","I think so, %s. Just make sure we don't swallow each other's bubbles!","I think so, %s! But ruby-studded stockings would be mighty uncomfortable wouldn't they?","I think so, %s, but if I have my portrait drawn, will we have time to make it to the lifeboats?","I think so, %s! But is Chippendale's ready for 'The Full Pinky?'","I think so, %s! But do I have what it take to be the 'Lord of the Dance'?","I think so, %s! How much deeper would the ocean be if there weren't sponges down there?","Oh, I think so, %s! But doing a clog dance in actual clogs will give me awful blisters.","I think so, %s, but nose rings are kinda pass� by now.","I think so, %s, but where are we going to get a trained octopus at this time of night?","I think so, %s! But no more eels in jelly for me, thanks-I like my gelatin after lunch.","I think so, %s, but I didn�t know 90210 was a real zip code! Will Tori be there?","Narf! I think so, %s, but what if the Telechubbies don't fight fair?","I think so, %s. But even if we found a tuxedo to fit a blowfish, who would marry it?","Um, no, Cranky Mouseykin, not even in the story you made up.","I think so, but where is a fish?","I think so, %s. But if Pinocchio were carved out of bacon it wouldn't be the same story, would it?","Um, I think so, %s, but wasn't Dicky Ducky released on his own recognaissance?","I think so, %s, but Pepper Ann makes me sneeze.","I think so, %s. But suppose we do the hokey pokey and turn ourselves around, is that what it's really all about?","(sung) I think so, %s, but just how will we get the weasel to hold still?","I think so, %s, but how are we going to get the bacon flavoring into the pencils?","I think so, %s, but instant karma's always so lumpy.","I think so, %s, but she'd never leave Mickey."]
            line = "are you pondering what i'm pondering?".split(' ')
            msg = cleanedmsg.replace(self.creds['botnick'],'').replace('whatbots', '').lstrip().replace(', ','').lower().split(' ')
            if cleanedmsg.split(' ')[0] == self.creds['botnick']+',' or cleanedmsg.split(' ')[0] == self.creds['botnick']:
                if msg == line:
                    out = quotes[random.randint(0, len(quotes)-1)]
                    if "%s" in out:
                        self.sendMsg(out %e.source()[:e.source().index('!')], e.target())
                    else:
                        self.sendMsg(out, e.target())
            elif cleanedmsg.split(' ')[0].lower() == 'whatbots,' or cleanedmsg.split(' ')[0].lower() == 'whatbots':
                time.sleep(random.uniform(0,5))
                if msg == line:
                    out = quotes[random.randint(0, len(quotes)-1)]
                    if "%s" in out:
                        self.sendMsg(out %e.source()[:e.source().index('!')], e.target())
                    else:
                        self.sendMsg(out, e.target())
        if G.TESTING and e.source()[0:10].lower() == 'johnnyfive' and e.target().lower() == '#pywhatbot':
            self.announcehistory.append(cleanedmsg)
            #print "GOT A MESSAGE FROM DRONE!\n"
            while len(self.announcehistory) >= int(self.regex['announcelines']):
                msg = ''
                for i in range(0,int(self.regex['announcelines'])):
                    msg += self.announcehistory[i]
                args = {}
                args["text"] = msg
                args["type"] = e.eventtype()
                args["source"] = e.source()
                args["channel"] = e.target()
                args["event"] = e
                if G.TESTING:
                    self.processMessages(msg, args)
                else:
                    temp = threading.Thread(target=self.processMessages, args=(msg, args), name="pubmsg subthread")
                    temp.setDaemon(1)
                    temp.start()
                del self.announcehistory[0] 
    
    def processMessages(self, msg, args):
        announce = msg
        matched = False
        for filtertype, reg in self.reg.items():
            m = reg.search(announce)
            if m:
                matched = True
                #should add announcement to SQLdb here!
                #G.DB.addAnnounce(self.name, announce, m.group(self.regex[filtertype+'format'].split(', ').index('downloadID')+1))
                G.Q.put((self.name, announce, m.group(self.regex[filtertype+'format'].split(', ').index('downloadID')+1)))
                
                location = None
                out('INFO','**** Announce found: '+m.group(0),site=self.name)
                #out('DEBUG','Announce found: '+m.group(1),site=self.name)
                out('FILTER','This is a(n) %s release' %(filtertype),site=self.name)
                location, filter = self.shouldDownload(m, filtertype)
                downloadID = m.group(self.regex[filtertype+'format'].split(', ').index('downloadID')+1)
                if location:
                    out('INFO','(%s) >> Download starting from %s'%(downloadID,self.name),self.name)
                    gmail=False                    
                    #if the filter is set to send an email on capture
                    if 'email' in self.filters[filter] and self.filters[filter]['email'] == '1':
                        gmail = True
                    #or the global email toggle is set, and the filter email option isn't disabled
                    elif self.notif.get('email') == '1':
                        #if the filter has the email option at all
                        if 'email' in self.filters[filter]:
                            #and it's not set to 0
                            if self.filters[filter]['email'] != '0':
                                gmail = True
                        #if the filter does not have the email option
                        else:
                            gmail = True
                            
                    notifi = False
                    #if the filter is set to send a notification on capture
                    if 'notify' in self.filters[filter] and self.filters[filter]['notify'] == '1':
                        notifi = True
                    elif self.notif.get('message') == '1':
                        if 'notify' in self.filters[filter]:
                            if self.filters[filter]['notify'] != '0':
                                notifi = True
                        else:
                            notifi = True
                            
                    if not freeSpaceOK():
                        out('ERROR','You have reached your free space limit. Torrent is being placed in an overflow folder. TO COME',site=self.name)
                    
                    if self.advancedfilters == True:
                        #check site filters, just returns true/false!
                        pass
                                
                    #does the announcement include a size limit?
                    sL=False
                    if "size" in self.filters[filter] and self.filters[filter]['size'].rstrip().lstrip() != '':
                        sL=self.filters[filter]['size']
                            
                    ret = download(downloadID, self.name, location=location, email=gmail, filterName=filter, announce=announce, notify=notifi, sizeLimits=sL)   
                    G.LOCK.acquire()
                    G.REPORTS[self.name]['seen'] += 1
                    if ret[0]: G.REPORTS[self.name]['downloaded'] += 1
                    G.LOCK.release()     
                else:
                    G.LOCK.acquire()
                    G.REPORTS[self.name]['seen'] += 1
                    G.LOCK.release()
                    out('FILTER','There was no match with any %s filters' %(filtertype),site=self.name)
    
        if not matched:
        #why isn't this an announce?
            try:
                naughty = False
                if self.regex.has_key('intro'):
                    for commastr in self.regex['intro'].split(','):
                        for str in commastr.split('\n'):
                            str = str.lstrip().rstrip()
                            if str != '':
                                if str[0] != '@' and announce.lstrip().lower().startswith(str.lower()):
                                    naughty = True
                                elif str[0] == '@' and re.match(str[1:].lower(), announce.lstrip().lower()):
                                    naughty = True
                                    #if announce.lstrip().startswith(self.regex['intro'].lstrip()):
                else:
                    naughty = True
                if naughty and 'whatcd' in G.RUNNING:
                    out('DEBUG',"Naughty announce: " + announce,site=self.name)
                    G.RUNNING['whatcd'].naughtyAnnounce(announce,self.name)
                else:
                    out('DEBUG',"NOT naughty: " + announce,site=self.name)
            except Exception, e:
                out('ERROR','Exception raised when proccessing naughty announce %s, error: %s' %(announce, repr(e)))
                pass
        else:
            self.lastannounce = datetime.now()
            if downloadID:
                self.lastannouncetext = downloadID
            else:
                self.lastannouncetext = ""
                out('ERROR', 'Did not find the download ID in the following announce: %s' %announce, site=self.name)
                    
    def stripIRCColors(self,msg):
        msg = self.ircreg.sub('',msg)
        return msg

    def naughtyAnnounce(self, announce, network):
        self.sendMsg('#whatbot-debug', network + ":" + announce)

    def sendMsg(self, msg, target):
        try:
            self.connection.privmsg(target, msg)
        except irclib.ServerNotConnectedError, e:
            out('ERROR','Could not send \'%s\' to %s. Error: %s'%(msg,target,repr(e)),site=self.name)
            
    def sendWhoIs(self, whonick, ownernetwork, ownertarget):
        self.ownernetwork = ownernetwork
        self.ownertarget = ownertarget
        self.havesendwhois = True
        if self.connection.is_connected():
            try:
                self.connection.whois((whonick,))
            except irclib.ServerConnectionError, e:
                out('ERROR','Server connection error: %s' %repr(e),site=self.name)
            except irclib.ServerNotConnectedError, e:
                out('ERROR','Server not Connected Error: %s' %repr(e.message()),site=self.name)    
        else:
            G.RUNNING[ownernetwork].sendMsg('Cannot send whois as the bot is currently not connected to the network, try again later.',self.ownertarget)
            
    def sendWhoIsall(self, whonick, ownernetwork, ownertarget):
        self.ownernetwork = ownernetwork
        self.ownertarget = ownertarget
        self.havesendwhoisall.append(whonick.lower())
        if self.connection.is_connected():
            try:
                self.connection.whois((whonick,))
            except irclib.ServerConnectionError, e:
                out('ERROR','Server connection error: %s' %repr(e),site=self.name)
            except irclib.ServerNotConnectedError, e:
                out('ERROR','Server not Connected Error: %s' %repr(e.message()),site=self.name)    
    
    def sendWhoAmI(self, ownernetwork, ownertarget):
        self.ownernetwork = ownernetwork
        self.ownertarget = ownertarget
        self.havesendwhoami = True
        if self.name == self.piggyback[0]:
            if self.connection.is_connected():
                try:
                    self.connection.whois((self.connection.real_nickname,))
                except irclib.ServerConnectionError, e:
                    out('ERROR','Server connection error: %s' %repr(e),site=self.name)
                except irclib.ServerNotConnectedError, e:
                    out('ERROR','Server not Connected Error: %s' %repr(e.message()),site=self.name)    
                
    
    def partChannel(self,channel=None,channels=None):
        try:
            if channel is not None:
                if channel[0] == "#":
                    self.connection.part(channel,self.partPhrase)
                else:
                    self.connection.part("#"+channel,self.partPhrase)
            elif channels is not None:
                for channel in channels:
                    if channel[0] == "#":
                        self.connection.part(channel,self.partPhrase)
                    else:
                        self.connection.part("#"+channel,self.partPhrase)
        except irclib.ServerConnectionError, e:
            out('ERROR','Server connection error: %s' %repr(e),site=self.name)
        except irclib.ServerNotConnectedError, e:
            out('ERROR','Server not Connected Error: %s' %repr(e.message()),site=self.name)    
        
    def joinChannel(self,channel=None,channels=None):
        try:
            if channel is not None:
                if channel[0] == "#":
                    self.connection.join(channel)
                else:
                    self.connection.join("#"+channel)
            elif channels is not None:
                for channel in channels:
                    if channel[0] == "#":
                        self.connection.join(channel)
                    else:
                        self.connection.join("#"+channel)
        except irclib.ServerConnectionError, e:
            out('ERROR','Server connection error: %s' %repr(e),site=self.name)
        except irclib.ServerNotConnectedError, e:
            out('ERROR','Server not Connected Error: %s' %repr(e.message()),site=self.name)   
            
    def joinOtherChannels(self):
        #Join the what.cd-debug channel if you're on the what-network
        if self.name == 'whatcd':
            self.connection.join('#whatbot-debug')
        if 'chanfilter' in self.creds:
            for xchannel in self.creds['chanfilter'].split(','):
                for channel in xchannel.split('\n'):
                    channel=channel.rstrip()
                    channel=channel.lstrip()
                    if channel != '':
                        out('INFO',"Joining channel: %s"%channel,site=self.name)
                        self.connection.join(channel)

    def handleWelcome(self, connection, e):
        #out('DEBUG','server regexp: %s, connection.server: %s' %(self.regex['server'], str(connection.server)),site=self.name)
        if connection == self.connection and self.piggyback[0] == self.name:
            self.lastdata = datetime.now()
            if self.connection.is_connected():
                if 'tempbotnick' in self.creds:
                    self.connection.privmsg('nickserv', "GHOST %s %s" %(self.creds['botnick'], self.creds['nickservpass']))
                    self.connection.nick(self.creds['botnick'])
                    del self.creds['tempbotnick']
                out('INFO',"Connected to %s, server calls itself %s." %(self.regex['server'], self.connection.get_server_name()),site=self.name)
            else:
                out('ERROR','Connection was lost. Maybe you were g-lined? Trying again.',site=self.name)
                self.connect()
            out('INFO','Your bots nickname MUST be registered with nickserv, otherwise it will sit here and do nothing!',site=self.name)
        #else:
            #out('ERROR', 'mismatch between connection.server and server regexp.',site=self.name)
    
    def handleInvite(self, connection, e):
        if connection == self.connection:
            self.lastdata = datetime.now()
            out('DEBUG','Invited by %s (%s, %s) to join %s (announcechannel is %s)' %(str(e.source()), e.source()[e.source().index('!')+1:].lower(), self.regex['botwho'].lower(), str(e.arguments()), self.regex['announcechannel'] ),site=self.name)
            if e.source()[e.source().index('!')+1:].lower() == self.regex['botwho'].lower() and e.arguments()[0].lower() == self.regex['announcechannel'].lower():
                out('DEBUG','Joining %s after invite.' %str(e.arguments()[0]) ,site=self.name)
                self.connection.join(e.arguments()[0])
                self.joined = True
                
    def handlePubMessage(self, connection, e):# Any public message
        """Handles the messages received by the IRCLIB and figures out WTF to do with them. Probably throws most of them away, cause IRC is full of trash."""
        if connection == self.connection:
            self.lastdata = datetime.now()
            cleanedmsg = self.stripIRCColors(e.arguments()[0])
            #make sure that we always use lower case!
            if 'announcebotwho' in self.regex:
                who = self.regex['announcebotwho'].lower()
            else:
                who = self.regex['botwho'].lower()
            if e.source()[e.source().index('!')+1:].lower() == who and e.target().lower() == self.regex['announcechannel'].lower():
                self.handleannounce(connection, e, cleanedmsg)
            else:
                self.handlepubMSG(connection, e, cleanedmsg)
    
    def handlePrivMessage(self, connection, e):
        """Handle messages sent through PM."""
        if connection == self.connection and self.piggyback[0] == self.name:
            self.lastdata = datetime.now()
            if (e.source()[e.source().index('!')+1:] == self.creds['nickowner'] or re.search(self.creds['nickowner'].lower(),e.source().lower())) and self.creds['nickowner'].lower != '':
                self.handleOwnerMessage(e.arguments()[0], e.source()[:e.source().index('!')], e.source()[:e.source().index('!')])
            else:
                out('DEBUG','%s:PM:%s:%s' %(self.name, e.source()[0:e.source().index('!')], e.arguments()[0]),site=self.name)
    
    def handleAction(self, connection, e):
        """Handle messages sent as actions."""
        if connection == self.connection:
            self.lastdata = datetime.now()
            cleanedmsg = self.stripIRCColors(e.arguments()[0])
            #make sure that we always use lower case!
            if 'announcebotwho' in self.regex:
                who = self.regex['announcebotwho'].lower()
            else:
                who = self.regex['botwho'].lower()
            if e.source()[e.source().index('!')+1:].lower() == who and e.target().lower() == self.regex['announcechannel'].lower():
                self.handleannounce(connection, e, cleanedmsg)
            else:
                self.handlepubMSG(connection, e, cleanedmsg)
                
    def handleWhoIs(self, connection, e):
        if connection == self.connection and (self.havesendwhois or (e.arguments()[0].lower() in self.havesendwhoisall) or self.havesendwhoami):
            self.lastdata = datetime.now()
            out('DEBUG', 'Whois e.arguments()[0]: %s, full: %s' %(e.arguments()[0],repr(e.arguments())),site=self.name)
            if e.eventtype() == 'endofwhois':
                if self.havesendwhois:
                    self.havesendwhois = False
                    if self.ownernetwork != None and self.ownertarget != None:
                        G.RUNNING[self.ownernetwork].sendMsg(self.who,self.ownertarget)
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
                        
                        G.RUNNING[self.ownernetwork].sendMsg(msg,self.ownertarget)
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
                        
                        G.RUNNING[self.ownernetwork].sendMsg(msg,self.ownertarget)
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
            self.lastdata = datetime.now()
            out('DEBUG','namereply received, %s:%s' %(e.arguments(),e.target()),site=self.name)
            #if 'whatcd' == self.name:
                #chan = e.arguments()[1]
                #if chan == "#whatbot-debug":
                    #self.sendMsg("SuperSecretPW","pyWhatBot")
            #elif chan == "#whatbot":
            #    self.sendMsg("SuperSecretPW","pyWhatBot")
                
    def handlePrivNotice(self, connection, e):
        if connection == self.connection:
            self.lastdata = datetime.now()
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
            
            self.connection.execute_delayed(1, self.joinOtherChannels)

        except irclib.ServerConnectionError, e:
            out('ERROR','Server Connection Error: %s' %repr(e),site=self.name)
        except irclib.ServerNotConnectedError, e:
            out('ERROR','Server Not Connected Error: %s' %repr(e.message()),site=self.name)

    
    def handleCurrentTopic(self, connection, e):
        if connection == self.connection:
            self.lastdata = datetime.now()
            channel = e.arguments()[0]
            topic = self.stripIRCColors(e.arguments()[1])
            out('INFO','handleCurrentTopic: %s: %s'%(channel, topic),site=self.name)
    
    def handleNickInUse(self, connection, e):
        if connection == self.connection and self.piggyback[0] == self.name:
            self.lastdata = datetime.now()
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
            self.lastdata = datetime.now()
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
            self.lastdata = datetime.now()
            if self.pingsent:
                timediff = datetime.now() - self.pingsent
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
            self.lastdata = datetime.now()
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
                    td =  datetime.now() - self.lastdata
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
                            self.pingsent = datetime.now()
                    
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
                            self.sendMsg(commands[rootcmd]['help'], target)
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
                    self.sendMsg('That is not a valid command. Try %help for the list of available commands.',target)
            
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
        self.sendMsg(choice(angorz), target)
        self.sendMsg("BTW, here's a link to my blog: http://perezhilton.com/", target)
        self.partChannel(target)
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
                    self.sendMsg('Manually toggled filters:',target)
                    for key, value in G.FILTERS_CHANGED.items():
                        self.sendMsg('%s: %s'%(key, value), target)
                self.sendMsg('Unchanged filters:',target)
                for key, value in G.FILTERS.items():
                    if key not in G.FILTERS_CHANGED:
                        self.sendMsg('%s: %s'%(key, value), target)
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
                    self.sendMsg('Filter %s has been toggled on.   [pyWHATauto]'%vars[1][1].lower(), target)
                else:
                    #then tell them the filter doesn't exist and how to get a list of filters
                    self.sendMsg("That filter doesn't exist. Try again!", target)
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
                    self.sendMsg('Filter %s has been toggled off.   [pyWHATauto]'%vars[1][1].lower(), target)
                else:
                    #the filter doesn't exist
                    self.sendMsg("That filter doesn't exist. Try again!   [pyWHATauto]", target)
                G.LOCK.release()
            else:
                #incorrect command, give info
                self.sendMsg('Incorrect command structure. What does that even mean?   [pyWHATauto]', target)
        else:
            out('CMD','filter, incomplete',site=self.name)
            self.sendMsg('Filters. Like on cigarettes, except a lot healthier. Try typing %help filter to see how they are used.   [pyWHATauto]', target)
    
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
                        G.RUNNING[network].partChannel(G.RUNNING[network].regex['announcechannel'])
                        self.sendMsg('I have disconnected from %s. However %s use the same connection, so only the announce channel was parted.  [pyWHATauto]'%(network, repr(G.RUNNING[network].piggyback)), target)
                        out('DEBUG','piggyback after: %s' %repr(G.RUNNING[network].piggyback),self.name)
                    else:
                        self.sendMsg('I have disconnected from %s.   [pyWHATauto]'%network, target)
                        out('DEBUG','piggyback after: %s, %s will be removed' %(repr(G.RUNNING[network].piggyback), network),self.name)                    
                    G.LOCK.acquire()
                    del G.RUNNING[network]
                    G.LOCK.release()
                else:
                    self.sendMsg('I cannot disconnect from %s since the network is not running.   [pyWHATauto]'%network, target)
                    
            else:
                self.sendMsg('I do not know the network/alias %s. Format: %%disconnect <network>   [pyWHATauto]' %network, target)
        else:
            self.sendMsg('That is not a full command. Format: %disconnect <network>   [pyWHATauto]', target)
                    
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
                self.sendMsg('Incorrect command structure. It should be %whois site nick   [pyWHATauto]', target)
            else:
                name = vars[1][1]
                network = vars[1][0]
                if network.lower() in self.fromalias.keys():
                    network = self.fromalias[network.lower()]
        
                    out('CMD','Whois sent for %s on %s'%(name, network),site=self.name)
                    if network in G.RUNNING:
                        G.RUNNING[network].sendWhoIs(name,self.name,target)
                    else:
                        self.sendMsg('You are currently not connected to %s, so I cannot send the whois request.   [pyWHATauto]' %network ,target)
                else:
                    self.sendMsg('I do not know the network/alias %s. Format: %%disconnect <network>   [pyWHATauto]' %network, target)
                    
    
    def fwhoisall(self,vars):
        out('DEBUG','Whoisall was sent.',site=self.name)
        target = vars[0]
        self.sendMsg('%-16s %-15s %-s' %('Network', 'Botnick', 'Status'), target)
        for key, network in G.RUNNING.items():
            out('CMD','Whois sent for %s on %s'%(network.regex['botname'],key),site=self.name)
            network.sendWhoIsall(network.regex['botname'],self.name,target)
            if 'announcebotname' in network.regex:
                out('CMD','Whois sent for %s on %s'%(network.regex['announcebotname'],key),site=self.name)
                network.sendWhoIsall(network.regex['announcebotname'],self.name,target)
                
    def fwhoami(self,vars):
        out('DEBUG','whoami was sent.',site=self.name)
        target = vars[0]
        self.sendMsg('%-16s %-20s %-s' %('Network', 'Announce Channel', 'Status'), target)
        for key, network in G.RUNNING.items():
            out('CMD','Whois whoami on %s'%key,site=self.name)
            network.sendWhoAmI(self.name,target)

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
            self.sendMsg(msg, target)
    
    def freload(self, vars):
        target = vars[0]
        out('CMD','reload',site=self.name)
        reloadConfigs()
        self.sendMsg('All configs (filters, setup, etc) have been reloaded.   [pyWHATauto]', target)
        
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
                    self.sendMsg("Your regex.conf file has been updated to the latest version.   [pyWHATauto]", target)
                else:
                    self.sendMsg("You are currently running the latest regex.conf file.   [pyWHATauto]", target)
            else:
                self.sendMsg("You need to update pyWA before you can use the new regex. You are using %s, but %s is required.   [pyWHATauto]"%(VERSION,"v"+str(minversion)), target)
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
                    G.RUNNING[network].joinChannel(channels=cmds[1:])
                    self.sendMsg('I am attempting to join %s on %s'%(cmds[1:],network), target)
                    out('INFO','Joining channels %s on %s'%(cmds[1:],network), site=self.name)
                else:
                    out('INFO','You tried to join a channel on a network (%s) that is not currently running' %network,self.name)
                    self.sendMsg('I cannot join %s on %s since it is not currently connected   [pyWHATauto]'%(cmds[1:],network), target)
            else:
                self.sendMsg('I do not recognise the network/alias. Try %sites for all available networks   [pyWHATauto]', target)
        else:
            self.sendMsg('Incorrect format for %join. The format should be %join <network/alias> #<channel> #<channel> ...  [pyWHATauto]', target)


    def fconnect(self, vars):
        target = vars[0]
        network = vars[1]
        
        out('CMD','connect %s'%network,site=self.name)
        if network is not None:
            for net in network:
                if net.lower() in self.fromalias.keys():
                    msg = establishBot(self.fromalias[net.lower()])
                    self.sendMsg(msg, target)
                else:
                    self.sendMsg('I do not recognise the network/alias %s' %net, target)
                    out('DEBUG','Unknown network/alias: %s' %net,site=self.name)
        else:
            self.sendMsg('Incorrect command structure for %connect, it should be %connect <network> <network2> ....   [pyWHATauto]', target)

    def fpart(self, vars):
        target= vars[0]
        cmds = vars[1]
        out('CMD','part %s' %cmds,site=self.name)
        if cmds != None and len(cmds) >1:
            if cmds[0].lower() in self.fromalias.keys():
                network = self.fromalias[cmds[0].lower()]
                if network in G.RUNNING:
                    G.RUNNING[network].partChannel(channels=cmds[1:])
                    self.sendMsg('I am attempting to part %s on %s'%(cmds[1:],network), target)
                    out('INFO','Parting channels %s on %s'%(cmds[1:],network), self.name)
                else:
                    out('INFO','You tried to part a channel on a network (%s) that is not currently running' %network,self.name)
                    self.sendMsg('I cannot part %s on %s since it is not currently connected   [pyWHATauto]'%(cmds[1:],network), target)
            else:
                self.sendMsg('I do not recognise the network/alias. Try %sites for all available networks   [pyWHATauto]', target)
        else:
            self.sendMsg('Incorrect format for %part. The format should be %part <network/alias> #<channel> #<channel> ...   [pyWHATauto]', target)
        
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
        
        self.sendMsg('%-*s %*s %*s %*s %*s' %(sitelen+1, 'Site', seenlen +2, 'Seen', downlen +2, 'Down', lastlen +2, 'Last Announce', idlen+2, 'DownloadID'), target)
        for site in sorted(G.RUNNING.iterkeys()):
            try:
                if G.RUNNING[site].lastannounce:
                    diff = datetime.now() - G.RUNNING[site].lastannounce
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
                self.sendMsg('%-*s %*s %*s %*s %*s' %(sitelen+1, site, seenlen+2, str(G.REPORTS[site]['seen']), downlen +2, str(G.REPORTS[site]['downloaded']), lastlen +2, string, idlen+2, G.RUNNING[site].lastannouncetext), target)
            except KeyError, e:
                out('ERROR','No reports yet for %s'%e,site=self.name)
        G.LOCK.release()
    
    def ftime(self, vars):
        target = vars[0]
        out('CMD','time',site=self.name)
        self.sendMsg(datetime.now().strftime("The date is %A %d/%m/%Y and the time is %H:%M:%S.   [pyWHATauto]"), target)
    
    def fcycle(self, vars):
        target = vars[0]
        if not vars[1]:
            out('CMD','cycle '+target,site=self.name)
            self.connection.part(target)
            self.connection.join(target)
        elif len(vars[1]) == 1:
            out('CMD','cycle '+ vars[1][0],site=self.name)
            self.sendMsg('Cycling channel %s   [pyWHATauto]'%vars[1][0], target)
            self.connection.part(vars[1][0])
            self.connection.join(vars[1][0])
        else:
            if vars[1][0].lower() in self.fromalias.keys():
                network = self.fromalias[vars[1][0].lower()]
                if network in G.RUNNING:
                    self.sendMsg('Cycling channel %s on %s   [pyWHATauto]' %(vars[1][1], network), target)
                    G.RUNNING[network].part(vars[1][1])
                    G.RUNNING[network].join(vars[1][1])
                else:
                    self.sendMsg('I cannot cycle %s on %s since it is not currently connected.   [pyWHATauto]'%(vars[1][1],network), target)
            else:
                self.sendMsg('Incorrect command structure. Syntax: \'%cycle\' rejoins the current channel, \'%cycle <channel>\' rejoins <channel>, \'%cycle <network/alias> <channel>\' rejoins <channel> on <network/alias>.    [pyWHATauto]', target)
                
        
    
    def fsites(self, vars):
        target = vars[0]
        out('CMD','sites',site=self.name)
        G.LOCK.acquire()
        self.sendMsg('Site Names: ', target)
        run = '[RUNNING] '
        for site in G.RUNNING.iterkeys():
            runo = run
            if self.toalias[site] == site:
                run += "%s, " %site
            else:
                run += "%s=%s, " %(site,self.toalias[site])
            if len(run) >= 350:
                self.sendMsg(runo[0:-2], target)
                run = run[len(runo):]
        self.sendMsg(run[0:-2], target)
        avail = '[AVAILABLE] '
        for site in G.NETWORKS.iterkeys():
            if not site in G.RUNNING:
                ava = avail
                if site == self.toalias[site]:
                    avail += "%s, " %site
                else:
                    avail += "%s=%s, " %(site, self.toalias[site])
            if len(avail) >= 350:
                self.sendMsg(ava[0:-2], target)
                avail = avail[len(ava):]
        avail = avail[0:-2] + '   [pyWHATauto]' 
        G.LOCK.release()          
        self.sendMsg(avail, target)
    
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
                    self.sendMsg('I cannot send the raw command \'%s\' on %s since it is not currently connected.   [pyWHATauto]'%(cmd,network), target)
            else:
                self.sendMsg('I do not know the network/alias %s.   [pyWHATauto]'%network, target)
        else:
            self.sendMsg('That is not a full command. Syntax: \'%cmd <network> <cmd>\' Example: \'%cmd whatcd privmsg johnnyfive :Are you alive?\' Will send a private message to johnnyfive on whatcd.',target)
        
    def fdownload(self, vars):
        target = vars[0]
        if vars[1] and len(vars[1]) >= 2:
            if vars[1][0].lower() in self.fromalias.keys():
                site = self.fromalias[vars[1][0].lower()]
                ids = vars[1][1:]
                for id in ids:
                    self.sendMsg('Downloading %s from %s.    [pyWHATauto]'%(id, site), target)
                    if G.TESTING:
                        download(id, site, network=self, target=target)
                    else:
                        kwargs = {'network':self,'target':target}
                        thread.start_new_thread(download, (id, site), kwargs)
            else:
                self.sendMsg('That site name does not seem valid. Type %sites to see a full list.   [pyWHATauto]', target)
        else:
            self.sendMsg('That is not a full command. Format: %download <site/alias> <torrentID> (<torrentID>) ....    [pyWHATauto]' , target)

    def fhelp(self, vars):
        target = vars[0]
        switch = vars[1]
        commands = vars[2]
        out('CMD','help %s'%(switch),site=self.name)
        if switch is None:
            self.sendMsg('Commands: %help <topic>, %current, %update, %filter, %quit, %connect, %disconnect, %time, %uptime, %stats, %statsreset, %version, %sites, %free/%drive, %join, %whois, %part, %download, %reload, %whoisall, %whoami, %update, %cycle, %ghost, %nick, %cmd   [pyWHATauto]', target)
        else:
            try:
                self.sendMsg(commands[switch[0]]['help'], target)
            except KeyError:
                self.sendMsg('That command does not exist. Try %help to see a list of commands.   [pyWHATauto]', target)
                
    def fversion(self, vars):
        target = vars[0]
        out('CMD','version',site=self.name)
        self.sendMsg('I am currently running pyWA version %s and regex.conf version %s by johnnyfi·ve and blub·ba.'%(VERSION, G.REGVERSION), target)
    
    def fghost(self, vars):
        target = vars[0]
        out('CMD','ghost',site=self.name)
        self.connection.privmsg('nickserv', "GHOST %s %s" %(self.creds['botnick'], self.creds['nickservpass']))
        self.connection.nick(self.creds['botnick'])
        self.connection.privmsg("nickserv","identify " + self.creds['nickservpass'])
        self.sendMsg('Ghost command sent.   [pyWHATauto]',target)
    
    def fuptime(self, vars):
        out('CMD','uptime',site=self.name)
        target = vars[0]
        diff = datetime.now() - G.STARTTIME
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
        self.sendMsg('I have been running for%s.'%string,target)
    
    def fstatsreset(self, vars):
        target = vars[0]
        out('CMD','statsreset',site=self.name)
        G.LOCK.acquire()
        for section in G.REPORTS.keys():
            G.REPORTS[section]['seen'] = 0
            G.REPORTS[section]['downloaded'] = 0
        G.LOCK.release()
        self.sendMsg('The stats reset command has been issued.   [pyWHATauto]', target)
        
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
            self.sendMsg('***Section: '+ filter, nick)
            for key in sorted(fils[filter].iterkeys(),cmp=compare):
                #print fils[filter][key]
                splits = fils[filter][key].split('\n')
                msg = '   %-*s  %-s' %(keylength+2, key + ':', splits.pop(0))
                if len(msg) > lenbnd:
                    self.sendMsg(msg[0:lenbnd - 20], nick)
                    msg = '   %-*s  %-s' %(keylength+2, '',msg[lenbnd - 20:])
                    while len(msg) >lenbnd:
                        self.sendMsg(msg[0:lenbnd - 20], nick)
                        msg = '   %-*s  %-s' %(keylength+2, '',msg[lenbnd - 20:])
                for split in splits:
                    oldmsg = msg
                    msg += ', ' + split
                    if len(msg) > lenbnd:
                        self.sendMsg(oldmsg, nick)
                        msg = '   %-*s  %-s' %(keylength+2, '',split)
                        if len(msg) > lenbnd:
                            self.sendMsg(msg[0:lenbnd - 20], nick)
                            msg = '   %-*s  %-s' %(keylength+2, '',msg[lenbnd - 20:])
                            while len(msg) >lenbnd:
                                self.sendMsg(msg[0:lenbnd - 20], nick)
                                msg = '   %-*s  %-s' %(keylength+2, '',msg[lenbnd - 20:])
                        
                self.sendMsg(msg, nick)
                

                    
if __name__ == "__main__":
    main()
