#!/bin/bash
# Script to reload uwsgi configuration

# Method 1: Touch the reload file (if touch-reload is configured)
if [ -f /tmp/uwsgi.reload ]; then
    touch /tmp/uwsgi.reload
    echo "Reload signal sent via touch-reload file"
    exit 0
fi

# Method 2: Use uwsgi --reload with PID file
if [ -f /tmp/uwsgi.pid ]; then
    uwsgi --reload /tmp/uwsgi.pid
    echo "Reload signal sent via PID file"
    exit 0
fi

# Method 3: Find uwsgi process and send HUP signal
UWSGI_PID=$(ps aux | grep '[u]wsgi' | grep -v grep | awk '{print $2}' | head -1)
if [ ! -z "$UWSGI_PID" ]; then
    kill -HUP $UWSGI_PID
    echo "Reload signal (HUP) sent to uwsgi process $UWSGI_PID"
    exit 0
fi

echo "Could not find uwsgi process or reload mechanism"
echo "Please ensure uwsgi is running with the updated configuration"

