#!/bin/bash
# Stop all DND Schedule Manager services

echo "🛑 Stopping DND Schedule Manager..."
echo ""

# Kill web server
WEB_PIDS=$(ps aux | grep "python.*web_app.py" | grep -v grep | awk '{print $2}')
if [ ! -z "$WEB_PIDS" ]; then
    echo "🌐 Stopping web server(s)..."
    for PID in $WEB_PIDS; do
        kill $PID 2>/dev/null
        echo "   Killed PID: $PID"
    done
else
    echo "🌐 No web server running"
fi

# Kill Discord bot
BOT_PIDS=$(ps aux | grep "python.*bot.py" | grep -v grep | awk '{print $2}')
if [ ! -z "$BOT_PIDS" ]; then
    echo "🤖 Stopping Discord bot(s)..."
    for PID in $BOT_PIDS; do
        kill $PID 2>/dev/null
        echo "   Killed PID: $PID"
    done
else
    echo "🤖 No Discord bot running"
fi

# Kill cloudflared tunnel
TUNNEL_PIDS=$(ps aux | grep "cloudflared tunnel" | grep -v grep | awk '{print $2}')
if [ ! -z "$TUNNEL_PIDS" ]; then
    echo "🌐 Stopping cloudflared tunnel(s)..."
    for PID in $TUNNEL_PIDS; do
        kill $PID 2>/dev/null
        echo "   Killed PID: $PID"
    done
else
    echo "🌐 No tunnel running"
fi

sleep 1

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All services stopped!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
