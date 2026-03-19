#!/bin/bash

# Find ffmpeg in nix store and add to PATH
if [ -f /nix/store/*/bin/ffmpeg ]; then
    FFMPEG_PATH=$(ls -d /nix/store/*/bin/ffmpeg 2>/dev/null | head -1)
    if [ -f "$FFMPEG_PATH" ]; then
        export PATH="$(dirname $FFMPEG_PATH):$PATH"
        echo "âœ… FFmpeg found at: $FFMPEG_PATH"
    fi
fi

# Verify ffmpeg is in PATH
which ffmpeg && echo "âœ… FFmpeg available in PATH" || echo "âŒ FFmpeg not in PATH"

# Start the bot
python main.py
