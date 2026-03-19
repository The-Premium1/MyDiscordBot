import discord
from discord.ext import commands
import json
import os

REACTION_ROLES_CONFIG = "reaction_roles_config.json"

def load_reaction_roles_config():
    if os.path.exists(REACTION_ROLES_CONFIG):
        with open(REACTION_ROLES_CONFIG, "r") as f:
            return json.load(f)
    return {}

def save_reaction_roles_config(config):
    with open(REACTION_ROLES_CONFIG, "w") as f:
        json.dump(config, f, indent=2)


class ReactionRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reaction_roles = load_reaction_roles_config()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle reaction added."""
        if payload.user_id == self.bot.user.id:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        config_key = f"{payload.guild_id}_{payload.message_id}"
        
        if config_key not in self.reaction_roles:
            return
        
        emoji_str = str(payload.emoji)
        role_data = self.reaction_roles[config_key].get(emoji_str)
        
        if not role_data:
            return
        
        role = guild.get_role(role_data['role_id'])
        if not role:
            return
        
        member = guild.get_member(payload.user_id)
        if member:
            try:
                await member.add_roles(role)
            except:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Handle reaction removed."""
        if payload.user_id == self.bot.user.id:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        config_key = f"{payload.guild_id}_{payload.message_id}"
        
        if config_key not in self.reaction_roles:
            return
        
        emoji_str = str(payload.emoji)
        role_data = self.reaction_roles[config_key].get(emoji_str)
        
        if not role_data:
            return
        
        role = guild.get_role(role_data['role_id'])
        if not role:
            return
        
        member = guild.get_member(payload.user_id)
        if member:
            try:
                await member.remove_roles(role)
            except:
                pass

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addreactionrole(self, ctx: commands.Context, message_id: int, emoji: str, role: discord.Role):
        """Add a reaction role to a message."""
        try:
            message = await ctx.channel.fetch_message(message_id)
        except:
            return await ctx.send("❌ Message not found!")
        
        config_key = f"{ctx.guild.id}_{message_id}"
        
        if config_key not in self.reaction_roles:
            self.reaction_roles[config_key] = {}
        
        emoji_str = str(emoji)
        self.reaction_roles[config_key][emoji_str] = {
            'emoji': emoji,
            'role_id': role.id,
            'role_name': role.name
        }
        
        save_reaction_roles_config(self.reaction_roles)
        
        try:
            await message.add_reaction(emoji)
        except:
            pass
        
        await ctx.send(f"✅ Reaction role added! React with {emoji} to get {role.mention}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def createreactionmenu(self, ctx: commands.Context, *, title: str = "Reaction Roles"):
        """Create a reaction role menu."""
        embed = discord.Embed(
            title=title,
            description="React to get roles!",
            color=discord.Color.blurple()
        )
        
        message = await ctx.send(embed=embed)
        
        config_key = f"{ctx.guild.id}_{message.id}"
        self.reaction_roles[config_key] = {}
        save_reaction_roles_config(self.reaction_roles)
        
        await ctx.send(f"✅ Reaction menu created! Message ID: **{message.id}**\nUse `!addreactionrole {message.id} emoji role`")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removereactionrole(self, ctx: commands.Context, message_id: int, emoji: str):
        """Remove a reaction role."""
        config_key = f"{ctx.guild.id}_{message_id}"
        
        if config_key not in self.reaction_roles:
            return await ctx.send("❌ No reaction roles found for this message!")
        
        emoji_str = str(emoji)
        if emoji_str not in self.reaction_roles[config_key]:
            return await ctx.send("❌ This emoji is not set up!")
        
        role_name = self.reaction_roles[config_key][emoji_str]['role_name']
        del self.reaction_roles[config_key][emoji_str]
        save_reaction_roles_config(self.reaction_roles)
        
        await ctx.send(f"✅ Removed {emoji} -> {role_name}")


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRoles(bot))
