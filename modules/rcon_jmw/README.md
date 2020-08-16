# JMWBot

## Monetization
This Bot (or code that I own inside) __cannot__ be used in a monetization process.

## Licence

<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br /><span xmlns:dct="http://purl.org/dc/terms/" property="dct:title">JMWBot</span> by <span xmlns:cc="http://creativecommons.org/ns#" property="cc:attributionName">Yoshi_E</span> is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License</a>.<br />

This project is not affiliated or authorized by Discord or Bohemia Interactive a.s. Bohemia Interactive, ARMA, DAYZ and all associated logos and designs are trademarks or registered trademarks of Bohemia Interactive a.s. 

## Examples

You can use this bot to analyse the performance of your mission on your server.<br>
<img src="https://github.com/Yoshi-E/jmwBOT/blob/dev/examples/2018-10-27_3-32-27562-ADV.png" height="500"/><br>
Or use it to look at the current balance of the game in a detailed graph.<br>
Promoting the mission with it as a summary is also possible<br>
<img src="https://github.com/Yoshi-E/jmwBOT/blob/dev/examples/discord_usage_example.PNG" height="400"/>

## Usage

This discord bot is designed with flexablity in mind. The core pricinple for it is to listen to a game log and to react and summarize events in the given log. This can be any kind of game that logs details of events to a text file. In theory this bot should work with other game such as CSGO, Minecraft, GTA, ... and many more.

In the current version the bot listens to 3 types of log entries:

* CTI_Mission_Performance: Starting Server
* CTI_Mission_Performance: GameOver
* ["CTI_Mission_Performance:",["time",110.087],["fps",49.2308],["score_east",0], ...

This helps the bot to understand the current state of the game, and helps it to report game starts and ends, and as well to create a summary of its performance.
These entries have to generated server side and for this version can be found here:
* <a href="https://github.com/zerty/Benny-Edition-CTI-0.97-Zerty-Modification/blob/b28af1dad5f8214252b08e1c9c83d6808da5205a/Server/Init/Init_Server.sqf#L315-L392">Server starting and timestamps with data</a>
* <a href="https://github.com/zerty/Benny-Edition-CTI-0.97-Zerty-Modification/blob/5d71066fbab57764e0127f2467990379578f17c7/Server/FSM/update_victory.fsm#L82-L108">Registering the Winner of a round</a>

Right now it is very important that the data array is logged in a format that can be interpreted by python as a valid data structure.
Valid: [{"Data1": 10}, {"Data1": "String"}, ["Data2"]]
Invalid: ["Data": String]

## Data Analysis
Analyse tracked data with heatmaps and more!<br>
<img src="https://cdn.discordapp.com/attachments/621800377515376640/727979266020474920/unknown.png" height="400"/>
<img src="https://cdn.discordapp.com/attachments/621800377515376640/727915131341766666/heatmap.jpg" height="400"/>

## Donate

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://paypal.me/YoshiEU)
