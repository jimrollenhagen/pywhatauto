#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
from __future__ import with_statement
from __future__ import division

import re, os, hashlib

def main():
    dir = '/home/blubba/.config/deluge/state'
    print('%-50s %-3s %10.2s  %-5s' %('Infohash','M','MBs','Name'))
    for file in os.listdir(dir):
        root, ext = os.path.splitext(file)
        if ext and ext == '.torrent':
            x = torrentparser(filename=os.path.join(dir,file))
            if root == x.infohash():
                m = 'Y'
            else:
                m = 'N'
            print('%-50s %-3s %10.2f  %-5s' %(root,m,x.mbsize(),x.name()))

class torrentparser(object):
    '''
    Universal torrent writing and parsing class
    '''
    def __init__(self, debug = False, filename=False, content=False):
        '''Takes a string with the path to the torrent file in filename,
        or the content of a torrent file in content (as a string).
        Runs the parses on it.
        Returns a string if the file could not be opened/read,
        raises SyntaxError on parsing errors.'''
        self.torrentfile = None
        self.debug = debug
        self.dictionary = None
        if filename or content:
            return self.parse(filename=filename, content=content)

    def parse(self, filename=False, content=False):

        if filename:
            try:
                with open(filename, 'rb') as f:
                    self.torrentfile = f.read()
            except IOError:
                print('Cannot open file ' + filename)
                raise
        elif content:
            self.torrentfile = content
        else:
            return 'No torrent data given'
        self.decode()

    def decode(self):
        '''Decodes the raw bencoded file into self.dictionary. Raises SyntaxErrors on errors.'''
        reg = re.compile('^(\d+)?(?:i(\d+)e)?(l?)(d)?(e)?', re.I + re.U) #strings, ints, lists, dicts
        t = self.torrentfile
        depth = [None]
        l = []
        i= 0

        while i < len(t):
            m = reg.match(t[i:])
            if self.debug: print 'left: ' + repr(l)
            ty = type(depth[-1])
            if m:
                if m.group(1): #String
                    string = t[i + len(m.group(1)) + 1 : i + int(m.group(1)) + len(m.group(1)) + 1]
                    if ty == type(list()):
                        if self.debug: print('Append %s to %s' %(repr(string),repr(depth[-1])))
                        depth[-1].append(string)
                    elif ty == type(dict()):
                        if l[-1]:
                            if l[-1] == 'pieces' and self.debug:
                                string = 'Here are all the pieces'
                            if self.debug: print('Map %s -> String: %s' %(l[-1],repr(string)))
                            depth[-1].update({l[-1] : string})
                            l[-1] = None
                        else:
                            if self.debug: print('Add left: String: %s' %(repr(string)))
                            l[-1] = string
                    else:
                        raise SyntaxError('Lonely String found: %s' %string)
                    i += int(m.group(1)) + len(m.group(1)) + 1
                elif m.group(2): #Integer
                    integer = int(m.group(2))
                    #print('Integer: ' + str(integer))
                    if ty == type(list()):
                        depth[-1].append(integer)
                    elif ty == type(dict()):
                        if l[-1]:
                            if self.debug: print('Map %s -> Integer: %s' %(l[-1],repr(integer)))
                            depth[-1].update({l[-1] : integer})
                            l[-1] = None
                        else:
                            if self.debug: print('Add left: Integer: %s' %(repr(integer)))
                            l[-1] = str(integer)
                    else:
                        raise SyntaxError('Lonely Integer found: %s' %str(integer))
                    i += len(str(m.group(2))) + 2
                elif m.group(3): #List
                    if self.debug: print('List found')
                    depth.append(list())
                    i+=1
                elif m.group(4):
                    if self.debug: print('Dictionary found')
                    depth.append(dict())
                    l.append(None)
                    i+=1
                elif m.group(5):
                    if type(depth[-2]) == type(dict()):
                        if ty == type(dict()):
                            if self.debug: print('Dictionary ended: Map %s -> %s' %(l[-2],repr(depth[-1])))
                            depth[-2].update({l[-2]: depth[-1]})
                            l[-2] = None
                            del l[-1]
                        else:
                            if self.debug: print('List ended: Map %s -> %s' %(l[-1],repr(depth[-1])))
                            depth[-2].update({l[-1]: depth[-1]})
                            l[-1] = None
                    elif type(depth[-2]) == type(list()):
                        if self.debug: print('List ended: Append %s to %s' %(repr(depth[-1]),repr(depth[-2])))
                        depth[-2].append(depth[-1])
                        if ty == type(dict()):
                            del l[-1]
                    else:
                        if self.debug: print repr(depth)
                        self.dictionary = depth[-1]
                    del depth[-1]
                    i+=1
                else:
                    if i+1 == len(t):
                        i+=1
                    else:
                        raise SyntaxError('Torrent files is not formated, i: %d/%d remaining content: %s' %(i,len(t),repr(t[i:])))
            else:
                raise SyntaxError('Torrent files is not formated, i: %d/%d remaining content: %s' %(i,len(t),repr(t[i:])))

    def encode(self, dictionary=None):
        '''Returns the bencoded version of the dictionary'''
        if not dictionary:
            dictionary = self.dictionary
        ben = 'd'
        for key in sorted(dictionary.iterkeys(),key=str.lower):
            t = type(dictionary[key])
            ben += "%d:%s"%(len(key),key)
            if t == type(dict()):
                ben += self.encode(dictionary[key])
            elif t == type(str()):
                ben += '%d:%s' %(len(dictionary[key]), dictionary[key])
            elif t == type(int()):
                ben += 'i%de' %dictionary[key]
            elif t == type(list()):
                ben += self.encodelist(dictionary[key])
            else:
                raise SyntaxError('Mallformated dictionary as it seems.')
        return ben + 'e'

    def encodelist(self, list):
        '''Returns the bencoded version of the list'''
        ben = 'l'
        for key in list:
            t = type(key)
            if t == type(dict()):
                ben += self.encode(key)
            elif t == type(str()):
                ben += '%d:%s' %(len(key), key)
            elif t == type(int()):
                ben += 'i%de' %key
            elif t == type(list()):
                ben += self.encodelist(key)
            else:
                raise SyntaxError('Mallformated dictionary as it seems.')
        return ben + 'e'

    def pretty(self):
        '''Prints a pretty version of the dictionary'''
        import pprint
        pprint.pprint(self.dictionary)

    def files(self):
        '''Returns a list of all files.'''
        f = []
        if 'files' in self.dictionary['info']:
            for ff in self.dictionary['info']['files']:
                path = self.dictionary['info']['name']
                for fff in ff['path']:
                    path = os.path.join(path,fff)
                f.append(path)
                if self.debug: print(path)
        elif 'name' in self.dictionary['info']:
            f.append(self.dictionary['info']['name'])
            if self.debug: print f[0]
        return(f)

    def infohash(self):
        '''Returns the sha1hash of the infodb'''
        return hashlib.sha1(self.encode(self.dictionary['info'])).hexdigest()

    def mbsize(self):
        '''Returns the size in MB'''
        return self.rawsize() / (1024*1024)

    def gbsize(self):
        '''Returns the size in GB'''
        return self.rawsize() / (1024*1024*1024)

    def name(self):
        '''Returns the name of the torrent, as specified in the info'''
        if 'name' in self.dictionary['info']:
            return self.dictionary['info']['name']

    def rawsize(self):
        '''Returns the size in bytes'''
        size = 0
        if 'files' in self.dictionary['info']:
            for ff in self.dictionary['info']['files']:
                size += ff['length']
        elif 'name' in self.dictionary['info']:
            size += self.dictionary['info']['length']
        return size

if __name__ == "__main__":
    main()

