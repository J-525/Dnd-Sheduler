import discord
from discord.ext import commands, tasks
import csv
from datetime import datetime, timedelta
import os
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

CSV_FILE = 'DND_SCHEDULE_MAP - Sheet1.csv'
PLAYERS = ['AZIR', 'VARIS', 'ALERIA', 'SILVER', 'IGRIS', 'DUNGEON MASTER']
TUNNEL_URL_FILE = 'tunnel_url.txt'  # File to store tunnel URL

# User mapping (Discord ID to player name)
# Configure this to map Discord users to players
USER_MAPPING = {
    '828547252904656927': 'AZIR',
    '936184431822143550': 'VARIS',
    '1188529810532741240': 'ALERIA',
    '1151570200353832960': 'SILVER',
    '1208797835844259841': 'IGRIS',
    '828606135057645588': 'DUNGEON MASTER',
}

# Reminder settings
REMINDER_CHANNEL_ID = int(os.getenv('REMINDER_CHANNEL_ID', 0))  # Channel ID for reminders
REMINDER_HOUR = 10  # Hour of day to send reminders (24-hour format, 10 = 10 AM)
REMINDER_INTERVAL_DAYS = 4  # Send reminders every 4 days
CHECK_DAYS = 5  # Check schedule for next 5 days
last_reminder_date = None  # Track last reminder sent


def get_web_url():
    """Get the current web URL (tunnel URL if available, otherwise localhost)"""
    try:
        if os.path.exists(TUNNEL_URL_FILE):
            with open(TUNNEL_URL_FILE, 'r') as f:
                url = f.read().strip()
                if url:
                    return url
    except Exception:
        pass
    return "http://localhost:5000"


class CSVManager:
    @staticmethod
    def read_csv() -> List[Dict]:
        """Read CSV and return list of dictionaries"""
        data = []
        try:
            with open(CSV_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
        except Exception as e:
            print(f"Error reading CSV: {e}")
        return data
    
    @staticmethod
    def get_next_n_days(n: int = 5) -> List[Dict]:
        """Get next N days from CSV"""
        today = datetime.now()
        data = CSVManager.read_csv()
        result = []
        
        for i in range(n):
            target_date = today + timedelta(days=i)
            date_str = target_date.strftime('%d-%m-%Y')
            
            for row in data:
                if row['DATE'] == date_str:
                    result.append(row)
                    break
        
        return result


@bot.event
async def on_ready():
    print(f'✅ {bot.user} is online and ready!')
    print(f'📅 Monitoring schedule reminders...')
    if REMINDER_CHANNEL_ID:
        print(f'🔔 Reminder channel ID: {REMINDER_CHANNEL_ID}')
    else:
        print(f'⚠️  No reminder channel configured! Set REMINDER_CHANNEL_ID in .env')
    
    # Start reminder task
    daily_reminder.start()


@tasks.loop(hours=24)
async def daily_reminder():
    """Send reminders every 4 days at specified hour"""
    global last_reminder_date
    now = datetime.now()
    
    # Only send at specific hour
    if now.hour != REMINDER_HOUR:
        return
    
    # Check if we should send reminder (every 4 days)
    if last_reminder_date:
        days_since_last = (now.date() - last_reminder_date).days
        if days_since_last < REMINDER_INTERVAL_DAYS:
            return
    
    if REMINDER_CHANNEL_ID == 0:
        print("⚠️  Reminder channel not configured!")
        return
    
    channel = bot.get_channel(REMINDER_CHANNEL_ID)
    if channel:
        await send_reminders(channel, check_today=False)
        last_reminder_date = now.date()
        
        # Also check if today is a scheduled session day
        await send_today_reminder(channel)


@bot.command(name='check')
async def check_schedule(ctx, days: int = 5):
    """Check schedule for next N days (default 5)"""
    days = min(max(days, 1), 14)
    next_days = CSVManager.get_next_n_days(days)
    
    if not next_days:
        await ctx.send("❌ No schedule data found!")
        return
    
    web_url = get_web_url()
    
    embed = discord.Embed(
        title=f"📅 DND Schedule - Next {days} Days",
        description=f"View and manage at: {web_url}",
        color=discord.Color.blue()
    )
    
    for day_data in next_days:
        players_status = []
        for player in PLAYERS:
            status = day_data.get(player, '').strip()
            emoji = {'AVAILABLE': '✓', 'MAYBE': '?', 'UNAVAILABLE': '☠'}.get(status, '○')
            players_status.append(f"{emoji} {player}")
        
        result_emoji = {'SCHEDULED': '⚅', 'POTENTIALLY': '-_-', 'NOT SCHEDULED': '☠'}.get(day_data['RESULT'], '○')
        
        embed.add_field(
            name=f"{day_data['DATE']} ({day_data['DAY']}) - {result_emoji} {day_data['RESULT']}",
            value="\n".join(players_status),
            inline=False
        )
    
    await ctx.send(embed=embed)


@bot.command(name='remind')
async def manual_remind(ctx):
    """Manually trigger reminder (Available to everyone)"""
    await send_reminders(ctx.channel, check_today=False)
    await send_today_reminder(ctx.channel)
    await ctx.send("✅ Reminder check completed!")


@bot.command(name='test_day')
async def test_day(ctx, date: str):
    """Test schedule and send reminders for a specific date (format: DD-MM-YYYY)"""
    try:
        datetime.strptime(date, '%d-%m-%Y')
    except ValueError:
        await ctx.send("⚠️  Invalid date format! Use DD-MM-YYYY (e.g., 15-04-2026)")
        return
    
    data = CSVManager.read_csv()
    row = None
    for r in data:
        if r['DATE'] == date:
            row = r
            break
    
    if not row:
        await ctx.send(f"⚠️  No data found for {date}")
        return
    
    # Show schedule status
    embed = discord.Embed(
        title=f"🎲 Schedule for {date} ({row['DAY']})",
        color=discord.Color.green()
    )
    
    available = []
    maybe = []
    unavailable = []
    not_set = []
    
    for player in PLAYERS:
        status = row.get(player, '').strip()
        if status == 'AVAILABLE':
            available.append(f"✅ {player}")
        elif status == 'MAYBE':
            maybe.append(f"❓ {player}")
        elif status == 'UNAVAILABLE':
            unavailable.append(f"❌ {player}")
        else:
            not_set.append(f"⚪ {player}")
    
    if available:
        embed.add_field(name="✅ Available", value="\n".join(available), inline=True)
    if maybe:
        embed.add_field(name="❓ Maybe", value="\n".join(maybe), inline=True)
    if unavailable:
        embed.add_field(name="❌ Unavailable", value="\n".join(unavailable), inline=True)
    if not_set:
        embed.add_field(name="⚪ Not Set", value="\n".join(not_set), inline=True)
    
    result_emoji = {'SCHEDULED': '🎲', 'POTENTIALLY': '🤔', 'NOT SCHEDULED': '❌'}.get(row['RESULT'], '⚪')
    embed.add_field(
        name="📊 Result",
        value=f"{result_emoji} **{row['RESULT']}**",
        inline=False
    )
    
    await ctx.send(embed=embed)
    
    # Send reminders for this specific date
    if not_set:
        await ctx.send("─────────────────────────────")
        await send_day_reminders(ctx.channel, date, row)


@bot.command(name='map')
@commands.has_permissions(administrator=True)
async def map_user(ctx, user: discord.Member, player: str):
    """Map a Discord user to a player (Admin only)"""
    if player not in PLAYERS:
        await ctx.send(f"⚠️  Invalid player! Choose from: {', '.join(PLAYERS)}")
        return
    
    USER_MAPPING[str(user.id)] = player
    await ctx.send(f"✅ Mapped {user.mention} to **{player}**\n⚠️  Note: This mapping is temporary. Add it to bot.py for persistence.")


@bot.command(name='web')
async def web_link(ctx):
    """Get link to web interface"""
    web_url = get_web_url()
    await ctx.send(
        "🌐 **Schedule Management Web Interface**\n"
        f"Access the schedule manager at: {web_url}"
    )


@bot.command(name='help_schedule')
async def help_command(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="🎲 DND Schedule Reminder Bot",
        description="This bot sends reminders for unfilled schedules. Manage your schedule on the web interface!",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="!check [days]",
        value="View the team schedule (default: 5 days)",
        inline=False
    )
    
    embed.add_field(
        name="!test_day <date>",
        value="Check schedule for specific date (DD-MM-YYYY)\nExample: !test_day 15-04-2026",
        inline=False
    )
    
    embed.add_field(
        name="!web",
        value="Get link to web schedule manager",
        inline=False
    )
    
    embed.add_field(
        name="!remind (Admin)",
        value="Manually trigger reminder check",
        inline=False
    )
    
    embed.add_field(
        name="!map <user> <player> (Admin)",
        value="Map Discord user to player\nExample: !map @User AZIR",
        inline=False
    )
    
    web_url = get_web_url()
    
    embed.add_field(
        name="🌐 Web Interface",
        value=f"Manage schedules at: {web_url}\n"
              f"• Full schedule view\n"
              f"• Easy dropdown selection\n"
              f"• Auto-save changes\n"
              f"• Premium dark mode UI",
        inline=False
    )
    
    embed.add_field(
        name="⏰ Automated Reminders",
        value=f"• Runs daily at {REMINDER_HOUR}:00\n"
              f"• Checks next {CHECK_DAYS} days\n"
              f"• Pings users with unfilled or unavailable status",
        inline=False
    )
    
    await ctx.send(embed=embed)


async def send_reminders(channel, check_today=False):
    """Send reminders for users who haven't filled schedule (empty status only)"""
    next_days = CSVManager.get_next_n_days(CHECK_DAYS)
    
    if not next_days:
        await channel.send("⚠️  No schedule data available!")
        return
    
    reminders = {}
    
    for day_data in next_days:
        date = day_data['DATE']
        for player in PLAYERS:
            status = day_data.get(player, '').strip()
            
            # Only track players who haven't filled (empty status)
            # Do NOT remind players who chose UNAVAILABLE, AVAILABLE, or MAYBE
            if not status:
                if player not in reminders:
                    reminders[player] = []
                reminders[player].append(date)
    
    if not reminders:
        await channel.send("✅ All players have filled their schedules!")
        return
    
    web_url = get_web_url()
    
    embed = discord.Embed(
        title="⚠️  Schedule Reminder - Action Required!",
        description=f"Please fill your schedule for the next {CHECK_DAYS} days at: {web_url}",
        color=discord.Color.orange()
    )
    
    mentions = []
    
    for player, dates in reminders.items():
        # Find Discord user for this player
        user_id = None
        user = None
        for uid, pname in USER_MAPPING.items():
            if pname == player:
                user_id = uid
                try:
                    user = await bot.fetch_user(int(user_id))
                except:
                    pass
                break
        
        # Show username if found, otherwise show player name
        if user:
            player_display = f"**{user.name}** ({player})"
        else:
            player_display = f"**{player}**"
            
        embed.add_field(
            name=player_display,
            value=f"⚪ **Not filled:** {', '.join(dates)}",
            inline=False
        )
        
        if user_id:
            mentions.append(f"<@{user_id}>")
    
    embed.set_footer(text=f"🌐 Fill your schedule at {web_url}")
    
    mention_text = " ".join(mentions) if mentions else ""
    await channel.send(content=mention_text, embed=embed)


async def send_day_reminders(channel, date: str, row: dict):
    """Send reminders for a specific day to players who haven't filled"""
    web_url = get_web_url()
    
    not_filled = []
    mentions = []
    
    for player in PLAYERS:
        status = row.get(player, '').strip()
        if not status:  # Only remind if not filled
            not_filled.append(player)
            
            # Find Discord user
            for uid, pname in USER_MAPPING.items():
                if pname == player:
                    try:
                        user = await bot.fetch_user(int(uid))
                        mentions.append(f"<@{uid}>")
                    except:
                        pass
                    break
    
    if not not_filled:
        await channel.send(f"✅ All players have filled their status for {date}!")
        return
    
    embed = discord.Embed(
        title=f"⚠️  Reminder for {date}",
        description=f"The following players need to fill their schedule:\n\n{web_url}",
        color=discord.Color.red()
    )
    
    embed.add_field(
        name="⚪ Not Filled",
        value="\n".join([f"• {p}" for p in not_filled]),
        inline=False
    )
    
    embed.set_footer(text=f"🌐 Update at {web_url}")
    
    mention_text = " ".join(mentions) if mentions else ""
    await channel.send(content=mention_text, embed=embed)


async def send_today_reminder(channel):
    """Send reminder on the actual session day to everyone"""
    today = datetime.now().strftime('%d-%m-%Y')
    
    data = CSVManager.read_csv()
    today_row = None
    for r in data:
        if r['DATE'] == today:
            today_row = r
            break
    
    if not today_row:
        return  # No session today
    
    result = today_row.get('RESULT', '').strip()
    
    # Only send if session is scheduled or potentially scheduled
    if result not in ['SCHEDULED', 'POTENTIALLY']:
        return
    
    web_url = get_web_url()
    
    # Mention everyone in the mapping
    mentions = [f"<@{uid}>" for uid in USER_MAPPING.keys()]
    
    embed = discord.Embed(
        title=f"🎲 Session Day: {today} ({today_row['DAY']})",
        description="Today is a D&D session day!",
        color=discord.Color.gold()
    )
    
    # Show who's available
    available = []
    maybe = []
    unavailable = []
    not_set = []
    
    for player in PLAYERS:
        status = today_row.get(player, '').strip()
        if status == 'AVAILABLE':
            available.append(f"✅ {player}")
        elif status == 'MAYBE':
            maybe.append(f"❓ {player}")
        elif status == 'UNAVAILABLE':
            unavailable.append(f"❌ {player}")
        else:
            not_set.append(f"⚪ {player}")
    
    if available:
        embed.add_field(name="✅ Available", value="\n".join(available), inline=True)
    if maybe:
        embed.add_field(name="❓ Maybe", value="\n".join(maybe), inline=True)
    if unavailable:
        embed.add_field(name="❌ Unavailable", value="\n".join(unavailable), inline=True)
    if not_set:
        embed.add_field(name="⚪ Not Set", value="\n".join(not_set), inline=True)
    
    result_emoji = {'SCHEDULED': '🎲', 'POTENTIALLY': '🤔'}.get(result, '⚪')
    embed.add_field(
        name="📊 Session Status",
        value=f"{result_emoji} **{result}**",
        inline=False
    )
    
    embed.set_footer(text=f"Have a great session! 🎲")
    
    mention_text = " ".join(mentions)
    await channel.send(content=f"{mention_text}\n\n**🎲 SESSION DAY REMINDER 🎲**", embed=embed)


# Run the bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        print("⚠️  DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please set it in your .env file before running the bot.")
        exit(1)
    
    print("🚀 Starting DND Schedule Reminder Bot...")
    print("⏳ Connecting to Discord...")
    
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        print("Check bot.log for details")
        exit(1)
