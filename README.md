# ArmaRconDiscordBot

## Monetization
This Bot (or code that I own inside) __cannot__ be used in a monetization process.
However you can ask for permission.

## Licence

<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br /><span xmlns:dct="http://purl.org/dc/terms/" property="dct:title">JMWBot</span> by <span xmlns:cc="http://creativecommons.org/ns#" property="cc:attributionName">Yoshi_E</span> is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License</a>.<br />

This project is not affiliated or authorized by Discord or Bohemia Interactive a.s. Bohemia Interactive, ARMA, DAYZ and all associated logos and designs are trademarks or registered trademarks of Bohemia Interactive a.s. 

## Credits:
- I thank those many, that tested my early versions and gave feedback on it.

## Questions:
<dl>
  <dt>I want to bot to do this or that, what can I do?</dt>
  <dd>You open an issue here with detailed infromation on what you want. You can also directly contact me on discord: Yoshi_E#0405 (I am on all Bohemia discord servers).</dd>
  <dd>You can also ask in the <a href="https://forums.bohemia.net/forums/topic/223835-api-bec-rcon-api-for-python-and-discord/">Forum Thread</a></dd>

  <dt>Can I use this bot with multiple servers?</dt>
  <dd>Yes and no, currently each instance of the bot can only handel one Arma server. However you can just setup multiple instances of the bot.</dd>

  <dt>How does this bot help to administrate my server?</dt>
  <dd>You can receive push notifications directly on your phone. You can manage your server on the go.</dd>
</dl>

## Setup:
1. Install Python3.6+
2. Clone the git `https://github.com/Yoshi-E/ArmaRconDiscordBot.git`
3. Run `pip install -r requirements.txt` to install required modules
4. Run the `bot.py` once, it will quickly terminate itself, as you still have to configure some settings:
5. Configure the bot: The files are created upon the first launch
5.1. In `/modules/core/config.json` you have to enter a Discord Bot Token
5.2. In `/modules/rcon/rcon_cfg.json` you have to enter your Battleye RCon details. Read more about it here: [Battleye Rcon](https://community.bistudio.com/wiki/BattlEye#RCon).
6. Now you should be good to go! Just start the `bot.py`!

## Related:
This Bot directly works with my RCon API:
https://github.com/Yoshi-E/Python-BEC-RCon

## Donate

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://paypal.me/YoshiEU)
