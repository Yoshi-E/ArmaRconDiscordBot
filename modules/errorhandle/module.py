import traceback
import sys
from discord.ext import commands
import discord
from modules.core.Log import log

class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def sendLong(self, ctx, msg):
        while(len(msg)>0):
            if(len(msg)>1800):
                await ctx.send(msg[:1800])
                msg = msg[1800:]
            else:
                await ctx.send(msg)
                msg = ""
    
    @commands.Cog.listener()
    async def on_error(event, *args, **kwargs):
        log.info(event,args, kwargs)
        
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command.
        ctx   : Context
        error : Exception"""
        
        #ignored = (commands.CommandNotFound, commands.UserInputError) #commands.errors.CheckFailure
        
        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, 'original', error)
        try:
            log.info("{}: '{}'. Error: '{}'".format(ctx.author.name, ctx.command.name, error))
        except:
            log.info("{} Error: '{}'".format(ctx, error))
            
            # return
        # Anything in ignored will return and prevent anything happening.
        # if isinstance(error, ignored):
            # try:
                # log.info("{}: '{}'. Ignored error: '{}'".format(ctx.author.name, ctx.command.name, error))
            # except:
                # log.info("{}: Ignored error: '{}'".format(ctx, error))
            # return
        
        if(isinstance(error, commands.errors.CheckFailure)):
            await self.sendLong(ctx, "{}, You do not have permission to use the command '{}'".format(ctx.author.name, ctx.command.name))
            return
        stack = traceback.extract_stack()[:-3] + traceback.extract_tb(error.__traceback__)
        pretty = traceback.format_list(stack)
        #stacktrace = ''.join(pretty) + '\n  {} {}'.format(error.__class__,error)
        stacktrace = str(error)
        await self.sendLong(ctx, (f'{ctx.command} has caused the following error: ```{stacktrace}```'))
        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, 'on_error'):
            return
        


        elif isinstance(error, commands.DisabledCommand):
            return await ctx.send(f'{ctx.command} has been disabled.')

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.author.send(f'{ctx.command} can not be used in Private Messages.')
            except:
                pass

        # All other Errors not returned come here... And we can just print the default TraceBack.
        log.info('Ignoring exception in command {}:'.format(ctx.command))
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
                

def setup(bot):
    bot.add_cog(CommandErrorHandler(bot))