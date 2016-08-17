'''
Created on Aug 13, 2010

@author: JohnnyFive
'''

import sqlite3, os, sys#, Queue
from threading import Thread

def main():
    sq = sqlDB(os.path.realpath(os.path.dirname(sys.argv[0])))
    print sq

class sqlDB( Thread ):
    
    def __init__(self, loadloc, queue):
        Thread.__init__(self)
        self.q = queue
        self.loadloc = loadloc
        self.verified = list()
    
    def run(self):
        self.conn = sqlite3.connect(os.path.join(self.loadloc, 'example.db'))
#        self.conn = sqlite3.connect(":memory:")
        self.c = self.conn.cursor()
        while True:
            info = self.q.get()
            self.addAnnounce(info[0],info[1],info[2])
            
    def verifyTable(self, site):
        #test to see if the table exists already
        self.c.execute("SELECT name FROM sqlite_master WHERE name=?", (site,))
        #if it doesn't, create it
        if self.c.fetchone() is None:
            self.c.execute("CREATE TABLE %s (token numeric, id integer PRIMARY KEY, announcement text, downloadid integer)" %site)
    
        self.verified.append(site)
    
    def addAnnounce(self, site, announcement, downloadid):
        #verify that we've already created a table for this site
        if site not in self.verified:
            self.verifyTable(site)       
             
        var = (site,)
        #test to see if any values exist in the table, and if anything exists grab the current token so we know where to start adding/replacing new announcements.
        self.c.execute("SELECT * from %s WHERE token='1'"%site)
        #if nothing exists, start adding things
        x = self.c.fetchone()
        if x is None:
            var = (announcement, downloadid)
            self.c.execute("insert into %s values ('1', '1', ?, ?)"%site,var)
        else:
            #REPLACE the line with the token and remove the token (set to 0)
            self.c.execute('UPDATE %s SET token=0 WHERE token=1'%site)
            
            #INSERT OR REPLACE the incoming announcement into the table
            currID = x[1]
            #Revolve back to 1 if we're at 100 already
            if currID == 100:
                currID = 1
            else:
                currID += 1
                
            #Create a new line or replace the current one with the new announce
            var = (currID, unicode(announcement,('utf-8'),errors='ignore'), downloadid)
            self.c.execute("INSERT OR REPLACE INTO %s VALUES ('1', ?, ?, ?)"%site,var)
            self.conn.commit()
        
if __name__ == '__main__':
    main()