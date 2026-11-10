#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -f taskmate.properties ]; then echo "Missing taskmate.properties. Copy .env.example to taskmate.properties and set credentials."; exit 1; fi
mvn -q clean compile exec:java
