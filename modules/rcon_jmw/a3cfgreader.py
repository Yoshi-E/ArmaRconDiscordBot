#import os
import linecache
#import re

class readcfg:
    def __init__(self, server_cfg, cycle_cfg):
        self.server_cfg = server_cfg
        self.cycle_cfg = cycle_cfg
        
    def getLine(self, pos):
        return linecache.getline(self.cycle_cfg, cline)
    
    def parseMissions(self):
        cycle = []
        file = open(self.cycle_cfg, "r")
        for line in file:
            if("MAP:=" in line):
                cycle.append([line.split(":=")[1].strip()])
                cycle[-1].append("")
            else:
                cycle[-1][1] += line
        return cycle
    
    def newCycleOrder(self, cycle, Map):
        index_nmap = -1
        new_cycle = []
        for num, val in enumerate(cycle):
            if(val[0] == Map):
                index_nmap = num
            if(index_nmap >= 0):
               new_cycle.append(val) 
        if(index_nmap >= 0):
            for i in range(0, index_nmap):
                new_cycle.append(cycle[i])
        else:
            print("[MapCycle] Error map not found:", Map, index_nmap)
        return new_cycle
        
    def writeMission(self, cycle, Map):
        new_cycle = self.newCycleOrder(cycle, Map)
        file = open(self.server_cfg, "r")
        #print(new_cycle)
        newfile = ""
        write = False
        for line in file:
            if("class Missions {" in line):
                write = True
                newfile += line
                for map in new_cycle:
                    newfile += map[1]
            if(write==True):
                if(line.rstrip() == "};"):
                    write=False
                    newfile += line
            else:
                newfile += line
        f = open(self.server_cfg, "w")
        f.write(newfile)
#rcfg = readcfg("D:/Server/discord/server.cfg","D:/Server/discord/jmwBOT/modules/jmw/mission_cycle.cfg")
#
#pcycle = rcfg.parseMissions()
#pcycle = rcfg.writeMission(pcycle, "Malden")