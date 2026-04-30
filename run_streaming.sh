#!/bin/bash

###############################################################################
# STREAMING WRAPPER SCRIPT
# Runs kafka_to_bronze.py with error recovery and auto-restart
###############################################################################

set -e

PYTHON_CMD="python3"
SCRIPT="streaming/kafka_to_bronze.py"
MAX_RETRIES=5
RETRY_DELAY=10

retry_count=0

echo "=========================================="
echo "Starting Bronze Layer Streaming"
echo "=========================================="
echo ""

while [ $retry_count -lt $MAX_RETRIES ]; do
    retry_count=$((retry_count + 1))
    
    echo "Attempt $retry_count of $MAX_RETRIES..."
    echo ""
    
    # Run the streaming script
    if $PYTHON_CMD $SCRIPT; then
        # If script exits cleanly (Ctrl+C), stay stopped
        echo ""
        echo "Streaming stopped gracefully."
        exit 0
    else
        exit_code=$?
        echo ""
        echo "⚠️  Stream exited with code $exit_code"
        
        # Check if this is the last retry
        if [ $retry_count -lt $MAX_RETRIES ]; then
            echo "Waiting ${RETRY_DELAY}s before restart..."
            sleep $RETRY_DELAY
            echo "--------"
            echo ""
        else
            echo "❌ Max retries reached. Exiting."
            exit 1
        fi
    fi
done
