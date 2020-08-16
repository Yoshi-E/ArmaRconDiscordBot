# Ingame commands

## Setup:

## Features:
 * Create custom in game commands using RCon and Python

## Example

```python
@RconCommandEngine.command(name="ping")  
async def ping(self, rctx):
	await rctx.say("Pong!")     
	
```

rctx is the RCon context the command was call from.<br>
It provides the method:
 * say(string): Send a private message to the user
 
In addition it provides the attributes:
 * base_msg: Original message
 * func_name: Function name of the function that was called
 * parameters: parameters of the function that was called
 * args: arguments passed to the command
 * error: Error message, or False if no error occurred
 * executed: True if the command was successfully completed
 * user: Username of the user that called the command
 * command = None
 * channel: Ingame channel name (e.g. Side, Direct, Global)
 * user_beid: BEID of the user that used the command. -1 if the user could not be found (e.g. already disconnected)


## Default commands
Provides recent mission data in a list grouped by mission.<br>
Mission events are ordered by the order they occur in the log:

 * ?ping: Returns "Pong!"
 * ?players: Returns the players and their BEID
 * ?afk BEID: checks if a player is active by asking him in chat.

 
## Monetization
This Bot (or code that I own inside) __cannot__ be used in a monetization process.
However you can ask for permission.

## Donate

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://paypal.me/TeamYoshiE)

## Licence

<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br /><span xmlns:dct="http://purl.org/dc/terms/" property="dct:title">JMWBot</span> by <span xmlns:cc="http://creativecommons.org/ns#" property="cc:attributionName">Yoshi_E</span> is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License</a>.<br />

This project is not affiliated or authorized by Discord or Bohemia Interactive a.s. Bohemia Interactive, ARMA, DAYZ and all associated logos and designs are trademarks or registered trademarks of Bohemia Interactive a.s. 

