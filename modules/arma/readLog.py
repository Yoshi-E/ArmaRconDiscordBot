#pip install matplotlib

import matplotlib.pyplot as plt
import ast
import os
from datetime import datetime
import json
import logging
import re
from collections import deque
import collections
import traceback
import sys
import itertools
import asyncio
import inspect

class Event_Handler(object):
    def __init__(self, events):
        self.events = events
        self.events.append("other")
        self.Events = []
        
    def add_Event(self, name: str, func):
        if(name in self.events):
            self.Events.append([name,func])
        else:
            raise Exception("Failed to add unknown event: "+name)

    def check_Event(self, parent, *args):
        for event in self.Events:
            func = event[1]
            if(inspect.iscoroutinefunction(func)): #is async
                if(event[0]==parent):
                    if(len(args)>0):
                        asyncio.ensure_future(func(*args))
                    else:
                        asyncio.ensure_future(func())
            else:
                if(event[0]==parent):
                    if(len(args)>0):
                        func(*args)
                    else:
                        func()

#Timestamp format:
#https://community.bistudio.com/wiki/server.cfg
#timeStampFormat
class readLog:
    def __init__(self, log_path):
        self.maxDataRows = 5000
        self.skip_server_init = True #Skips the server loading stuff
        
        
        #Internal vars:
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.log_path = log_path
        #all data rows are stored in here, limited to prevent memory leaks
        self.dataRows=deque(maxlen=self.maxDataRows)
        self.skip = False
        self.define_line_types()
        
        #self.EH.add_Event("other", self.test)
        
        #self.pre_scan()
        
        #Start Watchlog
        asyncio.ensure_future(self.watch_log())
    
    def test(self, *args):
        print(args)
        
    def pre_scan(self):
        logs = self.getLogs()
        tempdataRows = deque(maxlen=self.maxDataRows)
        if(len(logs)==0):
            print("[Warning]: No logs found in path '{}'".format(self.log_path))
        
        #scan most recent log. Until enough data is collected
        for log in reversed(logs):
            print("Pre-scanning: "+log)
            self.scanfile(log)
            if(len(tempdataRows)+len(self.dataRows) <= self.maxDataRows):
                tempdataRows.extendleft(reversed(self.dataRows))
                self.dataRows = deque(maxlen=self.maxDataRows)
            else:
                #TODO only merge some parts (to fill complelty)
                break
            if(len(tempdataRows)>=self.maxDataRows):
                break
        self.dataRows = tempdataRows
        
        
    def define_line_types(self):
        # Format: [name, regex]
        self.events = [
        #Clutter
            ["clutter", "^(NetServer: trying to send a too large non-guaranteed message \(len=([0-9]*)\/([0-9]*)\) to ([0-9]*))"], #NetServer: trying to send a too large non-guaranteed message (len=1348/1364) to 1104393217
            ["clutter", "^(Message not sent - error ([0-9]*), message ID = ([a-z]*), to ([0-9]*) \((.*)\))"], #Message not sent - error 0, message ID = ffffffff, to 1104393217 (Sig)
            ["clutter", "^(Server: Object ([0-9]*:[0-9]*) not found \((.*)\))"], #Server: Object 2:15953 not found (message Type_120)
            ["clutter", "^(Server: Object info (.*) not found\.)"], #Server: Object info 29:1758 not found.
            ["clutter", "^(Client: Object ([0-9]*:[0-9]*) \((.*)\) not found\.)"], #Client: Object 10:267 (type Type_92) not found.
            ["clutter", "^(Client: Remote object ([0-9]*:[0-9]*) not found)"], #Client: Remote object 14:1 not found
            ["clutter", "^(Can't change owner from ([0-9]*) to ([0-9]*))"], #Can't change owner from 0 to 1210751637
            ["clutter", "^((.*)\[(.*)\]:(Some of magazines weren't stored in soldier Vest or Uniform\?))"], #soldier[I_Soldier_AT_F]:Some of magazines weren't stored in soldier Vest or Uniform?
            ["clutter", "^(Warning: Convex component representing (.*) not found)"], #Warning: Convex component representing Track_L not found
            ["clutter", "^(Server: Network message (.*) is pending)"], #Server: Network message 6fefa8 is pending
            ["clutter", '^(Deinitialized shape \[Class: "(.*)"; Shape: "(.*)";\])'], #Deinitialized shape [Class: "Underwear_F"; Shape: "a3\characters_f\common\basicbody.p3d";]
            ["clutter", "^(NetServer: cannot find channel)"], #NetServer: cannot find channel
            ["clutter", "^(Duplicate weapon )"], #Duplicate weapon 
            ["clutter", "^(Unsupported language English in stringtable)"], #Unsupported language English in stringtable
        #No Timestamp
            ["clutter_no_TS", "^(Overflow)"], #Overflow
            ["clutter_no_TS", "^(Road not found)"], #Road not found
            ["clutter_no_TS", "^(Duplicate HitPoint name)"], #Duplicate HitPoint name
            ["clutter_no_TS", "^(Error: Object\(([0-9]* : [0-9]*)\) not found)"], #Error: Object(23 : 706) not found
            ["clutter_no_TS", "^(a3.*\.p3d)"], #a3\weapons_f\ammo\smokegrenade_white_throw.p3d
            ["clutter_no_TS", "^(.*\.p3d: No geometry and no visual shape)"], #a3\weapons_f\lasertgt.p3d: No geometry and no visual shape
            ["clutter_no_TS", "^((.*): (.*) - unknown animation source (.*))"], #B_Truck_01_mover_F: mirror_l_hide - unknown animation source mirror_l_hide
            ["clutter_no_TS", "^(Strange convex (.*) in (.*.p3d):(.*))"], #Strange convex component141 in a3\rocks_f\sharp\sharprock_wallv.p3d:geometryFire
        #server
            ["Server sessionID",        "^(sessionID: (.*))"], #sessionID: 20e34f8f50d2d2fad69c12452e853f7c6bc83ad5
            ["Server online",           "^(Host identity created\.)"], #Host identity created.
            ["Server port",             "^(Game Port: ([0-9]*), Steam Query Port: ([0-9]*))"], #Game Port: 2302, Steam Query Port: 2303
            ["Server waiting for game", "^(Waiting for next game\.)"], #Waiting for next game.
        #mission
            ["Mission roles assigned",  "^(Roles assigned\.)"], #Roles assigned.
            ["Mission readname",        "^(Mission (.*) read from bank.)"], #Mission BECTI BE 0.97 - Zerty 1.3.5.2 read from bank.
            ["Mission reading",         "^(Reading mission \.\.\.)"], #Reading mission ...
            ["Mission read",            "^(Mission read\.)"], #Mission read.
            ["Mission starting",        "^(Starting mission:)"], #Starting mission:
            ["Mission file",            "^( Mission file: (.*) \((.*)\))"], # Mission file: becti_current (__cur_mp)
            ["Mission world",           "^( Mission world: (.*))"], # Mission world: Altis
            ["Mission directory",       "^( Mission directory: (.*))"], # Mission directory: mpmissions\__cur_mp.Altis\
            ["Mission id",              "^( Mission id: (.*))"], # Mission id: a001eb0dc827137d84595a7706f2cdd937f95fa3
            ["Mission finished",        "^(Game finished\.)"], #Game finished.
            ["Mission started",         "^(Game started\.)"], #Game started.
        #player
            ["Player modified data file",   "^((.*) uses modified data file)"], #KKD | dawkar3152 uses modified data file
            ["Player disconnected",         "^(Player (.*) disconnected.)"], #Player ARMATA disconnected.
            ["Player connecting",           "^(Player (.*) connecting.)"], #Player Celis connecting.
            ["Player connected",            "^(Player (.*) connected \(id=([0-9]*)\)\.)"], #Player Fritz connected (id=76561198017145527).
            ["Player xml parse error",      "^(Warning: Could not parse squad\.xml for Player\[(.*)\], Squad\[(.*)\])"], #Warning: Could not parse squad.xml for Player[Hptm.v.Kriegern], Squad[https://armasquads.de/user/squads/xml/gvy2AxinZc2O1N2oU0OR6PWblHFr3Tte/squad.xml]
        #BattlEye
            ["BattlEye initialized",            "^(BattlEye Server: Initialized \((.*)\))"], #BattlEye Server: Initialized (v1.217)
            ["BattlEye registering player",     "^(BEServer: registering a new player #([0-9]*))"], #BEServer: registering a new player #989446346
            ["BattlEye chat message",           "^(BattlEye Server: \((.*)\) (.*): (.*))"], #BattlEye Server: (Side) Matt Fox: m
            ["BattlEye player connected",       "^(BattlEye Server: Player #([0-9]*) (.*) \(([0-9]*\.[0-9]*\.[0-9]*\.[0-9]*):([0-9]*)\) connected)"], #BattlEye Server: Player #36 Master (88.196.232.197:2304) connected
            ["BattlEye player disconnected",    "^(BattlEye Server: Player #([0-9]*) (.*) disconnected)"], #BattlEye Server: Player #4 Ztppp disconnected
            ["BattlEye player guid",            "^(BattlEye Server: Player #(.*) (.*) - GUID: (.*))"], #BattlEye Server: Player #38 Fritz - GUID: 54333f4dbe1d3c73b227c8a3ed7b663c
            ["BattlEye player guid verified",   "^(BattlEye Server: Verified GUID \((.*)\) of player #([0-9]*) (.*))"], #BattlEye Server: Verified GUID (2854515fa6c84ca6657cd55fa8c145cb) of player #8 Sgt. Gonzalez
            ["BattlEye player kicked",          "^(Player (.*) kicked off by BattlEye: (.*))"],  #Player MM Leon kicked off by BattlEye: Admin Kick (AFK too long (user_check by Ztppp))
            ["BattlEye rcon admin login",       "^(BattlEye Server: RCon admin #([0-9]*) \((.*):(.*)\) logged in)"],  #BattlEye Server: RCon admin #0 (90.92.59.82:59806) logged in
            ["BattlEye chat direct message",    "^(BattlEye Server: RCon admin #([0-9]*): \(To (.*)\) (.*))"]  #BattlEye Server: RCon admin #1: (To MM Leon) 
        ]
        #TODO: Bans?
        self.EH = Event_Handler([row[0] for row in self.events])
    # goes through an array of regex until it finds a match
    def check_log_events(self, line, events):
        for event in events:
            m = re.match(event[1], line)
            if m:
                return event[0], m
        return None, None
    
    def processLogLine(self, line, save=False):
        timestamp, msg = self.splitTimestamp(line)
            
        event, m = self.check_log_events(msg, self.events)
        if(m):
            self.EH.check_Event(event, timestamp, *m.groups())
            if(self.skip_server_init and event=="Server sessionID"):    
                self.skip = True
            elif(event=="Server online"):
                self.skip = False
            if("clutter" not in event and save):
                self.dataRows.append((timestamp, msg, m))
        else:
            if(self.skip==False):
                self.EH.check_Event("other", timestamp, msg)
                if(save):
                    self.dataRows.append((timestamp, msg))
                
                
    #get the log files from folder and sort them by oldest first
    def getLogs(self):
        if(os.path.exists(self.log_path)):
            files = []
            for file in os.listdir(self.log_path):
                if (file.endswith(".log") or file.endswith(".rpt")):
                    files.append(file)
            return sorted(files)
        else:
            return []

    
    #returns timestamp and msg
    def splitTimestamp(self, log_line):
        #Default timeStampFormat
        m = re.match(r"^\s?([0-9]{1,2}:[0-9]{2}:[0-9]{2})\s(.*)", log_line)
        if(m):
            return m.group(1), m.group(2)
        else:
            return None, log_line


    #this function will continusly scan a log for data entries. They are stored in self.dataRows
    def scanfile(self, name):
        with open(self.log_path+name) as fp: 
            try:
                line = fp.readline()
            except:
                line = None
            while line:
                self.processLogLine(line)
                try:
                    line = fp.readline()
                except:
                    line = None
                    
    async def watch_log(self):
        await asyncio.sleep(60)
        try:
            while(True): #Wait till a log file exsists
                logs = self.getLogs()
                if(len(logs) > 0):
                    current_log = logs[-1]
                    print("current log: "+current_log)
                    file = open(self.log_path+current_log, "r")
                    file.seek(0, 2) #jump to the end of the file
                    try:
                        while (True):
                            #where = file.tell()
                            try:
                                line = file.readline()
                            except:
                                line = None
                            if not line:
                                await asyncio.sleep(10)
                                #file.seek(where)
                                if(current_log != self.getLogs()[-1]):
                                    old_log = current_log
                                    current_log = self.getLogs()[-1] #update to new recent log
                                    #self.scanfile(current_log) #Log most likely empty, but a quick scan cant hurt.
                                    file = open(self.log_path+current_log, "r")
                                    print("current log: "+current_log)
                                    self.on_newLog(old_log, current_log)
                            else:
                                self.processLogLine(line)
                    
                    except (KeyboardInterrupt, asyncio.CancelledError):
                        print("[asyncio] exiting", watch_log)
                    except Exception as e:
                        print(e)
                        traceback.print_exc()
                else:
                    await asyncio.sleep(10*60)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("[asyncio] exiting", watch_log)
    


#RL = readLog("D:/Dokumente/_Git/_ArmaGit/ArmaRconDiscordBot/modules/rcon_jmw/")