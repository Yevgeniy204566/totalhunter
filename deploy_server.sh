#!/bin/bash
# Деплой сервера на GCP 34.68.86.57
# Запускать: bash deploy_server.sh
# Или one-liner через SSH (если есть ключ):
# ssh user@34.68.86.57 "cd /opt/totalhunter/server && git pull && source ../venv/bin/activate && alembic upgrade head && sudo systemctl restart totalhunter && sudo systemctl status totalhunter --no-pager"

SSH_USER="totalhunter"
SSH_HOST="34.68.86.57"
SERVER_DIR="/opt/totalhunter/server"
VENV_DIR="/opt/totalhunter/venv"
SERVICE="totalhunter"

ssh "$SSH_USER@$SSH_HOST" "
  cd $SERVER_DIR &&
  git pull origin main &&
  source $VENV_DIR/bin/activate &&
  alembic upgrade head &&
  sudo systemctl restart $SERVICE &&
  sudo systemctl status $SERVICE --no-pager -l | tail -20
"
