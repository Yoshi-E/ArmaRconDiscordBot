
# Works with Python 3.6
# Discord 1.2.2
import asyncio
import json
import os
import sys
import traceback
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, CheckFailure

import csv
from modules.core.utils import CommandChecker, RateBucket, sendLong, CoreConfig, Tools



class CommandRconDatabase(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.player_db = CoreConfig.cfg.new(self.path+"/player_db.json")

        asyncio.ensure_future(self.on_ready())
        
        #Import an EPM rcon database
        #First convert the EPM export (.sdf) to csv:
        #Convert SDF with https://www.rebasedata.com/convert-sdf-to-csv-online
        #then just import it:
        #self.import_epm_csv('Players.csv')

    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.CommandRcon = self.bot.cogs["CommandRcon"]
        asyncio.ensure_future(self.fetch_player_data_loop())
        
    async def fetch_player_data_loop(self):
        while True: 
            await asyncio.sleep(60)
            try:
                if(self.CommandRcon.arma_rcon.disconnected==True):
                    continue
                players = await self.CommandRcon.arma_rcon.getPlayersArray()
                self.player_db.save = False 
                
                for player in players:
                    d_row = {
                        "ID": player[0],
                        "name": player[4],
                        "beid": player[3],
                        "ip": player[1].split(":")[0], #removes port from ip
                        "note": ""
                    }    
                    if(self.in_data(d_row)==False):
                        if(player[3] not in self.player_db):
                            self.player_db[d_row["beid"]] = []
                        await self.new_data_entry(d_row)
                        self.player_db[d_row["beid"]].append(d_row)
                
                
                self.player_db.save = True
                self.player_db.json_save()
                
            except Exception as e:
                traceback.print_exc()
                print(e)
            
        
###################################################################################################
#####                                   General functions                                      ####
###################################################################################################         
    
    async def new_data_entry(self, row):
        linked = self.find_by_linked(row["beid"])
        ctx = self.bot.get_channel(int(CoreConfig.cfg["PUSH_CHANNEL"]))
        
        if(len(linked["beids"])>1):
            await ctx.send(":warning: Player '{name}' with BEID '{beid}' might be using >=2 accounts from the same ip".format(**row))
        
        
    
    def in_data(self, row):
        data = self.player_db[row["beid"]]
        for d in data:
            if(row["name"]==d["name"] and row["ip"]==d["ip"]):
                return True
        return False
                
    def import_epm_csv(self, file='Players.csv'):
        #disable auto saving, so the files is not written for every data entry
        self.player_db.save = False 
    
        with open(file, newline='',encoding='utf8') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
            head = None
            for row in spamreader:
                if(head):
                    d_row = {
                        "ID": row[0],
                        "name": row[1],
                        "beid": row[2],
                        "ip": row[3],
                        "note": row[4]
                    }
                    if(row[2] not in self.player_db):
                        self.player_db[row[2]] = []
                    self.player_db[row[2]].append(d_row)
                else:
                    head = row
        
        #Save the data
        self.player_db.save = True
        self.player_db.json_save()
        print("Databse Import sucessfull")
        
        
    def find_by_field(self, field, i):
        results = []
        for key, val in self.player_db.items():
            for data_row in val:
                if(data_row[field] == i):
                    results.append(data_row)
        return results
        
    def find_by_linked(self, beid, beids = set(), ips = set(), names = set()):
        for key, val in self.player_db.items():
            if(beid not in beids and key == beid):
                for data in val:
                    beids.add(data["beid"])
                    ips.add(data["ip"])
                    names.add(data["name"])
                    
                    ip_list = self.find_by_field("ip", data["ip"])
                    for row in ip_list:
                        ips.add(row["ip"]) 
                        if(row["beid"] not in beids):
                            beids.add(row["beid"])
                            r = self.find_by_linked(row["beid"], beids, ips, names)
                            beids = beids.union(r["beids"])
                            ips = ips.union(r["ips"])
                            names = names.union(r["names"])
        return {"beids": beids, "ips": ips, "names": names}

        #print(init)
###################################################################################################
#####                                       Commands                                           ####
###################################################################################################         


    @CommandChecker.command(name='find',
            brief="find user data by field",
            pass_context=True)
    async def find_data(self, ctx, field, data):
        result = self.find_by_field(field, data)
        if(len(result) > 0):
            msg = ""
            for row in result:
                msg += str(row)+"\n"
            await sendLong(ctx, msg)  
        else:
            await sendLong(ctx, "Sorry, I could not find anything")      
            
    @CommandChecker.command(name='find_linked',
            brief="Does a cross search over IPs and BEID",
            pass_context=True)
    async def find_linked(self, ctx, beid):
        result = self.find_by_linked(beid)
        msg = ""
        if(len(result["beids"]) > 0):
            msg+= "BEID: ```\n"
            for beid in result["beids"]:
                msg+=beid+"\n"
            msg+= "```\n"            
            
            msg+= "Names: ```"
            for name in result["names"]:
                msg+=str(name)+"\n"
            msg+= "```"
            await sendLong(ctx, msg)
        else:
            await sendLong(ctx, "Sorry, I could not find anything")  

    
    
def setup(bot):
    bot.add_cog(CommandRconDatabase(bot))