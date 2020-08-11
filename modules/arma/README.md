# readLog

## Setup:
ReadLog is a python script designed to be a flexible interface of reading all kinds of log files. <br>
It's main purpose is to listen to a servers log file and wait for certain events to happen.
<br><br>
In the current configuration it is optimized for Arma 3 log entries.

## Features:
 * Read Logs in real time
 * Event based for all functionality 
 * uses a config consisting of regex to be easly configured for other Titles

## Donate

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://paypal.me/TeamYoshiE)

## Usage

```python
reader = readLog("D:/Server/Arma/Logs/", maxMisisons=25)
reader.register_custom_log_event(event_name="clutter", regex="^(Overflow)") #register custom revents
reader.EH.add_Event("clutter", someFunction) #Calls "someFunction" when a log line of type "clutter" is read
                                             #Passed arguments are: timestamp, msg, [regexMatch]
reader.pre_scan() #Scan existing log files, does not fire EventHandlers
asyncio.ensure_future(self.readLog.watch_log()) #Read Logs in real time
```

All data is stored in readLog.Missions in the following format:
```python
# readLog.Missions is split into the following entries:
[Server Init]
[Mission 1]
[between Mission data]
[Mission 2]
[between Mission data]
[Mission 3]
# Crash
[Server Init]
[Mission 4]
[between Mission data]
...
[currently running Mission]


# Server init and between Mission data look like this.
# 0 <= index < maxMisisons
# index = -1 the latest, currently running mission
readLog.Missions[index]["dict"] = {"Server sessionID": server_sessionID} 
readLog.Missions[index]["data"] = [ [timestamp, msg, regexMatch],
                                    [timestamp, msg],
                                    [timestamp, msg],
                                    [timestamp, msg, regexMatch],
                                    ...
                                ]



# The mission block is almost identical, just contains additional information about the mission in the header:
readLog.Missions[index]["dict"] = {"Server sessionID": server_sessionID,
                                    "Mission readname",
                                    "Mission roles assigned",
                                    "Mission reading",
                                    "Mission starting",
                                    "Mission file",
                                    ...
                                }
readLog.Missions[index]["data"] = [ [timestamp, msg, regexMatch],
                                    [timestamp, msg],
                                    [timestamp, msg],
                                    [timestamp, msg, regexMatch],
                                    ...
                                ]
                                
# To differentiate the block types simply check if the "dict" contains "Mission readname".
# The "Server sessionID" identifies all blocks from the same log file.
```
## Core Events

 * Log new: Triggered when a new log file is created and used. Gives old and new log.
 * Log line: Triggered whenever a log line is read. Gives timestamp and message.
 * Log line filtered: Triggered whenever a non "cluttered" log line is read. Gives timestamp, message and regexMatch.
 
## Arma 3 features
Provides recent mission data in a list grouped by mission.<br>
Mission events are ordered by the order they occur in the log:

 * Mission readname: contains Mission name in group 2
 * Mission roles assigned
 * Mission reading
 * Mission starting
 * Mission file: contains Mission file name in group 2 (e.g. becti_current (__cur_mp)) without extension
 * Mission world: contains Mission world in group 2 (e.g. Altis)
 * Mission directory: contains Mission in group 2 (e.g. mpmissions\\__cur_mp.Altis\\)
 * Mission read
 * Mission id: contains unique Mission id in group 2 (e.g. 13dfdd0042a09e918dfe17933d1372e6cefc3f9a). Unique for every session, if you load a save file, the id will remain identical.
 * Mission started
 * Mission finished

Additionally the following events are used:<br> 
Server info:

 * Server sessionID
 * Server online       
 * Server port         
 * Server waiting for game
 
Player info: 

 * Player modified data file
 * Player disconnected
 * Player connecting
 * Player connected
 * Player xml parse error

Battleye:

 * BattlEye initialized
 * BattlEye registering player
 * BattlEye chat message
 * BattlEye player connected
 * BattlEye player disconnected
 * BattlEye player guid
 * BattlEye player guid verified
 * BattlEye player kicked
 * BattlEye rcon admin login
 * BattlEye chat direct message

 
## Monetization
This Bot (or code that I own inside) __cannot__ be used in a monetization process.
However you can ask for permission.

## Licence

<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br /><span xmlns:dct="http://purl.org/dc/terms/" property="dct:title">JMWBot</span> by <span xmlns:cc="http://creativecommons.org/ns#" property="cc:attributionName">Yoshi_E</span> is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License</a>.<br />

This project is not affiliated or authorized by Discord or Bohemia Interactive a.s. Bohemia Interactive, ARMA, DAYZ and all associated logos and designs are trademarks or registered trademarks of Bohemia Interactive a.s. 

