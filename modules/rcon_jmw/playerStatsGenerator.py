import json
import os
from os import listdir
from os.path import isfile, join
import numpy as np
import numpy.random
import sys
from glob import glob
from operator import itemgetter
# Usage: img = generateMap(self, player_name="all", bins=50)

class PlayerStatsGenerator():
    def __init__(self, path):
        self.data_path = path
        self.path = os.path.dirname(os.path.realpath(__file__))
        
        self.defaultTmpMap = {                  
                           #For calculating per game data
                           "total_entries": 0,
                           "current_cmd_time": 0, 
                           "side": "NONE",
                           "last_entry": [] # Last entry for a given map
                            }
        
        
        # playerScore: [infantry kills, soft vehicle kills, armor kills, air kills, deaths, total score]
        self.players = {}
        self.currentPlayers = {}
        
        if os.path.exists(self.path+"/playerStats.json"):
            with open(self.path+"/playerStats.json") as json_file:
                self.players  = json.load(json_file)
        
    def getdefaultMap(self):
        map = {"maps_played": None,
           "game_30min_played": 0,
           "game_60min_played": 0,
           "game_120min_played": 0,
           "game_240min_played": 0,
           "game_victories": 0,
           "game_defeats": 0,
           "side_opfor": 0,
           "side_bluefor": 0,
           "total_entries": 0,
           
           "total_infantry_kills": 0,
           "total_soft_vehicle_kills": 0,
           "total_armor_kills": 0,
           "total_air_kills": 0,
           "total_deaths": 0,
           "total_score": 0,
           "total_command_time": 0,
           "total_command_vicotries": 0, #for >30min
           "total_command_defeats": 0, #for >30min
        }
        map["maps_played"] = {}
        return map
        
    def processPlayers(self, data, file=""):
        if("players" not in data):
            return
            
        players = data["players"]
        for player in players:
            name = player[0]
            self.currentPlayers.setdefault(name, self.defaultTmpMap.copy())
            self.currentPlayers[name]["last_entry"] = player
            self.currentPlayers[name]["total_entries"] += 1
            if(data["commander_east"] == name or data["commander_west"] == name):
                self.currentPlayers[name]["current_cmd_time"] += 1
            if player[1] in ["EAST", "WEST"]:
                self.currentPlayers[name]["side"] = player[1]
                
    def processGameEnd(self, file):
        if("EAST" in file):
            winner = "EAST"
        else:
            winner = "WEST"
        map = file.split("#")[-2]
        for name, player in self.currentPlayers.items():
            #print(name, player)
            side = self.currentPlayers[name]["side"] #side
            self.players.setdefault(name, self.getdefaultMap())
            
            self.players[name]["total_command_time"] += player["current_cmd_time"]
            self.players[name]["total_entries"] += player["total_entries"]
            self.players[name]["maps_played"].setdefault(map, 0)
            self.players[name]["maps_played"][map] += 1
            
            #softstats:
            try:
                self.players[name]["total_infantry_kills"] += player["last_entry"][2][0]
                self.players[name]["total_soft_vehicle_kills"] += player["last_entry"][2][1]
                self.players[name]["total_armor_kills"] += player["last_entry"][2][2]
                self.players[name]["total_air_kills"] += player["last_entry"][2][3]
                self.players[name]["total_deaths"] += player["last_entry"][2][4]
                self.players[name]["total_score"] += player["last_entry"][2][5]
            except Exception as e:
                pass #print("softstats:", e)
            
            
            if side == winner:
                self.players[name]["game_victories"] += 1
            else:
                self.players[name]["game_defeats"] += 1
                
            if side == "EAST":
                self.players[name]["side_opfor"] += 1
            elif side == "WEST":
                self.players[name]["side_bluefor"] += 1
            
            if(player["total_entries"] > 30):
                self.players[name]["game_30min_played"] += 1            
            if(player["total_entries"] > 60):
                self.players[name]["game_60min_played"] += 1
            if(player["total_entries"] > 120):
                self.players[name]["game_120min_played"] += 1         
            if(player["total_entries"] > 240):
                self.players[name]["game_240min_played"] += 1
            
            
            if(player["current_cmd_time"] > 30): #all commander with > X Min cmd time will get it as a "win"
                if (winner == "EAST" and side=="EAST") or (winner == "WEST" and side=="WEST"):
                    self.players[name]["total_command_vicotries"] += 1
                else:
                    self.players[name]["total_command_defeats"] += 1
            
    def generateData(self):
        self.players = {}
    
        for file in glob(self.data_path+"/*.json"):
            self.currentPlayers = {}
            if("CUR" not in file and "ADV" in file):
                with open(file) as f:
                    data = json.load(f)
                    if(len(data) > 0):
                        for row in data:
                            if(row["CTI_DataPacket"] == "Data"):
                                try:
                                    self.processPlayers(row, file)
                                except Exception as e:
                                    print("processPlayers:", e)
                        try:
                            self.processGameEnd(file)
                        except Exception as e:
                            print("processGameEnd:", e)

    def wr(self, key):
        if(self.players[key]["game_victories"]+self.players[key]["game_defeats"] > 30):
            return self.players[key]["game_victories"]/(self.players[key]["game_defeats"] + self.players[key]["game_victories"])
        else:
            return 0
    
    def cwr(self, key):
        if(self.players[key]["total_command_defeats"]+self.players[key]["total_command_vicotries"] > 30):
            return self.players[key]["total_command_vicotries"]/(self.players[key]["total_command_defeats"] + self.players[key]["total_command_vicotries"])
        else:
            return 0
    
    def getWinrate(self):
        newlist = sorted(self.players, key=self.wr, reverse=True) 
        for key in newlist[:50]:
            print(key.ljust(30), round(self.players[key]["game_victories"]/(self.players[key]["game_defeats"] + self.players[key]["game_victories"])*100, 2))
    
    def getCMDWinrate(self):
        newlist = sorted(self.players, key=self.cwr, reverse=True) 
        for key in newlist[:50]:
            print(key.ljust(30), round(self.players[key]["total_command_vicotries"]/(self.players[key]["total_command_defeats"] + self.players[key]["total_command_vicotries"])*100, 2))
            
    def generateStats(self):
        self.generateData()
        with open(self.path+"/playerStats.json", 'w+') as outfile:
            json.dump(self.players, outfile, indent=4, sort_keys=True)
    
    def total_playtime(self):
        total = 0
        for name, player in self.players.items():
            total+= player["total_entries"]
        print(total)
if __name__ == "__main__":
    p = PlayerStatsGenerator(r"D:\Dokumente\_Git\_ArmaGit\ArmaRconDiscordBot\modules\rcon_jmw\data")
    p.total_playtime()
    #p.generateStats()
    #print(json.dumps(p.players, indent=4, sort_keys=True))