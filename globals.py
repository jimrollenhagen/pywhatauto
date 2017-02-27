from datetime import datetime
import threading, sys, os, Queue#, thread

#This is an internal flag I use to test announcements.
TESTING = False
#Should we log everything?
LOG = False

#What version of REGEX.conf are we using? Loaded from the file itself on startup
REGVERSION = 0


NETWORKS = dict()
#the dictionary of networks and their information that have a section in credentials.conf or custom.conf
RUNNING = dict()
#The dictionary of running bots
TOSTART = dict()
#Dictionary of initial 'sites' keys in setup and custom.conf
TOALIAS = dict()
#Take a sitename and go to the alias
ALIASLENGTH = 0
#Length of the longest alias
FROMALIAS = dict()
#take an alias and go to the sitename
REPORTS = dict()
#the reports of seen/downloaded for each site
FILTERS_CHANGED= dict()
#A dictionary of filters that have been manually changed and their states
FILTERS= dict()
#A dictionary of filters and their original states
STARTTIME = datetime.now()
#The time at which the bot was started
LOCK = threading.RLock()
#the threading LOCK. Come on people.
EXIT = False
#Do we want to exit?
sys.tracebacklimit = 20
#How far should I allow traceback?
OWNER = ['34038@johnnyfive','3808@johnnyfive','191067@blubba','1868@blubba']
#I own this shit, yo
CD = ['inline; filename=','inline; Filename=','attachment; Filename=','attachment; filename=', 'attachement; filename=']
#ContentDispositions
SCRIPTDIR=os.path.realpath(os.path.dirname(sys.argv[0]))
#where was this script loaded from?

Q = Queue.Queue()
#The Queue object used to send the DB new announcements
