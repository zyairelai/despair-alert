#!/bin/bash

# Find PIDs of processes with ".py" in their command line, 
# excluding the grep process and this script's process.
PIDS=$(ps aux | grep "\.py" | grep -v grep | grep -v "$0" | awk '{print $2}')

if [ -n "$PIDS" ]; then
    echo "Killing processes with .py extension..."
    kill -9 $PIDS 2>/dev/null
    echo "Done."
else
    echo "No running .py scripts found."
fi
