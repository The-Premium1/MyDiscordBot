#!/bin/bash
# Dashboard Startup Script for Railway - Handle PORT properly

echo "🚀 Starting Dashboard..."
echo "PORT env var: '$PORT'"

# Handle PORT - Railway sometimes passes it as literal $PORT string
if [ -z "$PORT" ]; then
    echo "⚠️ PORT not set, using 5000"
    PORT=5000
else
    # Remove $ if present
    PORT=$(echo "$PORT" | sed 's/^\$//')
    # Ensure it's numeric
    if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
        echo "⚠️ PORT '$PORT' is not numeric, using 5000"
        PORT=5000
    fi
fi

echo "✅ Using PORT: $PORT"
export FLASK_PORT=$PORT

# Change to dashboard directory
cd /app/dashboard || exit 1

# Run Python app
exec python app.py
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
