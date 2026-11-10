@echo off
cd /d "%~dp0\.."
if not exist taskmate.properties (
  echo Missing taskmate.properties. Copy .env.example to taskmate.properties and set credentials.
  exit /b 1
)
call mvn -q clean compile exec:java
