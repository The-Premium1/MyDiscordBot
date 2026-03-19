#!/usr/bin/env python3
"""
Simple wrapper to run Flask app with proper PORT handling
"""
import os
import sys

# Force PORT to be set
port = os.environ.get('PORT', '5000')
if not port or port == '$PORT':  # Handle case where shell didn't expand
    port = '5000'

print(f"🚀 Starting Flask app on port {port}")

# Set environment variable explicitly
os.environ['PORT'] = port

# Import and run the app
from app import app

if __name__ == '__main__':
    try:
        port_int = int(port)
    except ValueError:
        print(f"❌ Invalid PORT: {port}, using 5000")
        port_int = 5000
    
    app.run(host='0.0.0.0', port=port_int, debug=False)
