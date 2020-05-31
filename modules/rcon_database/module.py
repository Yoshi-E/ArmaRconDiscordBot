
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

#Convert SDF with https://www.rebasedata.com/convert-sdf-to-csv-online

class CommandRconDatabase(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.player_db = CoreConfig.cfg.new(self.path+"/player_db.json")

        asyncio.ensure_future(self.on_ready())
        #self.import_epm_csv('Players.csv')

    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.CommandRcon = self.bot.cogs["CommandRcon"]
        
###################################################################################################
#####                                   General functions                                      ####
###################################################################################################         
        
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
###################################################################################################
#####                                       Commands                                           ####
###################################################################################################         

    @CommandChecker.command(name='find',
            brief="find user data by field",
            pass_context=True)
    async def find_data(self, ctx, field, data):
        result = self.find_by_field(field, data)
        if(len(result) > 0):
            await ctx.send("\n".join(result))  
        else:
            await ctx.send("Sorry, I could not find anything")  

        

def setup(bot):
    bot.add_cog(CommandRconDatabase(bot))