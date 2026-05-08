#!/bin/bash

cd ~/Uim_Eno/bgbot

echo "[BG-BOT] activating venv..."
source venv/bin/activate

echo "[BG-BOT] stopping old process..."
pkill -f uvicorn
pkill -f ngrok

sleep 2

echo "[BG-BOT] starting bot..."
nohup uvicorn app:app --host 0.0.0.0 --port 8000 > ~/bot.log 2>&1 &

sleep 3

echo "[BG-BOT] starting ngrok..."
nohup ngrok http 8000 > ~/ngrok.log 2>&1 &

echo "[BG-BOT] SYSTEM ONLINE"
