import os
from datetime import datetime
import json
import builtins as __builtin__
import re
from collections import deque
import collections
import traceback
import sys
import asyncio
import inspect

class readLog:
    def __init__(self, cfg):
        self.cfg = cfg
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.maxDataRows = 100
        #all data rows are stored in here, limited to prevent memory leaks
        self.dataRows=deque(maxlen=self.maxDataRows)
        #scan most recent log. Until enough data is collected
        #logs = self.getLogs()
        self.Events = []
        self.lastLogCheck = None
        self.current_log = None
        # tempdataRows = deque(maxlen=self.maxDataRows)
        # for log in reversed(logs):
            # print("Pre-scanning: "+log)
            # self.scanfile(log)
            # if(len(tempdataRows)+len(self.dataRows) <= self.maxDataRows):
                # tempdataRows.extendleft(reversed(self.dataRows))
                # self.dataRows = deque(maxlen=self.maxDataRows)
            # else:
                # break
            # if(len(tempdataRows)>=self.maxDataRows):
                # break
        # self.dataRows = tempdataRows
        
        #Start Watchlog
        asyncio.ensure_future(self.watch_log())

    #get the log files from folder and sort them by oldest first
    def getLogs(self):
        if(self.lastLogCheck == None or (datetime.now() - self.lastLogCheck).total_seconds() > 60):
            self.lastLogCheck = datetime.now()
            
            if(os.path.exists(self.cfg['logs_path'])):
                files = []
                for file in os.listdir(self.cfg['logs_path']):
                    if (file.endswith(".log") or file.endswith(".rpt")):
                        files.append(file)
                return sorted(files)
        return []

    def splitTimestamp(self, pline):
        splitat = pline.find("[")
        r = pline[splitat:]  #remove timestamp
        timestamp = pline[:splitat]
        return [timestamp[:-1],r]
        
            
    def processLogLine(self, line):
        if(" Server load: FPS " in line):
            data = line.split("Server load: ")
            self.dataRows.append(data[1])
        return None
        
    #this function will continusly scan a log for data entries. They are stored in self.dataRows
    def scanfile(self, name):
        with open(self.cfg['logs_path']+name) as fp: 
            data = None
            try:
                line = fp.readline()
            except:
                line = None
            while line:
                self.processLogLine(line)
                self.dataRows.append(data)
                try:
                    line = fp.readline()
                except:
                    line = None
                    
    async def watch_log(self):

        while(True): #Wait till a log file exsists
            logs = self.getLogs()
            if(len(logs) > 0):
                self.current_log = logs[-1]
                print("current log: "+self.current_log)
                file = open(self.cfg["logs_path"]+self.current_log, "r")
                file.seek(0, 2) #jump to the end of the file
                try:
                    while (True):
                        #where = file.tell()
                        try:
                            line = file.readline()
                        except:
                            line = None
                        if not line:
                            await asyncio.sleep(1)
                            #file.seek(where)
                            new_log = self.getLogs()
                            if(len(new_log) > 0 and self.current_log != new_log[-1]):
                                old_log = self.current_log
                                self.current_log = new_log[-1] #update to new recent log
                                #self.scanfile(self.current_log) #Log most likely empty, but a quick scan cant hurt.
                                file = open(self.cfg["logs_path"]+self.current_log, "r")
                                print("current log: "+self.current_log)
                                #self.on_newLog(old_log, self.current_log)
                        else:
                            self.processLogLine(line)
                except Exception as e:
                    print(e)
                    traceback.print_exc()
            else:
                await asyncio.sleep(10*60)
###################################################################################################
#####                                  Event Handeler                                          ####
###################################################################################################   
    def add_Event(self, name: str, func):
        events = ["on_monitords"]
        if(name in events):
            self.Events.append([name,func])
        else:
            raise Exception("Failed to add unkown event: "+name)

            
    def check_Event(self, parent, *args):
        for event in self.Events:
            func = event[1]
            if(inspect.iscoroutinefunction(func)): #is async
                if(event[0]==parent):
                    if(len(args)>0):
                        asyncio.ensure_future(func(args))
                    else:
                        asyncio.ensure_future(func())
            else:
                if(event[0]==parent):
                    if(len(args)>0):
                        func(args)
                    else:
                        func()
###################################################################################################
#####                                  Event functions                                         ####
################################################################################################### 
    def on_monitords(self, data):
        self.check_Event("on_monitords", data)    

   
###################################################################################################
#####                                  Graph Generation                                        ####
###################################################################################################   

    def featchValues(self, data,field):
        list = []
        for item in data:
            if(field in item):
                list.append(item[field])
        return list
   