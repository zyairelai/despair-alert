#!/bin/bash

# Find all .py files in the current directory to create a specific filter
PY_FILES=$(ls *.py 2>/dev/null | tr '\n' '|' | sed 's/|$//')

if [ -z "$PY_FILES" ]; then
    echo "No .py scripts found in this directory."
    exit 0
fi

# Find processes matching the local .py files, 
# excluding the grep process and this script's process.
PROCESSES=$(ps -ao pid,args | grep -E "($PY_FILES)" | grep -v grep | grep -v "$0")

if [ -n "$PROCESSES" ]; then
    echo "Killing the following local .py processes:"
    echo "$PROCESSES" | awk '{printf "  PID: %-6s -> %s\n", $1, substr($0, index($0,$2))}'

    PIDS=$(echo "$PROCESSES" | awk '{print $1}')
    kill -9 $PIDS 2>/dev/null
    echo "Done."
else
    echo "No running local .py scripts found."
fi
