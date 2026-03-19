"""
Bot Data Connector
Allows Flask dashboard to fetch real data from the Discord bot
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict

class BotDataConnector:
    """Connects Flask dashboard to Discord bot for real data"""
    
    def __init__(self):
        self.bot = None
        self.data_file = 'bot_data.json'
        
    def set_bot(self, bot):
        """Set the Discord bot instance"""
        self.bot = bot
        
    def get_bot_stats(self) -> Dict:
        """Get real bot statistics"""
        if not self.bot or not self.bot.user:
            return self._default_stats()
        
        try:
            servers = len(self.bot.guilds)
            members = sum(guild.member_count for guild in self.bot.guilds if guild.member_count)
            uptime = self._get_uptime()
            
            return {
                'name': self.bot.user.name,
                'id': str(self.bot.user.id),
                'servers': servers,
                'members': members,
                'uptime': uptime,
                'prefix': '!',
                'version': '1.0.0',
                'status': '🟢 Online',
                'latency': f"{round(self.bot.latency * 1000)}ms"
            }
        except Exception as e:
            print(f"Error getting bot stats: {e}")
            return self._default_stats()
    
    def get_servers(self) -> List[Dict]:
        """Get list of all servers bot is in"""
        if not self.bot:
            return []
        
        try:
            servers = []
            for guild in self.bot.guilds:
                servers.append({
                    'id': str(guild.id),
                    'name': guild.name,
                    'members': guild.member_count,
                    'owner': str(guild.owner_id),
                    'icon': str(guild.icon.url) if guild.icon else None,
                    'created': guild.created_at.isoformat()
                })
            return servers
        except Exception as e:
            print(f"Error getting servers: {e}")
            return []
    
    def get_server_members(self, guild_id: int) -> List[Dict]:
        """Get members of a specific server"""
        if not self.bot:
            return []
        
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return []
            
            members = []
            for member in guild.members[:50]:  # Limit to 50
                members.append({
                    'id': str(member.id),
                    'name': member.name,
                    'joined': member.joined_at.isoformat() if member.joined_at else None,
                    'roles': [r.name for r in member.roles],
                    'bot': member.bot,
                    'avatar': str(member.avatar.url) if member.avatar else None
                })
            return members
        except Exception as e:
            print(f"Error getting members: {e}")
            return []
    
    def get_commands_list(self) -> List[Dict]:
        """Get all available commands"""
        if not self.bot:
            return []
        
        try:
            commands = []
            seen_commands = set()
            
            # Get all commands from bot
            for command in self.bot.commands:
                if command.name not in seen_commands:
                    seen_commands.add(command.name)
                    commands.append({
                        'name': command.name,
                        'description': command.help or 'No description',
                        'usage': f"!{command.name}",
                        'category': command.cog_name or 'General' if command.cog else 'General'
                    })
            
            return sorted(commands, key=lambda x: x['name'])
        except Exception as e:
            print(f"Error getting commands: {e}")
            return []
    
    def get_cogs_info(self) -> Dict:
        """Get information about loaded cogs/features"""
        if not self.bot:
            return {}
        
        try:
            cogs = {}
            for cog_name in self.bot.cogs:
                cog = self.bot.get_cog(cog_name)
                if cog:
                    commands_in_cog = len([cmd for cmd in self.bot.commands if cmd.cog == cog])
                    cogs[cog_name.lower()] = {
                        'name': cog_name,
                        'commands': commands_in_cog,
                        'loaded': True
                    }
            return cogs
        except Exception as e:
            print(f"Error getting cogs: {e}")
            return {}
    
    def get_guild_info(self, guild_id: int) -> Optional[Dict]:
        """Get detailed info about a specific guild"""
        if not self.bot:
            return None
        
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return None
            
            return {
                'id': str(guild.id),
                'name': guild.name,
                'owner_id': str(guild.owner_id),
                'members': guild.member_count,
                'channels': len(guild.channels),
                'roles': len(guild.roles),
                'created': guild.created_at.isoformat(),
                'icon': str(guild.icon.url) if guild.icon else None,
                'description': guild.description or 'No description',
                'verified': guild.verified
            }
        except Exception as e:
            print(f"Error getting guild info: {e}")
            return None
    
    def get_user_guilds(self, user_id: str) -> List[Dict]:
        """Get guilds that a user is in and bot is also in"""
        if not self.bot:
            return []
        
        try:
            user_guilds = []
            user_id_int = int(user_id)
            
            for guild in self.bot.guilds:
                member = guild.get_member(user_id_int)
                if member:
                    user_guilds.append({
                        'id': str(guild.id),
                        'name': guild.name,
                        'icon': str(guild.icon.url) if guild.icon else None,
                        'member': True,
                        'admin': member.guild_permissions.administrator
                    })
            
            return user_guilds
        except Exception as e:
            print(f"Error getting user guilds: {e}")
            return []
    
    def _get_uptime(self) -> str:
        """Calculate bot uptime"""
        try:
            if hasattr(self.bot, 'launch_time'):
                uptime = datetime.now() - self.bot.launch_time
                hours = uptime.seconds // 3600
                minutes = (uptime.seconds % 3600) // 60
                
                if uptime.days > 0:
                    return f"{uptime.days}d {hours}h {minutes}m"
                elif hours > 0:
                    return f"{hours}h {minutes}m"
                else:
                    return f"{minutes}m"
            return "Unknown"
        except Exception as e:
            return "Unknown"
    
    def _default_stats(self) -> Dict:
        """Return default stats when bot not connected"""
        return {
            'name': 'Discord Bot',
            'id': '0',
            'servers': 0,
            'members': 0,
            'uptime': 'Offline',
            'prefix': '!',
            'version': '1.0.0',
            'status': '🔴 Offline',
            'latency': 'N/A'
        }

# Global instance
bot_connector = BotDataConnector()
