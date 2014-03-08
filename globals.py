#! /usr/bin/env python

import datetime
import os
import Queue
import sys
import threading


# How far should I allow traceback?
sys.tracebacklimit = 20

# internal flag for debugging announces
TESTING = False
# Should we log everything?
LOG = False

# What version of REGEX.conf are we using?
# this is loaded from the file itself on startup
REGVERSION = 0

# the dictionary of networks and their information that have a section
# in credentials.conf or custom.conf
NETWORKS = {}
# The dictionary of running bots
RUNNING = {}

# Dictionary of initial 'sites' keys in setup and custom.conf
TOSTART = {}
# Take a sitename and go to the alias
TOALIAS = {}
# Length of the longest alias
ALIASLENGTH = 0
# take an alias and go to the sitename
FROMALIAS = {}

# the reports of seen/downloaded for each site
REPORTS = {}

# A dictionary of filters that have been manually changed and their states
FILTERS_CHANGED = {}
# A dictionary of filters and their original states
FILTERS = {}

# The time at which the bot was started
STARTTIME = datetime.datetime.now()

# the threading LOCK. Come on people.
LOCK = threading.RLock()
# exit flag for shutdown
EXIT = False

# Possible Content-Disposition headers
CD = [
    'inline; filename=',
    'inline; Filename=',
    'attachment; Filename=',
    'attachment; filename=',
    'attachement; filename=',
]

# where was this script loaded from?
SCRIPTDIR = os.path.realpath(os.path.dirname(sys.argv[0]))

# The Queue object used to send the DB new announcements
Q = Queue.Queue()

# all possible IRC events
ALL_EVENTS = [
    'pubnotice',
    'quit',
    'kick',
    'mode',
    'whoreply',
    'endofwho',
    'statskline',
    'part',
    'join',
    'topicinfo',
    'statsqline',
    'statsnline',
    'statsiline',
    'statscommands',
    'statscline',
    'tracereconnect',
    'statslinkinfo',
    'notregistered',
    'created',
    'endofnames',
    'statsuptime',
    'notopic',
    'statsyline',
    'endofstats',
    'uniqopprivsneeded',
    'cannotsendtochan',
    'adminloc2',
    'adminemail',
    'luserunknown',
    'luserop',
    'luserconns',
    'luserclient',
    'adminme',
    'adminloc1',
    'luserchannels',
    'toomanytargets',
    'listend',
    'toomanychannels',
    'statsoline',
    'invitelist',
    'endofinvitelist',
    'nosuchchannel',
    'inviting',
    'summoning',
    'exceptlist',
    'endofexceptlist',
    'noorigin',
    'nosuchserver',
    'nochanmodes',
    'endofbanlist',
    'yourebannedcreep',
    'passwdmismatch',
    'keyset',
    'needmoreparams',
    'nopermforhost',
    'alreadyregistered',
    'tryagain',
    'endoftrace',
    'tracelog',
    'notonchannel',
    'noadmininfo',
    'umodeis',
    'endoflinks',
    'nooperhost',
    'fileerror',
    'wildtoplevel',
    'usersdisabled',
    'norecipient',
    'notexttosend',
    'notoplevel',
    'info',
    'infostart',
    'whoisoperator',
    'whoisidle',
    'whoischanop',
    'whowasuser',
    'users',
    'usersstart',
    'time',
    'nousers',
    'endofusers',
    'servlist',
    'servlistend',
    'youwillbebanned',
    'badchannelkey',
    'serviceinfo',
    'endofservices',
    'service',
    'youreoper',
    'usernotinchannel',
    'list',
    'none',
    'liststart',
    'noservicehost',
    'channelmodeis',
    'away',
    'banlist',
    'links',
    'channelcreate',
    'closing',
    'closeend',
    'usersdontmatch',
    'killdone',
    'traceconnecting',
    'tracelink',
    'traceunknown',
    'tracehandshake',
    'traceuser',
    'traceoperator',
    'traceservice',
    'traceserver',
    'traceclass',
    'tracenewtype',
    'userhost',
    'ison',
    'unaway',
    'nowaway',
    'nologin',
    'yourhost',
    'rehashing',
    'statslline',
    'summondisabled',
    'umodeunknownflag',
    'bannedfromchan',
    'useronchannel',
    'restricted',
    'cantkillserver',
    'chanoprivsneeded',
    'noprivileges',
    'badchanmask',
    'statshline',
    'unknownmode',
    'inviteonlychan',
    'channelisfull',
    'version',
    'unknowncommand',
    'nickcollision',
    'myportis',
    'banlistfull',
    'erroneusnickname',
    'unavailresource',
    'nonicknamegiven'
]
