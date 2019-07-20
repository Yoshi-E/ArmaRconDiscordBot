import traceback
import sys
from discord.ext import commands
from discord.ext.commands import has_permissions, CheckFailure
import discord
import os
import json


class Config():
    def __init__(self, cfg_path = None, default_cfg_path = None):
        self.cfg = {}
        self.cfg_path = cfg_path
        self.default_cfg_path = default_cfg_path
        
        if(default_cfg_path):
            self.cfg_default = json.load(open(self.default_cfg_path,"r"))
       
        if(cfg_path):
            self.load()

    def load(self):
        self.cfg = self.json_load()
    
    def json_load(self):
        cfg = None
        if(os.path.isfile(self.cfg_path)):
            cfg_t = json.load(open(self.cfg_path,"r"))
            if(self.default_cfg_path):
                cfg = self.cfg_default.copy()
                cfg.update(cfg_t)
            else:
                cfg = cfg_t
        else:
            if(self.default_cfg_path):
                with open(self.cfg_path, 'w') as outfile:
                    json.dump(self.cfg_default, outfile, indent=4, separators=(',', ': '), default=serialize)
                cfg = self.cfg_default
        if(cfg == None):
            return {}
        return cfg
        
    def json_save(self):
        if(self.cfg_path ):
            with open(self.cfg_path, 'w') as outfile:
                json.dump(self.cfg, outfile, indent=4, separators=(',', ': '), default=serialize)   
    
    # resets custom config
    def reset(self):
        with open(self.cfg_path, 'w') as outfile:
            json.dump(self.cfg, outfile, indent=4, separators=(',', ': '), default=serialize)
            
    # deletes config files      
    def delete():
        if(self.cfg_path):
            os.remove(self.cfg_path)
        if(self.default_cfg_path):
            os.remove(self.default_cfg_path)

    # returns default value for config key
    def default(self, key):
        if(self.default_cfg_path and key in self.cfg_default):
            return self.cfg_default[key]
        raise KeyError("No default value found for key '{}'".format(key))
    
    def __repr__(self):
        return "Config(default: {}, cfg: {})".format(self.default_cfg_path, self.cfg_path)
        
    def __contains__(self, item):
        return item in self.cfg
            
    def __setitem__(self, key: str, value):
        #if(isinstance(value, Config)):
        self.cfg[key] = value
        self.json_save()
        
    def __getitem__(self, key: str):
        if(key in self.cfg):
            return self.cfg[key]
        raise KeyError("No value found for key '{}'".format(key))
    
    def __str__(self):
        return str(self.cfg)
    
    def __dict__(self):
        return self.cfg
    
    def to_json(self):
        return self.cfg

    # return a new config handler
    def new(self, cfg_path = None, default_cfg_path = None):
        return Config(cfg_path, default_cfg_path)

  
def serialize(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, Config):
        return str(obj.cfg)

    return obj.__dict__

     
class Commandconfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
       
        self.path = os.path.dirname(os.path.realpath(__file__))
        cfg = Config(self.path+"/config.json", self.path+"/config.default_json")
        self.cfg = cfg
        self.bot.cfg = cfg
        
    @commands.command(  name='config_reload',
                        brief="reloads the config",
                        description="reloads the config from disk")
    @has_permissions(administrator=True)
    async def config_reload(self):
        self.bot.cfg.load()
        await ctx.send("Reloaded!")
                

def setup(bot):
    bot.add_cog(Commandconfig(bot))
