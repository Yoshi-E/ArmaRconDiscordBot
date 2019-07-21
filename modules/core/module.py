import traceback
import sys
from discord.ext import commands
from discord.ext.commands import has_permissions, CheckFailure
import discord
import os

new_path = os.path.dirname(os.path.realpath(__file__))
if new_path not in sys.path:
    sys.path.append(new_path)
from utils import CoreConfig
     
class Commandconfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.cfg = CoreConfig.cfg
        self.bot.cfg = CoreConfig.cfg
        
    @commands.command(  name='config_reload',
                        brief="reloads the config",
                        description="reloads the config from disk")
    @has_permissions(administrator=True)
    async def config_reload(self):
        self.bot.cfg.load()
        await ctx.send("Reloaded!")
                

def setup(bot):
    bot.add_cog(Commandconfig(bot))
