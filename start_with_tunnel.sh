#!/bin/bash
# Complete startup script with cloudflared tunnel

echo "🎲 DND Schedule Manager - Complete Startup"
echo "=========================================="
echo ""

# Stop any existing instances first
echo "🧹 Checking for existing processes..."
./stop.sh 2>/dev/null
sleep 1
echo ""

# Start web server
echo "🌐 Starting web server..."
./venv/bin/python web_app.py > /dev/null 2>&1 &
WEB_PID=$!
echo "✅ Web server started (PID: $WEB_PID)"
sleep 2

# Start Discord bot
echo "🤖 Starting Discord bot..."
./venv/bin/python bot.py > /dev/null 2>&1 &
BOT_PID=$!
echo "✅ Discord bot started (PID: $BOT_PID)"
sleep 1

# Start cloudflared tunnel
echo "🌐 Starting cloudflare tunnel (HTTP/2)..."
echo ""

if command -v cloudflared &> /dev/null; then
    # Start cloudflared with metrics enabled
    cloudflared --protocol http2 --metrics localhost:40001 tunnel --url http://localhost:5000 > /dev/null 2>&1 &
    TUNNEL_PID=$!
    echo "✅ Tunnel starting (PID: $TUNNEL_PID)"
    echo ""
    echo "⏳ Waiting for tunnel URL..."
    
    # Wait for cloudflared to start and get URL from metrics endpoint
    PUBLIC_URL=""
    for i in {1..15}; do
        sleep 1
        echo -n "."
        # Try to get URL from cloudflared metrics
        PUBLIC_URL=$(curl -s http://localhost:40001/metrics 2>/dev/null | grep -o 'https://[^"]*trycloudflare.com' | head -1)
        if [ ! -z "$PUBLIC_URL" ]; then
            break
        fi
    done
    echo ""
    
    if [ ! -z "$PUBLIC_URL" ]; then
        # Save URL to file for bot to use
        echo "$PUBLIC_URL" > tunnel_url.txt
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🎉 PUBLIC URL READY!"
        echo ""
        echo "   $PUBLIC_URL"
        echo ""
        echo "Share this URL with your players!"
        echo "Discord bot will use this URL automatically!"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    else
        echo "⚠️  Could not detect tunnel URL automatically"
        echo "   Tunnel is running on PID: $TUNNEL_PID"
        echo "   The URL will appear in Discord bot messages"
        echo "   Or check: ps aux | grep cloudflared"
        # Save localhost as fallback
        echo "http://localhost:5000" > tunnel_url.txt
    fi
else
    echo "⚠️  Cloudflared not installed. Run ./setup_tunnel.sh first"
    echo "   Web server accessible only at: http://localhost:5000"
    # Save localhost URL to file
    echo "http://localhost:5000" > tunnel_url.txt
    TUNNEL_PID=""
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All services running!"
echo ""
echo "📝 Process IDs:"
echo "   Web Server: $WEB_PID"
echo "   Discord Bot: $BOT_PID"
if [ ! -z "$TUNNEL_PID" ]; then
    echo "   Tunnel: $TUNNEL_PID"
fi
echo ""
echo "🌐 Access:"
echo "   Local: http://localhost:5000"
if [ ! -z "$PUBLIC_URL" ]; then
    echo "   Public: $PUBLIC_URL"
fi
echo ""
echo "🛑 To stop all services:"
echo "   ./stop.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
