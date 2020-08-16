import traceback
import sys
import os
import discord
from discord.ext import commands
from discord.ext.commands import GroupMixin

from packaging import version
import time
import inspect
import asyncio
import glob
assert version.parse(discord.__version__) >= version.parse("1.2.2"), "Module 'Discord' required to be >= 1.2.5"


from modules.core.httpServer import server
from modules.core.config import Config

async def sendLong(ctx, msg: str, enclosed=False, hard_post_limit=4):
    discord_limit = 1900 #discord limit is 2000
    if(len(msg) > discord_limit*hard_post_limit):
        msg = msg[:discord_limit*hard_post_limit]
    while(len(msg)>0): 
        if(len(msg)>discord_limit): 
            t = msg[discord_limit::-1]
            pos = t.find("\n", 0, 1000)
            if(pos > 0):
                pos = len(t)-pos
                if(enclosed==True):
                    await ctx.send("```"+msg[:pos]+"```")
                else:
                    await ctx.send(msg[:pos])
                msg = msg[pos:]
            else:
                if(enclosed==True):
                    await ctx.send("```"+msg[:discord_limit]+"```")
                else:
                    await ctx.send(msg[:discord_limit])
                msg = msg[discord_limit:]
        else:
            if(enclosed==True):
                await ctx.send("```"+msg+"```")
            else:
                await ctx.send(msg)
            msg = ""

class Event_Handler(object):
    def __init__(self, events):
        self.events = events
        self.events.append("other")
        self.Events = []
        self.disabled = False
        
    def add_Event(self, name: str, func):
        if(name in self.events):
            self.Events.append([name,func])
        else:
            raise Exception("Failed to add unknown event: "+name)

    def remove_Event(self, name: str, func=None):
        for event in self.Events:
            if((name == event[0] and id(func)==id(event[1])) or (name == event[0] and func==None)):
                del event
                return True
        return False
        
    def check_Event(self, parent, *args):
        if(self.disabled):
            return
        for event in self.Events:
            func = event[1]
            if(event[0]==parent):
                if(inspect.iscoroutinefunction(func)): #is async
                    if(len(args)>0):
                        asyncio.ensure_future(func(parent, *args))
                    else:
                        asyncio.ensure_future(func(parent))
                else:
                    if(len(args)>0):
                        func(parent, *args)
                    else:
                        func(parent)
                        
class Modules(object):
    settings_dir = ".settings/"
    general_settings_file = "general"
    core_dir = "modules/core/"
   
    def loadCogs(bot):
        Modules.module_list = sorted(list(glob.glob("modules/*")))

        for module in  Modules.module_list:
            module = module.replace("\\", "/")
            try:
                cfg = Modules.loadCfg(module)
                if(cfg):
                    CoreConfig.modules[module] = {Modules.general_settings_file: cfg}
                    if(cfg["load_module"] == True):
                        bot.load_extension(module.replace("/", ".")+".module")
                else:
                    print("[Modules] Skipped Cogs in '{}'".format(module))
            except (discord.ClientException, ModuleNotFoundError):
                print('Failed to load extension: '+extension)
                traceback.print_exc()   
        Modules.fix_wrappers()

    def loadCfg(module):
        if("modules/core" in module):
            return CoreConfig.cfg
            
        setting_folder = module+"/"+Modules.settings_dir

        if(not os.path.exists(setting_folder)):
            return False
            os.mkdir(setting_folder)
        
        default_setting = setting_folder+Modules.general_settings_file+".default_json"
        if(not os.path.exists(default_setting)):
            default_setting =   Modules.core_dir + Modules.settings_dir + Modules.general_settings_file + ".default_json"
                          
                          
        cfg = CoreConfig.cfg.new(   setting_folder+
                                    Modules.general_settings_file+".json", 
                                    default_setting)

        return cfg
        

    def fix_wrappers():
        #We are using a custom wrapper for the discord.ext.commands
        #In the process the commands are losing information about the parameters
        #We are setting the parameters from cache:
        for cmd in CoreConfig.bot.commands:
            for func in CommandChecker.registered_func:
                if(str(cmd) == str(func.name)):
                    signature = inspect.signature(func)
                    cmd.params = signature.parameters.copy() 
                    break
                    

class Tools():
    @staticmethod
    def column(matrix, i):
        return [row[i] for row in matrix]
        

#combines items of the last X seconds into a list
class RateBucket():
    def __init__(self, function, limit = 5):
        self.limit = limit
        self.last = time.time()
        self.list = []
        self.function = function
    
    # ensures the msg is send
    async def _add_check(self):
        await asyncio.sleep(self.limit+0.1)
        self._add()
    
    def _add(self):
        if((time.time()-self.last) > self.limit):
            if(inspect.iscoroutinefunction(self.function)): #is async
                asyncio.ensure_future(self.function(self.list))
            else:
                self.function(self.list) 
            self.list = []
            self.last = time.time()
        else:
            asyncio.ensure_future(self._add_check())
                
    def add(self, value):
        self.list.append(value)
        self._add()


class CoreConfig():
    path = os.path.dirname(os.path.realpath(__file__))
    #Core config is always avaible, modules only after they are loaded
    cfg = Config(path+"/"+Modules.settings_dir+"/"+Modules.general_settings_file+".json", path+"/"+Modules.settings_dir+"/"+Modules.general_settings_file+".default_json")
    cfgDiscord = Config(path+"/"+Modules.settings_dir+"/discord.json", path+"/"+Modules.settings_dir+"/discord.default_json")
    cfgPermissions = Config(path+"/permissions.json", path+"/permissions.default_json")
    registered = []
    modules = {}
    bot = None
    def __init__(self, bot):
        
        CoreConfig.bot = bot
        self.cfgPermissions_Roles = {}
        self.WebServer = server.WebServer(bot, CommandChecker, CoreConfig)
        
    @staticmethod
    def update():
        GlobalConfig.cfg.load() #reload cfg from file 
        
    def load_role_permissions(self):
        files = glob.glob(CoreConfig.path+"/permissions_*.json")
        if(len(files)==0):
            self.generate_default_settings()
        for file in files:
            role = os.path.basename(file).replace("permissions_", "").replace(".json", "")
            self.cfgPermissions_Roles[role] = Config(CoreConfig.path+"/permissions_{}.json".format(role))
        
        #add new commands (for new modules)
        for role, data in self.cfgPermissions_Roles.items():
            for command in CoreConfig.bot.commands:
                cmd = "command_"+str(command)
                if(cmd not in self.cfgPermissions_Roles[role]):
                    self.cfgPermissions_Roles[role][cmd] = False
            
        
    def generate_default_settings(self):
        for role in CoreConfig.cfgPermissions["roles"]:
            self.cfgPermissions_Roles[role] = CoreConfig.cfg.new(CoreConfig.path+"/permissions_{}.json".format(role))
            
            if(role in ["default"]):
                val = False
            else:
                val = True
                
            for command in CoreConfig.bot.commands:
                self.cfgPermissions_Roles[role]["command_"+str(command)] = val
                
    def setCommandSetting(self, data):
        val = True if data["value"][0]=="true" else False
        self.cfgPermissions_Roles[data["role"][0]][data["name"][0]] = val
    
    def setGeneralSetting(self, data):
       CoreConfig.modules["modules/core"]["discord"]["TOKEN"] = data["token"][0]
       CoreConfig.modules["modules/core"]["discord"]["BOT_PREFIX"] = data["prefix"][0]   
       CoreConfig.modules["modules/core"]["discord"]["post_channel"] = int(data["post_channel"][0])   

    def deall_role(self, data):
        role = data["role"][0]
        for command in CoreConfig.bot.commands:
            self.cfgPermissions_Roles[role]["command_"+str(command)] = False    
    
    def all_role(self, data):
        role = data["role"][0]
        for command in CoreConfig.bot.commands:
            self.cfgPermissions_Roles[role]["command_"+str(command)] = True
        
    def add_role(self, data):
        role = data["add_role"][0]
        print("Created new role: '{}'".format(role))
        self.cfgPermissions_Roles[role] = CoreConfig.cfg.new(CoreConfig.path+"/permissions_{}.json".format(role))

        for command in CoreConfig.bot.commands:
            self.cfgPermissions_Roles[role]["command_"+str(command)] = False
            
    def delete_role(self, data):
        role = data["delete_role"][0]
        self.cfgPermissions_Roles[role].delete()
        print("Deleted role '{}'".format(role))
        self.cfgPermissions_Roles = {}
        self.load_role_permissions()
        
class CommandChecker():       
    permssion = CoreConfig.cfgPermissions
    registered = []
    registered_func = []
    @staticmethod
    def command(*d_args,**d_kwargs):
        def decorator(func):  
            CommandChecker.registered_func.append(func)
            CommandChecker.registered.append(d_kwargs["name"])
            @commands.command(*d_args,**d_kwargs)
            @commands.check(CommandChecker.checkPermission)
            async def wrapper(*args,**kwargs):
                return await func(*args,**kwargs)
            signature = inspect.signature(func)
            wrapper.params = signature.parameters.copy() 
            func.name = wrapper.name
            #print(dir(wrapper))
            #print(wrapper.cog) #__cog_commands__
            #print("####",func.__name__)
            # sys.exit()
            # for cmd in CoreConfig.bot.commands:
                # for func in CommandChecker.registered_func:
                    # if(str(cmd) == str(func.__name__)):
                        # signature = inspect.signature(func)
                        # cmd.params = signature.parameters.copy() 
                        # break
                        #sys.exit()
            return wrapper
        return decorator
    
    @staticmethod
    def disabled(ctx):
        return False
    
    @staticmethod
    def get_roles(ctx, user_id):
        server = ctx.bot.guilds[0]
        return discord.utils.get(server.members, id=user_id)
        return False

    @staticmethod
    def checkPermission(ctx):
        pr = ctx.bot.CoreConfig.cfgPermissions_Roles
        if(type(ctx) == discord.ext.commands.context.Context):
            
            # if(ctx.author.id in CommandChecker.permssion["can_use_dm"]):
                # return True
            if(hasattr(ctx.author, 'roles')):
                roles = ctx.author.roles
            else:
                roles = CommandChecker.get_roles(ctx, ctx.author.id).roles
            for role in roles:
                if str(role) in pr.keys():
                    cmd = "command_{}".format(ctx.command.name)
                    if(cmd in pr[str(role)] and pr[str(role)][cmd]):
                        return True
        return False       