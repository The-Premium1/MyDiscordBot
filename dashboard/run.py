#!/usr/bin/env python3
"""
Flask app runner that handles PORT correctly
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get PORT from environment - try multiple ways
port_str = None

# Method 1: Direct environment variable
if 'PORT' in os.environ:
    port_str = os.environ['PORT']
    logger.info(f"PORT from environ: {port_str}")

# Method 2: If PORT is literally "$PORT", replace it
if not port_str or port_str == '$PORT':
    logger.warning("PORT not set or literal '$PORT', using default 5000")
    port_str = '5000'

# Convert to integer
try:
    port = int(port_str)
    logger.info(f"✅ Using port: {port}")
except (ValueError, TypeError) as e:
    logger.error(f"❌ Invalid port: {port_str}, error: {e}")
    port = 5000
    logger.info(f"✅ Fallback to port: {port}")

# Import app AFTER setting environment
os.environ['PORT'] = str(port)

from app import app

if __name__ == '__main__':
    logger.info(f"🚀 Starting Flask app on 0.0.0.0:{port}")
    try:
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"❌ Failed to start app: {e}")
        sys.exit(1)

