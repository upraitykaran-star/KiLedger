#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v java >/dev/null 2>&1; then echo "Java 17 is required. Install a JDK 17, then rerun."; exit 1; fi
if ! command -v mvn >/dev/null 2>&1; then echo "Maven is required. Install Maven 3.9+, then rerun."; exit 1; fi
if ! command -v mysql >/dev/null 2>&1; then echo "MySQL client not found. Install MySQL 8 and its command-line client, then run: mysql -u root -p < database/schema.sql"; else echo "To initialize the schema, run: mysql -u root -p < database/schema.sql"; fi
if [ ! -f taskmate.properties ]; then cp .env.example taskmate.properties; echo "Created taskmate.properties. Edit database credentials before launch."; fi
mvn -q -DskipTests package
