#!/bin/bash

CWD=`dirname $0`
cd "$CWD"
CWD=`pwd`
readonly SOURCE_DIR="$CWD"
readonly TARGET_DIR="/data/data/com.termux/files/home/code/async_termux_api"
readonly SSH_USER_HOST="dreagonmon@192.168.44.1"
readonly SSH_PORT="8022"
readonly CONN_OPT="ssh -p $SSH_PORT"
readonly RSYNC_SOURCE="$SOURCE_DIR/"
readonly RSYNC_DEST="$SSH_USER_HOST:$TARGET_DIR/"

rsync -azq \
    -e "$CONN_OPT" \
    --exclude=".venv" \
    --exclude=".vscode" \
    --exclude=".git" \
    --progress \
    --safe-links \
    "$RSYNC_SOURCE" \
    "$RSYNC_DEST"

ssh "$SSH_USER_HOST" -p "$SSH_PORT" -t "cd \"$TARGET_DIR\" && python -m async_termux._test"
