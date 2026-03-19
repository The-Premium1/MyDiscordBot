#!/usr/bin/env python3
"""
Start script that properly handles PORT environment variable
"""
import os
import sys

# Get PORT from environment, with fallback
port_str = os.environ.get('PORT', '5000')

# Clean up the port string - remove $ and other characters
port_str = port_str.strip().lstrip('$')

try:
    port = int(port_str)
    print(f"✅ Using PORT: {port}")
except (ValueError, TypeError) as e:
    print(f"⚠️ Could not parse PORT='{port_str}': {e}")
    port = 5000
    print(f"✅ Falling back to PORT: {port}")

# Set the port back into environment for Flask
os.environ['FLASK_PORT'] = str(port)

# Import and run app
from app import app

if __name__ == '__main__':
    print(f"🚀 Starting Flask app on 0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
