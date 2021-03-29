import traceback
import sys
import os
import discord
from packaging import version
import time
import inspect
import json
from modules.core.Log import log

class Config():
    def __init__(self, cfg_path = None, default_cfg_path = None):
        self.cfg = {}
        self.cfg_path = cfg_path
        self.default_cfg_path = default_cfg_path
        self.save = True
        
        self.ignored = ["description"] #any item, will not be carried outside the default_cfg
        if(default_cfg_path):
            try:
                self.cfg_default = json.load(open(self.default_cfg_path,"r"))
            except Exception as e:
                log.print_exc()
                raise Exception("{} for '{}'".format(e, self.cfg_path))
       
        if(cfg_path):
            self.load()

    def load(self):
        self.cfg = self.json_load()
    
    def remove_ignored(self, tdic):
        dic = tdic.copy()
        remove_keys = []
        for key in dic.keys():
            for i in self.ignored:
                if(i in key):
                    remove_keys.append(key)
        for key in remove_keys:
            del dic[key]
        return dic
    
    def json_load(self):
        try:
            cfg = None
            if(os.path.isfile(self.cfg_path)):
                cfg_t = json.load(open(self.cfg_path,"r"))
                if(self.default_cfg_path):
                    cfg = self.cfg_default.copy()
                    cfg.update(cfg_t)
                    #TODO: remove description etc
                    with open(self.cfg_path, 'w') as outfile:
                        json.dump(self.remove_ignored(cfg), outfile, indent=4, separators=(',', ': '), default=serialize)  
                else:
                    cfg = cfg_t
            else:
                if(self.default_cfg_path):
                    with open(self.cfg_path, 'w') as outfile:
                        #TODO: remove description etc
                        json.dump(self.remove_ignored(self.cfg_default), outfile, indent=4, separators=(',', ': '), default=serialize)
                    cfg = self.cfg_default
            if(cfg == None):
                return {}
            return cfg
        except Exception as e:
            log.print_exc()
            raise Exception("{} for '{}'".format(e, self.cfg_path))
        
    def json_save(self):
        if(self.cfg_path):
            with open(self.cfg_path, 'w') as outfile:
                json.dump(self.cfg, outfile, indent=4, separators=(',', ': '), default=serialize)   
    
    # resets custom config
    def reset(self):
        with open(self.cfg_path, 'w') as outfile:
            json.dump(self.cfg, outfile, indent=4, separators=(',', ': '), default=serialize)
            
    # deletes config files      
    def delete(self):
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
        if(self.save):
            self.json_save()
            
    def __iter__(self):
        return self.cfg
    
    def items(self):
        return self.cfg.items()   

    def keys(self):
        return self.cfg.keys()
        
        
    def __getitem__(self, key: str):
        if(key in self.cfg):
            return self.cfg[key]
        raise KeyError("No value found for key '{}'".format(key))
    
    def __delitem__(self, key: str):
        if(key in self.cfg):
            del self.cfg[key]
            return True
        raise KeyError("No value found for key '{}'".format(key))
        
    def __str__(self):
        return str(self.cfg)
    
    def __dict__(self):
        return self.cfg
    
    def to_json(self):
        return self.cfg

    # return a new config handler
    def new(self, cfg_path = None, default_cfg_path = None):
        cfg = Config(cfg_path, default_cfg_path)
        return cfg
  
def serialize(obj):
    if isinstance(obj, Config):
        return str(obj.cfg)

    return obj.__dict__
