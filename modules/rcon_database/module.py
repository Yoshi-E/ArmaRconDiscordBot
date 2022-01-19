
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
import prettytable
import requests

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
        self.alter_database()
        #self.player_db = CoreConfig.cfg.new(self.path+"/player_db.json")

        self.cfg = CoreConfig.modules["modules/rcon_database"]["general"]
        
        asyncio.ensure_future(self.on_ready())
        self.players = None


    async def on_ready(self):
        await self.bot.wait_until_ready()
        if("CommandRcon" not in self.bot.cogs):
            log.error("[module] 'CommandRcon' required, but not found in '{}'. Module unloaded".format(type(self).__name__))
            del self
            return
        try:
            self.CommandArma = self.bot.cogs["CommandArma"]
            self.CommandArma.readLog.EH.add_Event("Player connected", self.playerConnected)
        except KeyError:
            self.CommandArma = None
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
                        stamp DATETIME,
                        profileid INTEGER
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
    
    def alter_database(self):
        try:
            ## Alter table (upgrade by adding the profileid column)
            self.c.execute("SELECT COUNT(*) AS CNTREC FROM pragma_table_info('users') WHERE name='profileid'")
            if self.c.fetchone()[0]==0: 
                
                sql = """   ALTER TABLE users
                            ADD COLUMN profileid INTEGER;"""
                self.c.execute(sql)
                self.con.commit()
                log.info("Altered DB Table: 'Added COLUMN profileid'")
        except Exception as e:
            log.print_exc()
            log.error(e)  
            
    async def fetch_player_data_loop(self):
        while True: 
            try:
                if(self.CommandRcon.arma_rcon.disconnected==True):
                    await asyncio.sleep(60)
                    continue
                try:
                    self.players = await self.CommandRcon.arma_rcon.getPlayersArray()
                except Exception as e:
                    await asyncio.sleep(60)
                    continue
                #self.player_db.save = False 
                
                
                c_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") 

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
            await asyncio.sleep(60)
            
    async def setTopicPlayerList(self, players):
        #log.info("[DEBUG] {}".format(players))#
        channel = self.bot.get_channel(self.cfg["setTopicPlayerList_channel"])
        if(not channel):
            return
        playerlist = "Players online: "+str(len(players))+" - "
        for player in players:
            playerlist += player[4]+", "
        await channel.edit(topic=playerlist[:-2])
    
    
    # fetches players profile ID from the log file, 
    # and adds it to the database if it can be matched to a user.
    async def playerConnected(self, event, data):
        try:
            player_name = data["event_match"].group(2)
            player_profileID = int(data["event_match"].group(3))
            for i in range(2):
                for player in self.players:
                    name = player[4]
                    if(name.endswith(" (Lobby)")): #Strip lobby from name
                        name = name[:-8]
                        
                    if name == player_name:
                        beid = player[3]
                        ip = player[1].split(":")[0]
                        sql = """   UPDATE users
                                    SET profileid = ?
                                    WHERE name = ?
                                          AND beid = ?
                                          AND ip = ?
                                          AND stamp > date('now','-1 day')"""
                                                                                
                        log.debug(sql)
                        self.c.execute(sql, (player_profileID, name, beid, ip))
                        self.con.commit()
                        break
                    await asyncio.sleep(60)
        except Exception as e:
            log.print_exc()
            log.error(e)
        
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
        sql = "SELECT * FROM users WHERE name = ? AND beid = ? AND ip = ? AND stamp > date('now','-1 day')"
        self.c.execute(sql, (row["name"], row["beid"], row["ip"]))
        r = self.c.fetchone()
        if r is None: 
            #TODO Handel stamp = Null
            sql = 'INSERT INTO users (id, name, beid, ip, stamp) values(?, ?, ?, ?, ?)'
            self.c.execute(sql, (row["id"], row["name"], row["beid"], row["ip"], row["stamp"]))
            self.con.commit()

    def find_by_linked(self, beid, beids = None, ips = None, names = None):
        try:
            if(beids == None):
                beids = set()       
            if(ips == None):
                ips = set()      
            if(names == None):
                names = set()
            self.c.execute("SELECT count(beid) FROM users WHERE beid = ?", (beid, ))
            if self.c.fetchone()[0]==0: 
                return {"beids": beids, "ips": ips, "names": names}
                
            entries = self.c.execute("SELECT * FROM users WHERE beid = ?", (beid, ))
            entries = entries.fetchall()
            for data in entries:
                beids.add(data[2])
                ips.add(data[3])
                names.add(data[1])

                ip_list = self.c.execute("SELECT * FROM users WHERE ip = ?", (data[3], ))
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

        result = self.c.execute("SELECT * FROM users WHERE {} LIKE ? GROUP BY beid ORDER BY stamp DESC".format(field), (data, ))
        
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

    @CommandChecker.command(name='players+',
        brief="Lists players on the server and checks if they are regulars",
        pass_context=True)
    async def players(self, ctx):
        players = await self.CommandRcon.arma_rcon.getPlayersArray()
        msgtable = prettytable.PrettyTable()
        msgtable.field_names = ["ID", "Name", "IP", "GUID", "First Seen", "Visits"]
        msgtable.align["ID"] = "r"
        msgtable.align["Name"] = "l"
        msgtable.align["IP"] = "l"
        msgtable.align["GUID"] = "l"
        msgtable.align["First Seen"] = "l"
        msgtable.align["Visits"] = "r"

        limit = 100
        i = 1
        new = False
        msg  = ""
        for player in players:
            if(i <= limit):
                first_seen = self.c.execute("SELECT * FROM users WHERE beid = ? AND stamp IS NOT NULL ORDER BY stamp ASC LIMIT 1", (player[3], ))
                first_seen = list(first_seen)
                if(len(first_seen) > 0):
                    first_seen = first_seen[0][4].split(" ")[0]
                else:
                    first_seen = ""
                visits = self.c.execute("SELECT COUNT(*) FROM users WHERE beid = ?", (player[3], ))
                visits = list(visits)
                if(len(visits) > 0):
                    visits = visits[0][0]
                else:
                    visits = 0
                msgtable.add_row([player[0], discord.utils.escape_markdown(player[4], as_needed=True), player[1],player[3], first_seen, visits])
                if(len(str(msgtable)) < 1800):
                    i += 1
                    new = False
                else:
                    msg += "```"
                    msg += str(msgtable)
                    msg += "```"
                    await ctx.send(msg)
                    msgtable.clear_rows()
                    msg = ""
                    new = True
        if(new==False):
            msg += "```"
            msg += str(msgtable)
            msg += "```"
            await ctx.send(msg)      
            
    @CommandChecker.command(name='regulars',
        brief="Lists the most seen players",
        pass_context=True)
    async def regulars(self, ctx):
        sql = """   SELECT name,COUNT(beid) AS cnt FROM users
                    GROUP BY beid
                    ORDER BY cnt DESC;
        """
        players = self.c.execute(sql)
        players = (list(players)[:10])
        
        msgtable = prettytable.PrettyTable()
        msgtable.field_names = ["Name", "Visits"]
        msgtable.align["Name"] = "l"
        msgtable.align["Visits"] = "r"

        limit = 100
        i = 1
        new = False
        msg  = ""
        for player in players:
            if(i <= limit):
                msgtable.add_row([discord.utils.escape_markdown(player[0], as_needed=True), player[1]])
                if(len(str(msgtable)) < 1800):
                    i += 1
                    new = False
                else:
                    msg += "```"
                    msg += str(msgtable)
                    msg += "```"
                    await ctx.send(msg)
                    msgtable.clear_rows()
                    msg = ""
                    new = True
        if(new==False):
            msg += "```"
            msg += str(msgtable)
            msg += "```"
            await ctx.send(msg)      
            
    @CommandChecker.command(name='query',
        brief="Runs and commits an SQL command",
        help="""table: 'users'
        columns: 
        id INTEGER NOT NULL,
        name  TEXT,
        beid TEXT,
        ip TEXT,
        stamp DATETIME
        
        returns at most 15 rows
        """,
        pass_context=True)
    async def query(self, ctx, *query):
        try:
            query = " ".join(query)
            log.info(query)
            result = self.c.execute(query)
            result = list(result)
            self.con.commit()
            
            msg = ""
            for row in result[:15]:
                msg += "{}\n".format(row)
            if(msg == ""):
                msg = "Query returned nothing"
        except Exception as e:
            msg = str(e)
        await ctx.send(msg)    
        
    @CommandChecker.command(name='convertID',
        brief="Convert a players ID. Can be Steam ID, BattlEye ID or Bohemia ID",
        aliases=["convertid"],
        pass_context=True)
    async def convertid(self, ctx, id):
        url = '	https://api.devt0ols.net/converter/'

        params = dict(id=id)
        resp = requests.get(url=url, params=params, verify=False)
        data = resp.json() # Check the JSON Response Content documentation below
        msg=""
        for key, val in data["result"].items():
            if(key == "steam_url"):
                msg += "{} {}\n".format(key, val)
            else:
                msg += "{} ``{}``\n".format(key, val)
        await ctx.send(msg)
        
def setup(bot):
    bot.add_cog(CommandRconDatabase(bot))