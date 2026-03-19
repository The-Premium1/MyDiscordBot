let currentGuild = null;
let authToken = localStorage.getItem('auth_token') || null;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    if (!authToken) {
        window.location.href = '/login';
        return;
    }

    await loadGuilds();
});

async function fetchAPI(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
        ...options.headers
    };

    const response = await fetch(endpoint, {
        ...options,
        headers
    });

    if (response.status === 401) {
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
        return;
    }

    return response.json();
}

async function loadGuilds() {
    try {
        const guilds = await fetchAPI('/api/guilds');
        const guildsList = document.getElementById('guilds-list');
        guildsList.innerHTML = '';

        guilds.forEach(guild => {
            const div = document.createElement('div');
            div.className = 'guild-item';
            div.textContent = guild.guild_name;
            div.onclick = () => selectGuild(guild);
            guildsList.appendChild(div);
        });
    } catch (error) {
        console.error('Error loading guilds:', error);
    }
}

function selectGuild(guild) {
    currentGuild = guild;
    document.querySelectorAll('.guild-item').forEach(item => {
        item.classList.remove('active');
    });
    event.target.classList.add('active');

    document.getElementById('guild-selector').classList.add('hidden');
    document.getElementById('dashboard-tabs').classList.remove('hidden');

    loadAnalytics(7);
    loadSettings();
    loadCustomCommands();
}

function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active from buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');
}

async function loadSettings() {
    try {
        const settings = await fetchAPI(`/api/guilds/${currentGuild.guild_id}/settings`);

        document.getElementById('prefix').value = settings.prefix || '!';
        document.getElementById('welcome-channel').value = settings.welcome_channel || '';
        document.getElementById('logs-channel').value = settings.logs_channel || '';
        document.getElementById('suggestions-channel').value = settings.suggestions_channel || '';
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

async function saveSettings() {
    const settings = {
        prefix: document.getElementById('prefix').value || '!',
        welcome_channel: document.getElementById('welcome-channel').value,
        logs_channel: document.getElementById('logs-channel').value,
        suggestions_channel: document.getElementById('suggestions-channel').value
    };

    try {
        await fetchAPI(`/api/guilds/${currentGuild.guild_id}/settings`, {
            method: 'POST',
            body: JSON.stringify(settings)
        });

        alert('✅ Settings saved!');
    } catch (error) {
        alert('❌ Error saving settings');
        console.error(error);
    }
}

async function loadAnalytics(days = 7) {
    try {
        const data = await fetchAPI(`/api/guilds/${currentGuild.guild_id}/analytics?days=${days}`);

        // Update stats
        document.getElementById('active-users').textContent = data.active_users;
        document.getElementById('commands-used').textContent = data.commands.reduce((sum, cmd) => sum + cmd.count, 0);

        // Top commands chart
        const topCommandsDiv = document.getElementById('top-commands');
        topCommandsDiv.innerHTML = '';

        const maxCount = Math.max(...data.commands.map(c => c.count), 1);

        data.commands.slice(0, 10).forEach(cmd => {
            const percentage = (cmd.count / maxCount) * 100;

            const html = `
                <div class="chart-item">
                    <div class="chart-label">
                        <span>!${cmd.command}</span>
                        <span>${cmd.count}</span>
                    </div>
                    <div class="chart-bar">
                        <div class="chart-fill" style="width: ${percentage}%"></div>
                    </div>
                </div>
            `;

            topCommandsDiv.innerHTML += html;
        });

        // Analytics page
        const analyticsContent = document.getElementById('analytics-content');
        analyticsContent.innerHTML = `
            <h4>Top Commands</h4>
            <div id="analytics-commands"></div>
            <h4>Top Users</h4>
            <div id="analytics-users"></div>
        `;

        const analyticsCommands = document.getElementById('analytics-commands');
        analyticsCommands.innerHTML = '';

        data.commands.forEach(cmd => {
            analyticsCommands.innerHTML += `
                <div class="command-item">
                    <div>!${cmd.command}</div>
                    <div>${cmd.count} uses</div>
                </div>
            `;
        });

        const analyticsUsers = document.getElementById('analytics-users');
        analyticsUsers.innerHTML = '';

        data.top_users.forEach(user => {
            analyticsUsers.innerHTML += `
                <div class="command-item">
                    <div>&lt;@${user.user_id}&gt;</div>
                    <div>${user.count} commands</div>
                </div>
            `;
        });

    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

async function loadCustomCommands() {
    try {
        const commands = await fetchAPI(`/api/guilds/${currentGuild.guild_id}/custom-commands`);
        const cmdsList = document.getElementById('commands-list');
        cmdsList.innerHTML = '';

        document.getElementById('custom-count').textContent = commands.length;

        commands.forEach(cmd => {
            const div = document.createElement('div');
            div.className = 'command-item';
            div.innerHTML = `
                <div class="command-info">
                    <h4>!${cmd.command_name}</h4>
                    <p>${cmd.response}</p>
                </div>
                <button class="btn btn-danger btn-small" onclick="deleteCommand(${cmd.id})">Delete</button>
            `;
            cmdsList.appendChild(div);
        });
    } catch (error) {
        console.error('Error loading custom commands:', error);
    }
}

async function createCommand() {
    const name = document.getElementById('cmd-name').value.trim();
    const response = document.getElementById('cmd-response').value.trim();

    if (!name || !response) {
        alert('❌ Fill in all fields');
        return;
    }

    try {
        await fetchAPI(`/api/guilds/${currentGuild.guild_id}/custom-commands`, {
            method: 'POST',
            body: JSON.stringify({
                command_name: name,
                response: response
            })
        });

        document.getElementById('cmd-name').value = '';
        document.getElementById('cmd-response').value = '';

        loadCustomCommands();
        alert('✅ Command created!');
    } catch (error) {
        alert('❌ Error creating command');
        console.error(error);
    }
}

async function deleteCommand(cmdId) {
    if (!confirm('Delete this command?')) return;

    try {
        await fetchAPI(`/api/guilds/${currentGuild.guild_id}/custom-commands/${cmdId}`, {
            method: 'DELETE'
        });

        loadCustomCommands();
        alert('✅ Command deleted!');
    } catch (error) {
        alert('❌ Error deleting command');
        console.error(error);
    }
}
