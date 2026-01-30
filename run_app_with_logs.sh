#!/bin/bash
# Helper script to run the app and capture all console logs

LOG_FILE="/tmp/fish_morphometrics_console.log"

echo "Starting Fish Morphometrics with console logging..."
echo "Logs will be written to: $LOG_FILE"
echo ""

# Kill any existing instances
pkill -f "Fish Morphometrics" 2>/dev/null
sleep 1

# Run the app and capture all output
'/Applications/Fish Morphometrics.app/Contents/MacOS/Fish Morphometrics' > "$LOG_FILE" 2>&1 &

APP_PID=$!
echo "App started with PID: $APP_PID"
echo ""
echo "To view logs in real-time, run:"
echo "  tail -f $LOG_FILE"
echo ""
echo "To search for specific patterns:"
echo "  grep 'overlay' $LOG_FILE"
echo "  grep 'drawPreview' $LOG_FILE"
echo "  grep 'First prediction' $LOG_FILE"
echo ""
echo "App is running. Press Ctrl+C to stop watching (app will keep running)."
echo ""

# Tail the log file
tail -f "$LOG_FILE"
