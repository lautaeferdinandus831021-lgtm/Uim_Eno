#!/bin/bash

cd ~/Uim_Eno/bgbot
source venv/bin/activate

while true; do

    curl -s http://127.0.0.1:4040/api/tunnels | grep public_url > /dev/null

    if [ $? -ne 0 ]; then
        echo "[WATCHER] ngrok down → restart"
        pkill -f ngrok
        sleep 2
        nohup ngrok http 8000 > ~/ngrok.log 2>&1 &
    fi

    sleep 5
done
