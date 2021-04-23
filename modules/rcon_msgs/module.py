
# Work with Python 3.6
import asyncio
from collections import Counter
import json
import os
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, CheckFailure
import ast
import sys
import traceback

from modules.core.utils import CommandChecker, sendLong, CoreConfig
from modules.core.Log import log
log.setLevel(20)

class CommandJoinMSG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        
        self.cfg = CoreConfig.modules["modules/rcon_msgs"]["general"]
        
        
        asyncio.ensure_future(self.on_ready())
        
    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.channel = self.bot.get_channel(self.cfg["post_channel"])
        if("CommandRcon" not in self.bot.cogs):
            log.info("[module] 'CommandRcon' required, but not found in '{}'. Module unloaded".format(type(self).__name__))
            del self
            return
        try:
            self.CommandRcon = self.bot.cogs["CommandRcon"]
            self.CommandRcon.arma_rcon.add_Event("received_ServerMessage", self.rcon_on_msg_received)
        except Exception as e:
            log.print_exc()
            log.error(e)
            
    #function called when a new message is received by rcon
    def rcon_on_msg_received(self, args):
        try:
            message=args[0].strip()
           
            if(message.startswith("Player #")):
                #log.info(message)
                if(self.cfg["send_player_connect_msg"]):
                    #"disconnect"
                    if(message.endswith(" disconnected") and ":" not in message):
                        if(self.cfg["send_player_connect_msg_hide_details"]):
                            message = ":x: "+" ".join(message.split(" ")[2:-1])
                        asyncio.ensure_future(self.channel.send(message))
                    #"connect"
                    elif(message.endswith(") connected")):
                        if(self.cfg["send_player_connect_msg_hide_details"]):
                            msg = "(".join(message.split("(")[:-1]) #removes the last block with the ip
                            msg = ":white_check_mark: "+" ".join(msg.split(" ")[2:])
                        else:
                            msg = message
                        asyncio.ensure_future(self.channel.send(msg))
        except Exception as e:
            log.print_exc()
            log.error(e)
                
    
###################################################################################################
#####                                  common functions                                        ####
###################################################################################################
 
def setup(bot):
    bot.add_cog(CommandJoinMSG(bot))
    