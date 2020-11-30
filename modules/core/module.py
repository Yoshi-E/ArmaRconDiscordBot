from discord.ext import commands
from discord.ext.commands import has_permissions, CheckFailure
import discord
import os

import psutil
import datetime
from modules.core import CoreConfig, CommandChecker
import modules.core.utils as utils
from modules.core.httpServer import server

class Commandconfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        
        #Load cfg:
        self.cfg = CoreConfig.cfg.new(  self.path+"/"+
                                        utils.Modules.settings_dir+"discord.json", 
                                        self.path+"/"+
                                        utils.Modules.settings_dir+"discord.default_json")
        CoreConfig.modules["modules/core"]["discord"] = self.cfg 
        
    @CommandChecker.command(  name='config_reload',
                        brief="reloads the config",
                        description="reloads the config from disk")
    async def config_reload(self, ctx):
        self.cfg.load()
        await ctx.send("Reloaded!")      

    @CommandChecker.command(  name='setpush',
                        brief="Sets the channel the bots sends status updates to",
                        description="Sets the channel the bots sends status updates to")
    async def set_push(self, ctx):
        self.cfg["post_channel"] = int(ctx.channel.id)
        await ctx.send("Channel set")       
        
    @CommandChecker.command(  name='res',
                        brief="Display system utilization",
                        description="Displays the current system resource utilization")
    async def set_push(self, ctx):
        process = psutil.Process(os.getpid())
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        td = datetime.datetime.now() - boot_time
        
    
        msg = "```asciidoc\n"
        msg += "Online since: {}\nOnline for: {}days, {}min {}s\n".format(boot_time.strftime("%Y-%m-%d %H:%M:%S"), td.days, td.seconds//3600, (td.seconds//60)%60)
        msg += "• CPU  :: {}%\n".format(round(psutil.cpu_percent(),2))
        msg += "• RAM  :: {}% ({}mb)\n".format(round(psutil.virtual_memory().percent,2), round(psutil.virtual_memory().used / 1000000))
        msg += "• SWAP :: {}% ({}mb)\n".format(round(psutil.swap_memory().percent,2), round(psutil.swap_memory().used / 1000000))
        msg += "\n"
        msg += "= Bot usage =\n"
        with process.oneshot():
             # return cached value
            msg += "• CPU  :: {}%\n".format(round(process.cpu_percent(),2))
            msg += "• RAM  :: {}mb\n".format(round(process.memory_info().rss / 1000000),2)
        msg += "```"
        await ctx.send(msg)    
        
def setup(bot):
    bot.add_cog(Commandconfig(bot))
