#!/usr/bin/env bash

set -eEo pipefail

# Set config vars for HTTP server
export HTTP_DEBUG=1
export JWT_SECRET="test"
export LOCAL_PATH="/tmp/integrity-preprocessor/http/local"
export OUTPUT_PATH="/tmp/integrity-preprocessor/http/output"
export PORT=58694 # Random

# Run server in background
if [ "$PIPENV_ACTIVE" == "1" ]; then
    python3 http/main.py &
else
    pipenv run http &
fi

# Stop server if rest of script fails
trap "pkill -f 'http/main.py'" ERR

# Server startup
sleep 2

# Run tests
if [ "$PIPENV_ACTIVE" == "1" ]; then
    pytest -v tests/test_http.py
else
    pipenv run pytest -v tests/test_http.py
fi

# Stop server
pkill -f 'http/main.py'
