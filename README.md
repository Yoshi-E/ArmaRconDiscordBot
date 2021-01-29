# ArmaRconDiscordBot

## Setup:
Make sure to enable "Privileged Gateway Intents" for the discord bot:
https://discord.com/developers/applications/
-> SERVER MEMBERS INTENT

1. Install Python3.6+
2. Clone the git `https://github.com/Yoshi-E/ArmaRconDiscordBot.git`
3. Run `pip install -r requirements.txt` to install required modules
4. Run the `bot.py` once.
5. Now configure the bot inside a web browser of your choice. Simply open the site: localhost:8000
6. Now enter all essential details (Discord token, etc.)
7. Restart the bot
8. The bot should now be functional. However the permission have to be configured first, otherwise you wont be able to use any commands. Open the settings again, and set up the permissions.
9. Now you are done.

## Troubleshooting:
 * "The system cannot find the file specified while executing the command git clone ..."
	* This means you do not have git installed on your computer. Either install git, or manually download the .whl [here](https://github.com/Yoshi-E/Python-BEC-RCon). If you choose the non git option, then you have to delete the first line in the requirments.txt and install it normally.
 * "ModuleNotFoundError: No module named '____'"
	1. You forgot to install the modules. You can just install missing modules with "pip install <module_name>"
	2. Make sure you are running the bot with the correct python instance. E.g. run the bot with "python3 bot.py" instead of just using "bot.py". Sometimes windows uses by default python2.
 * The settings page looks mostly empty
	* Try a diffrent browser (IE / Edge not supported)
## Related:
This Bot directly works with my RCon API:
https://github.com/Yoshi-E/Python-BEC-RCon

## Questions:
<dl>
  <dt>I want to bot to do this or that, what can I do?</dt>
  <dd>You open an issue here with detailed information on what you want. You can also directly contact me on discord: Yoshi_E#0405 (I am on all Bohemia discord servers).</dd>
  <dd>You can also ask in the <a href="https://forums.bohemia.net/forums/topic/223835-api-bec-rcon-api-for-python-and-discord/">Forum Thread</a></dd>

  <dt>Can I use this bot with multiple servers?</dt>
  <dd>Yes and no, currently each instance of the bot can only handel one Arma server. However you can just setup multiple instances of the bot.</dd>

  <dt>How does this bot help to administrate my server?</dt>
  <dd>You can receive push notifications directly on your phone. You can manage your server on the go.</dd>
</dl>


## Donate

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://paypal.me/TeamYoshiE)

## Features

Easy setup and configuration with a web based setup page<br>
![easy setup](https://i.imgur.com/IiIOST2.png)

Display Player account in the bots status:<br>
![player count](https://i.imgur.com/ehjPjF8.png)

Get warnings about script errors in the mission:
![script errors](https://i.imgur.com/5KsgcGR.png) 

Receive Ban notifications (Local only):<br>
![ban notifications](https://i.imgur.com/fXWWblD.png)

Warnings for people that might be using multiple accounts<br>
![multi account warning](https://i.imgur.com/vixaJAg.png)

Search users using IP, BEID, Name, last seen:<br>
![database search](https://i.imgur.com/OolyCBv.png)

See user nationality<br>
![database search](https://i.imgur.com/2huOd6e.png)

Server performance<br>
![server performance](https://i.imgur.com/9aTK480.png)

Get notified on key words<br>
![key words](https://i.imgur.com/3aSGob1.png)

## Monetization
This Bot (or code that I own inside) __cannot__ be used in a monetization process.
However you can ask for permission.

## Licence

<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br /><span xmlns:dct="http://purl.org/dc/terms/" property="dct:title">JMWBot</span> by <span xmlns:cc="http://creativecommons.org/ns#" property="cc:attributionName">Yoshi_E</span> is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License</a>.<br />

This project is not affiliated or authorized by Discord or Bohemia Interactive a.s. Bohemia Interactive, ARMA, DAYZ and all associated logos and designs are trademarks or registered trademarks of Bohemia Interactive a.s. 

