import os
import re
from collections import deque
import traceback
import asyncio

from modules.core.utils import Event_Handler
from modules.core.Log import log

#timeStampFormat:
#https://community.bistudio.com/wiki/server.cfg

class readLog:
    def __init__(self, log_path, maxMissions=20):
        self.maxMissions = maxMissions #max amount of Missions stored in the buffer 
                              #also contains datablock between the mission 
                              #(e.g 2 scenarios played --> 5 Missions blocks)        
        
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.log_path = log_path
        self.currentLinePos = 0
        self.current_log = None
        self.multiEventLock = None
        self.multiEventLockData = []
        if(len(self.getLogs()) == 0):
            log.info("[WARNNING] No log files found in '{}'".format(self.log_path))
            
        #all data rows are stored in here, limited to prevent memory leaks
        self.Missions=deque(maxlen=self.maxMissions)
        self.Missions.append({"dict": {}, "data": []})
        
        self.define_line_types()
        #self.EH.add_Event("Mission script error", self.test)
        #self.pre_scan()
        #self.test_missions()
        
        #Start Watchlog
        #asyncio.ensure_future(self.watch_log())
    
    def test(self, *args):
        log.info("---- {}".format(args))

###################################################################################################
#####                                       Events                                             ####
###################################################################################################     
    
    #configure the event listern regex
    def define_line_types(self, additonal_defintions=None):
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
            ["Server load", "^(Server load: FPS (?P<FPS>[0-9]*), memory used: (?P<memory>[0-9]*) (?P<memory_unit>.*?), out: (?P<out>[0-9]*) (?P<out_unit>.*?), in: (?P<in>[0-9]*) (?P<in_unit>.*?),.*Players: (?P<players>[0-9]*) .*)"], #Server load: FPS 9, memory used: 2430 MB, out: 993 Kbps, in: 290 Kbps, NG:0, G:6358, BE-NG:0, BE-G:0, Players: 17 (L:0, R:0, B:0, G:17, D:0)
        #mission
            ["Mission readname",        "^(Mission (.*) read from bank.)"], #Mission BECTI BE 0.97 - Zerty 1.3.5.2 read from bank.
            ["Mission roles assigned",  "^(Roles assigned\.)"], #Roles assigned.
            ["Mission reading",         "^(Reading mission \.\.\.)"], #Reading mission ...
            ["Mission starting",        "^(Starting mission:)"], #Starting mission:
            ["Mission restarted",        "^(Game restarted)"], #Game restarted:
            ["Mission file",            "^\s(Mission file: (.*) \((.*)\))"], # Mission file: becti_current (__cur_mp)
            ["Mission world",           "^\s(Mission world: (.*))"], # Mission world: Altis
            ["Mission directory",       "^\s(Mission directory: (.*))"], # Mission directory: mpmissions\__cur_mp.Altis\
            ["Mission read",            "^(Mission read\.)"], #Mission read.
            ["Mission id",              "^\s(Mission id: (.*))"], # Mission id: a001eb0dc827137d84595a7706f2cdd937f95fa3
            ["Mission started",         "^(Game started\.)"], #Game started.
            ["Mission finished",        "^(Game finished\.)"], #Game finished.
            ["Mission script error",         "^(Error in expression .*)"], #Error in expression <= false };  #File mpmissions\__cur_mp.Altis\Server\Functions\Server_SpawnTownResistance.sqf..., line 151
            #, "^(File (?P<path>.*)..., line (?P<line>[0-9]*))"
            #TODO: Multi line Events can cause other events to be skipped. 
        #player
            ["Player modified data file",   "^((.*) uses modified data file)"], #KKD | dawkar3152 uses modified data file
            ["Player disconnected",         "^(Player (.*) disconnected.)"], #Player ARMATA disconnected.
            ["Player connecting",           "^(Player (.*) connecting.)"], #Player Celis connecting.
            ["Player connected",            "^(Player (.*) connected \(id=([0-9]*)\)\.)"], #Player Fritz connected (id=76561198117145527).
            ["Player xml parse error",      "^(Warning: Could not parse squad\.xml for Player\[(.*)\], Squad\[(.*)\])"], #Warning: Could not parse squad.xml for Player[Hptm.v.Kriegern], Squad[https://armasquads.de/user/squads/xml/gvy2AxinZc2O1N2oU00R6PWblHFr3Tte/squad.xml]
        #BattlEye
            ["BattlEye initialized",            "^(BattlEye Server: Initialized \((.*)\))"], #BattlEye Server: Initialized (v1.217)
            ["BattlEye registering player",     "^(BEServer: registering a new player #([0-9]*))"], #BEServer: registering a new player #989446346
            ["BattlEye chat message",           "^(BattlEye Server: \((.*)\) (.*): (.*))"], #BattlEye Server: (Side) Matt Fox: m
            ["BattlEye player connected",       "^(BattlEye Server: Player #([0-9]*) (.*) \(([0-9]*\.[0-9]*\.[0-9]*\.[0-9]*):([0-9]*)\) connected)"], #BattlEye Server: Player #36 Master (88.196.232.197:2304) connected
            ["BattlEye player disconnected",    "^(BattlEye Server: Player #([0-9]*) (.*) disconnected)"], #BattlEye Server: Player #4 Ztppp disconnected
            ["BattlEye player guid",            "^(BattlEye Server: Player #(.*) (.*) - GUID: (.*))"], #BattlEye Server: Player #38 Fritz - GUID: 54333f4dbe1d3c73b227c8a3ed7b663c
            ["BattlEye player guid verified",   "^(BattlEye Server: Verified GUID \((.*)\) of player #([0-9]*) (.*))"], #BattlEye Server: Verified GUID (2844515fa6c84ca6647cd55fa8c145cb) of player #8 Sgt. Gonzalez
            ["BattlEye player kicked",          "^(Player (.*) kicked off by BattlEye: (.*))"],  #Player MM Leon kicked off by BattlEye: Admin Kick (AFK too long (user_check by Ztppp))
            ["BattlEye player banned",          "^(Player (?P<player>.*?) kicked off by BattlEye: Admin Ban \((?P<reason>.*)\))"],  #Player  kicked off by BattlEye: Admin Ban (Banned by 'Yoshi_E' for 60min)
            ["BattlEye rcon admin login",       "^(BattlEye Server: RCon admin #([0-9]*) \((.*):(.*)\) logged in)"],  #BattlEye Server: RCon admin #0 (90.92.59.82:59806) logged in
            ["BattlEye chat direct message",    "^(BattlEye Server: RCon admin #([0-9]*): \(To (.*)\) (.*))"],  #BattlEye Server: RCon admin #1: (To MM Leon) 
            ["BattlEye chat global message",    "^(BattlEye Server: RCon admin #([0-9]*):)"]  #BattlEye Server: RCon admin #2: (Global) Yoshi_E: test
        ]
        #TODO: Bans?
        
        #TODO:
        """
Server: Object 2:6738 not found (message Type_120)
Error in expression <= false };
};

if (_can_use) then {
if (_unit isEqualType []) then { _unit = sel>
  Error position: <_unit isEqualType []) then { _unit = sel>
  Error Undefined variable in expression: _unit
File mpmissions\__cur_mp.Altis\Server\Functions\Server_SpawnTownResistance.sqf..., line 151
Error in expression <{

_picked = _pool select _ci;

_unit = _picked select 0;
_probability = _picked>
  Error position: <_picked select 0;
_probability = _picked>
  Error Undefined variable in expression: _picked
File mpmissions\__cur_mp.Altis\Server\Functions\Server_SpawnTownResistance.sqf..., line 142
"POOL Composer for Paros (value 350)"
        
        """
        
        #base events:
        self.base_events = ["Log new", "Log line", "Log line filtered"]
        
        self.EH = Event_Handler([row[0] for row in self.events] + self.base_events)
    
    # goes through an array of regex until it finds a match
    def check_log_events(self, line, events):
        if(self.multiEventLock):
            try:
                m = re.match(self.multiEventLock[2], line)
                if m:  
                    self.multiEventLockData.append(line)
                    result = (self.multiEventLock[0], self.multiEventLockData)
                    self.multiEventLock = None
                    tmpB = self.multiEventLockData.copy()
                    self.multiEventLockData = []
                    return result
                self.multiEventLockData.append(line)
                if(len(self.multiEventLockData)>5): #max multi line lenght
                    log.info("Warning Exceeded 'multiEventLock' length! For '{}'".format((self.multiEventLock[0], self.multiEventLockData)))
                    self.multiEventLock = None
                    self.multiEventLockData = []
            except Exception as e:
                log.print_exc()
                raise Exception("Error processing MultiEventLock: '{}' '{}'".format(self.multiEventLock, e))
        else:
            try:
                for event in events:
                    m = re.match(event[1], line)
                    if m:
                        if(len(event)>2):
                            self.multiEventLock = event
                            self.multiEventLockData.append(line)
                        else:
                            return event[0], m
            except Exception as e:
                raise Exception("Invalid Regex: '{}' '{}'".format(event, e))
        return None, None
      
    #add custom regex based events to the log reader
    def register_custom_log_event(self, event_name, regex):
        self.EH.append(event_name)
        self.events.append([event_name, regex])
    

###################################################################################################
#####                                 Line processing                                          ####
################################################################################################### 

    #Scan already written logs
    #because the logs are being scanned from newest to oldest
    #it is necessary to rearrange the data to ensure they stay in order.
    #Limited by Mission count
    def pre_scan(self):
        try:
            if(self.maxMissions <= 0):
                return
            #disable Event handlers, so they dont trigger
            self.EH.disabled = True 
            
            logs = self.getLogs()
            tempdataMissions = deque(maxlen=self.maxMissions)
            
            #scan most recent log. Until enough data is collected
            #go from newest to oldest log until the data buffer is filled
            for _log in reversed(logs):
                log.info("Pre-scanning: "+_log)
                self.scanfile(_log)
                if(len(tempdataMissions)+len(self.Missions) <= self.maxMissions):
                    tempdataMissions.extendleft(reversed(self.Missions))
                    self.Missions = deque(maxlen=self.maxMissions)
                    self.Missions.append({"dict": {}, "data": []})
                else:
                    break
                if(len(tempdataMissions)>=self.maxMissions):
                    break
            self.Missions = tempdataMissions
            self.EH.disabled = False    
        except Exception as e:
            log.print_exc()
            log.error(e)
    
    def processLogLine(self, line):
        payload = {}
        try:
            timestamp, msg = self.splitTimestamp(line)
            payload["timestamp"] = timestamp
            payload["msg"] = msg
            payload["currentLinePos"] = self.currentLinePos
            self.EH.check_Event("Log line", payload)
            event, event_match = self.check_log_events(msg, self.events)
            # if(self.EH.disabled==False):
                # log.info("{} {} {}".format(line, event, event_match))      
            #log.info(event, msg, self.multiEventLockData)
            if(event_match):
                payload["event_match"] = event_match
                self.EH.check_Event(event, payload)
                if("clutter" not in event):
                    #log.info("{} {}".format(event, event_match))
                    self.processMission(event, (timestamp, msg, event_match))
                    self.EH.check_Event("Log line filtered", payload)
            else:
                self.processMission("", (timestamp, msg))
                self.EH.check_Event("Log line filtered", payload)
        except Exception as e:
            log.print_exc()
            log.error(e)
    
    #builds mission blocks    
    def processMission(self, event, data): 
        try:
            #new mission is being started
            if(event == "Mission readname"):
                self.Missions.append({"dict": {"Server sessionID": self.server_sessionID, event: data}, "data": []})
            elif(event == "Server sessionID"):
                self.server_sessionID = data[2].group(2)
            
            #mission is complete, switching to between mission block
            elif(event == "Mission finished" or event == "Mission restarted"): 
                log.info("{} {}".format(self.Missions[-1]["dict"]["Mission id"][0], self.Missions[-1]["dict"]["Mission id"][1]))
                self.Missions[-1]["dict"][event] = data
                self.Missions.append({"dict": {"Server sessionID": self.server_sessionID}, "data": []})
            
            #process data within a mission
            elif("Mission" in event):
                self.Missions[-1]["dict"][event] = data
            self.Missions[-1]["data"].append(data)
        except Exception as e:
            log.print_exc()
            log.error(e)

###################################################################################################
#####                                       Utils                                              ####
###################################################################################################  
         
    #get the log files from folder and sort them by oldest first
    def getLogs(self):
        ignore = ["mpStatistics", "netlog"] #log files that will be ignored
        if(os.path.exists(self.log_path)):
            files = []
            for file in sorted(os.listdir(self.log_path), key = lambda thing: os.stat(os.path.join(self.log_path, thing)).st_ctime):
                if ((file.endswith(".log") or file.endswith(".rpt")) and not any(x in file for x in ignore)):
                    files.append(file)
            return files
        else:
            return []

    #returns timestamp and msg
    def splitTimestamp(self, log_line):
        #Default timeStampFormat
        #TODO: Other formats
        m = re.match(r"^\s?([0-9]{1,2}:[0-9]{2}:[0-9]{2})\s(.*)", log_line)
        if(m):
            return m.group(1), m.group(2)
        else:
            return None, log_line

###################################################################################################
#####                                    File reading                                          ####
################################################################################################### 
 
    #this function will continuously scan a log for data entries. They are stored in self.dataRows
    def scanfile(self, name):
        with open(self.log_path+name, encoding='utf-8', errors='replace') as fp: 
            try:
                line = fp.readline()
            except:
                line = None
            while line:
                self.processLogLine(line)
                try:
                    line = fp.readline()
                except Exception as e:
                    log.print_exc()
                    log.error(e)
                    line = None
    
    #follows the current log and switches to a new log, should one be created
    async def watch_log(self):
        try:
            update_counter = 0 
            while(True): #Wait till a log file exsists
                logs = self.getLogs()
                if(len(logs) > 0):
                    self.current_log = logs[-1]
                    log.info("current log: "+self.current_log)
                    self.currentLinePos = 0
                    file = open(self.log_path+self.current_log, "r")
                    for i, l in enumerate(file):
                        pass
                    self.currentLinePos = i+1
                    #file.seek(0, 2) #jump to the end of the file
                    try:
                        while (True):
                            #where = file.tell()
                            try:
                                line = file.readline()
                                update_counter+= 1
                            except:
                                line = None
                            if not line:
                                await asyncio.sleep(1)
                                #file.seek(where)
                                if(update_counter >= 60): #only check for new log files every 60s, to reduce IOPS
                                    update_counter = 0
                                    if(self.current_log != self.getLogs()[-1]):
                                        old_log = self.current_log
                                        self.current_log = self.getLogs()[-1] #update to new recent log
                                        self.currentLinePos = 0
                                        file = open(self.log_path+self.current_log, "r")
                                        log.info("current log: "+self.current_log)
                                        self.EH.check_Event("Log new", old_log, self.current_log)
                            else:
                                self.currentLinePos += 1
                                self.line = line #access to last read line (debugging)
                                self.processLogLine(line)
                    
                    except (KeyboardInterrupt, asyncio.CancelledError):
                        log.info("[asyncio] exiting {}".format(watch_log))
                    except Exception as e:
                        log.error(e)
                        log.print_exc()
                else:
                    await asyncio.sleep(10*60)
        except (KeyboardInterrupt, asyncio.CancelledError):
            log.info("[asyncio] exiting {}".format(watch_log))
        except Exception as e:
            log.print_exc()
            log.error(e)
