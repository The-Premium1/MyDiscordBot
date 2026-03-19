from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
import sqlite3
import json
import os
from datetime import datetime, timedelta
import secrets
import requests
from dotenv import load_dotenv
import sys

# Add parent directory to path to import bot connector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot_data_connector import bot_connector

# Load environment variables from parent directory
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

app = Flask(__name__, template_folder='templates', static_folder='static')

# CRITICAL: Fixed secret key that persists
SECRET_KEY = os.getenv('SECRET_KEY') or 'fixed-secret-key-for-sessions-12345'
app.secret_key = SECRET_KEY

print(f"🔑 Using SECRET_KEY: {SECRET_KEY[:20]}...")

# Configure sessions properly
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Local testing
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_REFRESH_EACH_REQUEST=False
)

CORS(app)

# Database setup
DATABASE = 'dashboard.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        return f(session['user_id'], *args, **kwargs)
    return decorated_function

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guilds (
            guild_id INTEGER PRIMARY KEY,
            guild_name TEXT,
            owner_id INTEGER,
            prefix TEXT DEFAULT '!',
            settings TEXT,
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            command TEXT,
            user_id INTEGER,
            timestamp TEXT,
            success BOOLEAN
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            command_name TEXT,
            response TEXT,
            created_by INTEGER,
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dashboard_users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            email TEXT,
            password_hash TEXT,
            api_token TEXT,
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_guilds (
            user_id INTEGER,
            guild_id INTEGER,
            role TEXT,
            PRIMARY KEY (user_id, guild_id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not api_token:
            return jsonify({'error': 'Unauthorized'}), 401
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM dashboard_users WHERE api_token = ?", (api_token,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(user['user_id'], *args, **kwargs)
    
    return decorated_function

# Routes

@app.before_request
def before_request():
    """Make session permanent for all requests"""
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=7)

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    print(f"📱 Login page accessed - Session user_id: {session.get('user_id')}")
    
    # If already logged in, go to dashboard
    if 'user_id' in session:
        print(f"✅ User already logged in, redirecting to dashboard")
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM dashboard_users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['user_id']
            return jsonify({'success': True})
        
        return jsonify({'error': 'Invalid credentials'}), 401
    
    return render_template('login.html')

@app.route('/auth/discord')
def auth_discord():
    """Redirect to Discord OAuth2 authorization"""
    client_id = os.getenv('DISCORD_CLIENT_ID')
    redirect_uri = os.getenv('DISCORD_REDIRECT_URI')
    
    discord_auth_url = f"https://discord.com/api/oauth2/authorize"
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'identify email guilds'
    }
    
    query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
    auth_url = f"{discord_auth_url}?{query_string}"
    
    return redirect(auth_url)

@app.route('/callback')
def callback():
    """Discord OAuth2 callback"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error or not code:
        print("❌ No code or error from Discord")
        return redirect(url_for('login'))
    
    try:
        # Exchange code for token
        client_id = os.getenv('DISCORD_CLIENT_ID')
        client_secret = os.getenv('DISCORD_CLIENT_SECRET')
        redirect_uri = os.getenv('DISCORD_REDIRECT_URI')
        
        print(f"🔄 Exchanging code for token...")
        print(f"   Client ID: {client_id}")
        print(f"   Redirect URI: {redirect_uri}")
        
        token_url = 'https://discord.com/api/oauth2/token'
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        resp = requests.post(token_url, data=data, headers=headers)
        resp.raise_for_status()
        
        token_data = resp.json()
        access_token = token_data.get('access_token')
        print(f"✅ Got access token")
        
        # Get user info
        user_url = 'https://discord.com/api/users/@me'
        headers = {'Authorization': f'Bearer {access_token}'}
        user_resp = requests.get(user_url, headers=headers)
        user_resp.raise_for_status()
        
        user_data = user_resp.json()
        user_id = str(user_data.get('id'))
        username = user_data.get('username')
        email = user_data.get('email')
        
        print(f"✅ Got user info: {username} ({user_id})")
        
        # Store user in database
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO dashboard_users 
            (user_id, username, email, api_token, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, email, access_token, datetime.now().isoformat()))
        
        # Get user's guilds from Discord API
        guilds_url = 'https://discord.com/api/users/@me/guilds'
        guilds_resp = requests.get(guilds_url, headers=headers)
        user_guilds = guilds_resp.json() if guilds_resp.ok else []
        
        # Add guilds where user is admin/owner
        for guild in user_guilds:
            guild_id = guild.get('id')
            # Check if user is owner (bit 3 = ADMINISTRATOR permission)
            permissions = int(guild.get('permissions', 0))
            is_admin = (permissions & 8) == 8  # ADMINISTRATOR permission
            is_owner = guild.get('owner', False)
            
            if is_admin or is_owner:
                cursor.execute("""
                    INSERT OR REPLACE INTO user_guilds (user_id, guild_id, role, joined_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, guild_id, 'owner' if is_owner else 'admin', datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # SET SESSION - ORDER MATTERS!
        print(f"📝 Setting session...")
        session.permanent = True
        session['user_id'] = user_id
        session['username'] = username
        session['email'] = email
        
        print(f"✅ Session set: {{'user_id': '{user_id}', 'username': '{username}'}}")
        print(f"✅ Redirecting to /dashboard")
        
        return redirect('/dashboard')
        
    except Exception as e:
        print(f"❌ Auth error: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    print(f"📊 Dashboard route - Session: {dict(session)}")
    print(f"📊 user_id in session: {'user_id' in session}")
    
    if 'user_id' not in session:
        print("❌ No user_id in session, redirecting to login")
        return redirect(url_for('login'))
    
    print(f"✅ User {session.get('username')} accessing dashboard")
    return render_template('dashboard-new.html')

# API Endpoints

@app.route('/api/user-info')
def api_user_info():
    """Get current user info"""
    print(f"🔍 User info check - Session: {dict(session)}")
    
    if 'user_id' not in session:
        print("❌ Not authenticated")
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_info = {
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'email': session.get('email')
    }
    
    print(f"✅ Returning user info: {user_info}")
    return jsonify(user_info)

@app.route('/api/bot-stats')
def api_bot_stats():
    """Get bot statistics from live Discord bot"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get REAL data from bot connector
    stats = bot_connector.get_bot_stats()
    return jsonify(stats)


@app.route('/api/servers')
def api_servers():
    """Get list of servers USER manages that bot is in"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    
    # Get ALL servers bot is in
    all_servers = bot_connector.get_servers()
    
    # Get user's guilds (from database - guilds they manage)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT guild_id FROM user_guilds WHERE user_id = ?
    """, (user_id,))
    user_guild_ids = [str(row[0]) for row in cursor.fetchall()]
    conn.close()
    
    # Filter: only return servers bot is in AND user manages
    user_servers = [s for s in all_servers if str(s.get('id')) in user_guild_ids]
    
    return jsonify(user_servers)


@app.route('/api/commands')
def api_commands():
    """Get list of available commands"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get REAL commands from bot
    commands = bot_connector.get_commands_list()
    return jsonify(commands)


@app.route('/api/features')
def api_features():
    """Get all bot features and their status"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get REAL cogs/features from bot
    cogs = bot_connector.get_cogs_info()
    
    features = []
    for cog_name, cog_info in cogs.items():
        features.append({
            'name': cog_info['name'],
            'enabled': cog_info['loaded'],
            'description': f"{cog_info['commands']} commands",
            'category': cog_name
        })
    
    return jsonify(features)


@app.route('/api/members')
def api_members():
    """Get server members"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    guild_id = request.args.get('guild_id', type=int)
    
    if guild_id:
        # Get members from specific guild
        members = bot_connector.get_server_members(guild_id)
    else:
        # Get all members from all guilds
        members = []
        for guild in bot_connector.get_servers():
            guild_members = bot_connector.get_server_members(int(guild['id']))
            members.extend(guild_members)
    
    return jsonify(members)


@app.route('/api/server/<int:guild_id>/config')
def api_server_config(guild_id):
    """Get real configuration for a specific server"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    
    # Check if user has access to this guild
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_guilds WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
    access = cursor.fetchone()
    
    if not access:
        conn.close()
        return jsonify({'error': 'Access denied'}), 403
    
    # Get guild info from bot
    guild_info = bot_connector.get_guild_info(guild_id)
    
    # Get saved settings from database
    cursor.execute("SELECT settings, prefix FROM guilds WHERE guild_id = ?", (guild_id,))
    guild_row = cursor.fetchone()
    saved_settings = json.loads(guild_row['settings']) if guild_row and guild_row['settings'] else {}
    prefix = guild_row['prefix'] if guild_row else '!'
    
    # Get loaded cogs/features
    cogs = bot_connector.get_cogs_info()
    features = []
    for cog_name, cog_info in cogs.items():
        features.append({
            'name': cog_info['name'],
            'enabled': cog_info['loaded'],
            'commands': cog_info['commands']
        })
    
    conn.close()
    
    return jsonify({
        'guild_info': guild_info,
        'settings': saved_settings,
        'prefix': prefix,
        'features': features,
        'members_count': guild_info.get('members', 0)
    })


@app.route('/api/server/<int:guild_id>/stats')
def api_server_stats(guild_id):
    """Get real analytics for a specific server"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    
    # Check access
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_guilds WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Access denied'}), 403
    
    days = request.args.get('days', 7, type=int)
    since = datetime.now() - timedelta(days=days)
    
    # Top commands in this server
    cursor.execute("""
        SELECT command, COUNT(*) as count, SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
        FROM analytics
        WHERE guild_id = ? AND timestamp > ? 
        GROUP BY command
        ORDER BY count DESC
        LIMIT 10
    """, (guild_id, since.isoformat()))
    
    top_commands = [{'command': row[0], 'total': row[1], 'successful': row[2]} for row in cursor.fetchall()]
    
    # Active members
    cursor.execute("""
        SELECT COUNT(DISTINCT user_id) FROM analytics
        WHERE guild_id = ? AND timestamp > ? AND success = 1
    """, (guild_id, since.isoformat()))
    active_users = cursor.fetchone()[0]
    
    # Total commands
    cursor.execute("""
        SELECT COUNT(*), SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)
        FROM analytics
        WHERE guild_id = ? AND timestamp > ?
    """, (guild_id, since.isoformat()))
    total_count, successful_count = cursor.fetchone()
    
    conn.close()
    
    return jsonify({
        'top_commands': top_commands,
        'active_users': active_users,
        'total_commands': total_count or 0,
        'successful_commands': successful_count or 0,
        'period_days': days
    })


@app.route('/api/server/<int:guild_id>/settings', methods=['GET', 'POST'])
def api_server_settings(guild_id):
    """Get or update server settings"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check access
    cursor.execute("SELECT * FROM user_guilds WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Access denied'}), 403
    
    if request.method == 'GET':
        cursor.execute("SELECT settings, prefix FROM guilds WHERE guild_id = ?", (guild_id,))
        row = cursor.fetchone()
        settings = json.loads(row['settings']) if row and row['settings'] else {}
        prefix = row['prefix'] if row else '!'
        conn.close()
        return jsonify({'settings': settings, 'prefix': prefix})
    
    if request.method == 'POST':
        data = request.get_json()
        settings_json = json.dumps(data.get('settings', {}))
        prefix = data.get('prefix', '!')
        
        cursor.execute("""
            INSERT OR REPLACE INTO guilds (guild_id, settings, prefix, created_at)
            VALUES (?, ?, ?, ?)
        """, (guild_id, settings_json, prefix, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Settings saved'})

@app.route('/api/guilds/<int:guild_id>/analytics', methods=['GET'])
@require_auth
def get_analytics(user_id, guild_id):
    """Get analytics for a guild."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check access
    cursor.execute("SELECT * FROM user_guilds WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Access denied'}), 403
    
    days = request.args.get('days', 7, type=int)
    since = datetime.now() - timedelta(days=days)
    
    # Commands used
    cursor.execute('''
        SELECT command, COUNT(*) as count
        FROM analytics
        WHERE guild_id = ? AND timestamp > ? AND success = 1
        GROUP BY command
        ORDER BY count DESC
    ''', (guild_id, since.isoformat()))
    
    commands = [{'command': row[0], 'count': row[1]} for row in cursor.fetchall()]
    
    # Active users
    cursor.execute('''
        SELECT COUNT(DISTINCT user_id)
        FROM analytics
        WHERE guild_id = ? AND timestamp > ?
    ''', (guild_id, since.isoformat()))
    
    active_users = cursor.fetchone()[0]
    
    # Top users
    cursor.execute('''
        SELECT user_id, COUNT(*) as count
        FROM analytics
        WHERE guild_id = ? AND timestamp > ? AND success = 1
        GROUP BY user_id
        ORDER BY count DESC
        LIMIT 10
    ''', (guild_id, since.isoformat()))
    
    top_users = [{'user_id': row[0], 'count': row[1]} for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'commands': commands,
        'active_users': active_users,
        'top_users': top_users,
        'period_days': days
    })

@app.route('/api/guilds/<int:guild_id>/custom-commands', methods=['GET', 'POST'])
@require_auth
def custom_commands(user_id, guild_id):
    """Get or create custom commands."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check access
    cursor.execute("SELECT * FROM user_guilds WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Access denied'}), 403
    
    if request.method == 'GET':
        cursor.execute("SELECT * FROM custom_commands WHERE guild_id = ?", (guild_id,))
        commands = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(commands)
    
    if request.method == 'POST':
        data = request.get_json()
        cursor.execute('''
            INSERT INTO custom_commands (guild_id, command_name, response, created_by, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (guild_id, data['command_name'], data['response'], user_id, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

@app.route('/api/guilds/<int:guild_id>/custom-commands/<int:cmd_id>', methods=['DELETE'])
@require_auth
def delete_custom_command(user_id, guild_id, cmd_id):
    """Delete a custom command."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check access
    cursor.execute("SELECT * FROM user_guilds WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Access denied'}), 403
    
    cursor.execute("DELETE FROM custom_commands WHERE id = ? AND guild_id = ?", (cmd_id, guild_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/analytics', methods=['POST'])
def log_analytics():
    """Log command usage (called from bot)."""
    token = request.headers.get('Authorization', '')
    if token != 'Bot ' + os.environ.get('BOT_ANALYTICS_TOKEN', 'secret'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO analytics (guild_id, command, user_id, timestamp, success)
        VALUES (?, ?, ?, ?, ?)
    ''', (data['guild_id'], data['command'], data['user_id'], datetime.utcnow().isoformat(), data.get('success', True)))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
