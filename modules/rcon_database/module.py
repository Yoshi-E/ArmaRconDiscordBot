
# Works with Python 3.6
# Discord 1.2.2
import asyncio
import json
import sqlite3 as sl
import os
import sys
import traceback
import datetime
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, CheckFailure

import csv
from modules.core.utils import CommandChecker, RateBucket, sendLong, CoreConfig, Tools
from modules.core.Log import log


class CommandRconDatabase(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        
        self.con = sl.connect(self.path+'/users.db')       
        self.c = self.con.cursor()

        
        self.upgrade_database()
        #self.player_db = CoreConfig.cfg.new(self.path+"/player_db.json")

        self.cfg = CoreConfig.modules["modules/rcon_database"]["general"]
        
        asyncio.ensure_future(self.on_ready())
        self.players = None
        #Import an EPM rcon database
        #First convert the EPM export (.sdf) to csv:
        #Convert SDF with https://www.rebasedata.com/convert-sdf-to-csv-online
        #then just import it:
        #self.import_epm_csv('Players.csv')

    async def on_ready(self):
        await self.bot.wait_until_ready()
        if("CommandRcon" not in self.bot.cogs):
            log.error("[module] 'CommandRcon' required, but not found in '{}'. Module unloaded".format(type(self).__name__))
            del self
            return
        self.CommandRcon = self.bot.cogs["CommandRcon"]
        asyncio.ensure_future(self.fetch_player_data_loop())
        #self.check_all_users()
        
    def upgrade_database(self):
        try:
            json_f = self.path+"/player_db.json"
            if(not os.path.isfile(json_f)):
                
                return
            
            #get the count of tables with the name
            self.c.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='users' ''')
            if self.c.fetchone()[0]==0 : 
                
                #load old table
                with open(json_f) as json_file:
                    data_db = json.load(json_file)

                data = []
                for key, item in data_db.items():
                    for _item in item:
                        id = None
                        name = None
                        beid = None
                        ip  = None
                        date = None
                        if "ID" in _item:
                            id = int(_item["ID"])        
                        if "name" in _item:
                            name = _item["name"]        
                        if "beid" in _item:
                            beid = _item["beid"]       
                        if "ip" in _item:
                            ip = _item["ip"]       
                        if "last-seen" in _item:
                            date = _item["last-seen"]
                        data.append((id, name, beid, ip, date))

                self.c.execute("""
                    CREATE TABLE users (
                        id INTEGER NOT NULL,
                        name  TEXT,
                        beid TEXT,
                        ip TEXT,
                        stamp DATETIME
                    );
                """)
                
                #date yyyy-MM-dd HH:mm:ss    
                sql = 'INSERT INTO users (id, name, beid, ip, stamp) values(?, ?, ?, ?, ?)'
                self.c.executemany(sql, data)
                self.con.commit()
                json_f_new = json_f.replace(".json", "_old.json")
                os.rename(json_f, json_f_new)
                log.info("*** Database has been upgraded! ***")
        except Exception as e:
            log.print_exc()
            log.error(e)
            
    async def fetch_player_data_loop(self):
        while True: 
            await asyncio.sleep(60)
            try:
                if(self.CommandRcon.arma_rcon.disconnected==True):
                    continue
                try:
                    self.players = await self.CommandRcon.arma_rcon.getPlayersArray()
                except Exception as e:
                    continue
                #self.player_db.save = False 
                
                
                c_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
                #Set status
                if(self.cfg["set_custom_status"]==True):
                    await self.set_status(self.players)                
                    
                if(self.cfg["setTopicPlayerList_channel"]>0):
                    await self.setTopicPlayerList(self.players)
                
                for player in self.players:
                    name = player[4]
                    if(name.endswith(" (Lobby)")): #Strip lobby from name
                        name = name[:-8]
                    d_row = {
                        "id": player[0],
                        "name": name,
                        "beid": player[3],
                        "ip": player[1].split(":")[0], #removes port from ip
                        "note": None,
                        "stamp": c_time
                    }   
                    self.update_insert(d_row)
                    
                
                #self.player_db.save = True
                #self.player_db.json_save()
                
            except Exception as e:
                log.print_exc()
                log.error(e)
            
    async def set_status(self, players):
        game_name = "{} Players".format(len(players))
        status = discord.Status.do_not_disturb #discord.Status.online
        if(self.CommandRcon.arma_rcon.disconnected==False):
            status = discord.Status.online
        
        await self.bot.change_presence(activity=discord.Game(name=game_name), status=status)
    
    async def setTopicPlayerList(self, players):
        #log.info("[DEBUG] {}".format(players))#
        channel = self.bot.get_channel(self.cfg["setTopicPlayerList_channel"])
        if(not channel):
            return
        playerlist = "Players online: "+str(len(players))+" - "
        for player in players:
            playerlist += player[4]+", "
        await channel.edit(topic=playerlist[:-2])
        
###################################################################################################
#####                                   General functions                                      ####
###################################################################################################         
    
    async def new_data_entry(self, row):
        linked = self.find_by_linked(row["beid"])

        if(len(linked["beids"])>1):
            channel = self.bot.get_channel(self.cfg["post_channel"])
            if(channel):
                await channel.send(":warning: Player '{name}' with BEID '{beid}' might be using >=2 accounts from the same ip".format(**row))
        

    def update_insert(self, row):
        #update only if user if last seen > 1 day or diffrent ip/beid
        self.c.execute("SELECT * FROM users WHERE name = '{name}' AND beid = '{beid}' AND ip = '{ip}' AND stamp < date('now','-1 day')".format(**row))
        r = self.c.fetchone()
        if r is None: 
            sql = 'INSERT INTO users (id, name, beid, ip, stamp) values({id}, "{name}", "{beid}", "{ip}", "{stamp}")'.format(**row)
            self.c.execute(sql)
            self.con.commit()

                
    # def import_epm_csv(self, file='Players.csv'):
        #disable auto saving, so the files is not written for every data entry
        # self.player_db.save = False 
    
        # with open(file, newline='',encoding='utf8') as csvfile:
            # spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
            # head = None
            # for row in spamreader:
                # if(head):
                    # d_row = {
                        # "ID": row[0],
                        # "name": row[1],
                        # "beid": row[2],
                        # "ip": row[3],
                        # "note": row[4]
                    # }
                    # if(row[2] not in self.player_db):
                        # self.player_db[row[2]] = []
                    # self.player_db[row[2]].append(d_row)
                # else:
                    # head = row
        
        #Save the data
        # self.player_db.save = True
        # self.player_db.json_save()
        # log.info("Databse Import sucessfull")
        
        
    def find_by_linked(self, beid, beids = None, ips = None, names = None):
        try:
            if(beids == None):
                beids = set()       
            if(ips == None):
                ips = set()      
            if(names == None):
                names = set()
            self.c.execute("SELECT count(beid) FROM users WHERE beid='{}'".format(beid))
            if self.c.fetchone()[0]==0: 
                return {"beids": beids, "ips": ips, "names": names}
                
            entries = self.c.execute("SELECT * FROM users WHERE beid = '{}'".format(beid))
            entries = entries.fetchall()
            for data in entries:
                beids.add(data[2])
                ips.add(data[3])
                names.add(data[1])

                ip_list = self.c.execute("SELECT * FROM users WHERE ip = '{}'".format(data[3]))
                ip_list = ip_list.fetchall()
                for row in ip_list:
                    ips.add(row[3]) 
                    if(row[1] not in names):
                        names.add(row[1])
                    if(row[2] not in beids):
                        beids.add(row[2])
                        r = self.find_by_linked(row[2], beids, ips, names)
                        beids = beids.union(r["beids"])
                        ips = ips.union(r["ips"])
                        names = names.union(r["names"])
            return {"beids": beids, "ips": ips, "names": names}
        except Exception as e:
            log.print_exc()
            log.error(e)

        #log.info(init)
    
    #Checks all users in the database for possible multi account usage.
    #The generated list will be printed into console.
    def check_all_users(self, min = 2):
        for key in self.player_db.keys():
            data = self.find_by_linked(key)
            if(len(data["beids"]) >= min):
                log.info(data)
###################################################################################################
#####                                       Commands                                           ####
###################################################################################################         


    @CommandChecker.command(name='find',
            brief="find user data by field",
            pass_context=True)
    async def find_data(self, ctx, field, data):
        valid = ["name", "beid", "ip", "stamp"]
        if field not in valid:
            raise Exception("Invalid field '{}', must be one of these values: {}".format(field, valid))

        result = self.c.execute("SELECT * FROM users WHERE {} = '{}' GROUP BY beid ORDER BY stamp DESC".format(field, data))
        
        if(result):
            msg = ""
            for row in result:
                msg += "{} ``{}`` ({})\n".format(row[1], row[2], row[4])
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