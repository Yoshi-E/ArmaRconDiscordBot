import discord
import traceback
from discord.ext import commands

# Make bot join server:
# https://discordapp.com/oauth2/authorize?client_id=xxxxxx&scope=bot
# API Reference
#https://discordpy.readthedocs.io/en/rewrite/ext/commands/api.html#event-reference

modules = ["errorhandle","core", "rcon"]
bot = commands.Bot(command_prefix="!", pm_help=True)
 
def load_modules():
    for extension in modules:
        try:
            bot.load_extension("modules."+extension+".module")
        except (discord.ClientException, ModuleNotFoundError):
            print('Failed to load extension: '+extension)
            traceback.print_exc()

###################################################################################################
#####                                  Initialization                                          ####
###################################################################################################     


@bot.event
async def on_ready():

    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------------')

def main():
    load_modules()

    #checking depencies 
    if("Commandconfig" in bot.cogs.keys()):
        cfg = bot.cogs["Commandconfig"].cfg
    else: 
        sys.exit("Module 'Commandconfig' not loaded, but required")
    bot.run(cfg["TOKEN"])
     

     
if __name__ == '__main__':
    main() 

            
