#!/bin/bash
# Dashboard Startup Script for Linux/Mac

echo "===================================="
echo "Discord Bot Dashboard Startup"
echo "===================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not available"
    exit 1
fi

# Install requirements if needed
echo "Installing dashboard requirements..."
pip3 install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please update the .env file with your Discord credentials!"
    read -p "Press Enter to continue..."
fi

# Start the dashboard
echo ""
echo "Starting Dashboard on http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

python3 app.py
