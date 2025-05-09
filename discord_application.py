import discord
from discord import app_commands
from discord.ext import commands
import requests
import logging
from flask import Flask, request
import threading, asyncio
from datetime import datetime, timedelta
import os

# Configuration from environment variables
FLASK_API_URL = os.getenv("FLASK_API_URL", "http://default_url_here")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "default_token_here")
GUILD_ID = os.getenv("GUILD_ID", "123456789")

# === Bot setup ===
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# === Embed helper ===
def make_embed(title: str, description: str, color: discord.Color) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="TrackMyClass")
    return embed

# === /start ===
@bot.tree.command(name="start", description="Register yourself as a user")
async def start(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    username = interaction.user.name

    try:
        r = requests.post(
            f"{FLASK_API_URL}/create_user",
            json={"user_id": user_id, "discord_username": username},
            timeout=5
        )
        if r.status_code == 200:
            embed = make_embed("✅ Registered!", "You’ve been registered successfully.", discord.Color.green())
        else:
            embed = make_embed("❌ Registration failed", r.text, discord.Color.red())
    except Exception as e:
        embed = make_embed("⚠️ Error", f"Could not contact backend: {e}", discord.Color.orange())

    await interaction.followup.send(embed=embed)

# 1) Define a DM-only check for slash commands
def dm_only(interaction: discord.Interaction) -> bool:
    if interaction.guild is not None:
        raise app_commands.CheckFailure("DM only")
    return True

# 2) Global error handler to catch CheckFailures and respond
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    # Only handle our DM-only check failure
    if isinstance(error, app_commands.CheckFailure) and str(error) == "DM only":
        embed = make_embed(
            "❌ DM Only",
            "Please send `/subscribe` to me in a DM so I can message you with updates later.\n"
            "If you can’t DM me, make sure you’ve added the bot or enabled DMs from server members.",
            discord.Color.red()
        )
        # If we haven’t sent or deferred yet, use response; otherwise follow up
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)
    else:
        # re-raise others so they bubble up or get logged
        raise error

# 3) Apply the DM-only check to just /subscribe
@bot.tree.command(name="subscribe", description="Subscribe using a class number")
@app_commands.check(dm_only)
@app_commands.describe(class_number="Class number (e.g. 12345)")
async def subscribe(interaction: discord.Interaction, class_number: str):
    # This will only ever run in DMs
    await interaction.response.defer()
    user_id = str(interaction.user.id)

    try:
        lookup = requests.post(
            f"{FLASK_API_URL}/lookup_section_id",
            json={"class_number": class_number},
            timeout=5
        )
        if lookup.status_code != 200:
            embed = make_embed(
                "❌ Class Not Found",
                f"Could not find class `{class_number}`.",
                discord.Color.red()
            )
        else:
            section_id = lookup.json()["section_id"]
            sub = requests.post(
                f"{FLASK_API_URL}/subscribe_user",
                json={"user_id": user_id, "section_id": section_id},
                timeout=5
            )
            if sub.status_code == 200:
                embed = make_embed(
                    "✅ Subscribed!",
                    f"You are now tracking class `{class_number}`.",
                    discord.Color.green()
                )
            else:
                err = sub.json().get("error", "Subscription failed")
                embed = make_embed("❌ Subscription Failed", err, discord.Color.red())
    except Exception as e:
        embed = make_embed("⚠️ Error", f"Could not subscribe: {e}", discord.Color.orange())

    await interaction.followup.send(embed=embed)

# === /unsubscribe ===
@bot.tree.command(name="unsubscribe", description="Unsubscribe using a class number")
@app_commands.describe(class_number="Class number (e.g. 12345)")
async def unsubscribe(interaction: discord.Interaction, class_number: str):
    await interaction.response.defer()
    user_id = str(interaction.user.id)

    try:
        lookup = requests.post(f"{FLASK_API_URL}/lookup_section_id", json={"class_number": class_number}, timeout=5)
        if lookup.status_code != 200:
            embed = make_embed("❌ Class Not Found", f"Could not find class `{class_number}`.", discord.Color.red())
        else:
            section_id = lookup.json()["section_id"]
            unsub = requests.post(f"{FLASK_API_URL}/unsubscribe_user", json={"user_id": user_id, "section_id": section_id}, timeout=5)
            if unsub.status_code == 200:
                embed = make_embed("✅ Unsubscribed!", f"You have stopped tracking class `{class_number}`.", discord.Color.green())
            else:
                error = unsub.json().get("error", "Unsubscribe failed")
                embed = make_embed("❌ Unsubscribe Failed", error, discord.Color.red())
    except Exception as e:
        embed = make_embed("⚠️ Error", f"Could not unsubscribe: {e}", discord.Color.orange())

    await interaction.followup.send(embed=embed)

# === /subscriptions ===
@bot.tree.command(name="subscriptions", description="View your current class subscriptions")
async def subscriptions(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = str(interaction.user.id)

    try:
        r = requests.post(f"{FLASK_API_URL}/get_subscriptions", json={"user_id": user_id}, timeout=5)
        r.raise_for_status()
        subs = r.json().get("subscriptions", [])
        if not subs:
            embed = make_embed("📭 No Subscriptions", "You are not subscribed to any classes.", discord.Color.blurple())
        else:
            embed = discord.Embed(title="📚 Your Subscriptions", color=discord.Color.blurple())
            for sub in subs[:10]:
                embed.add_field(
                    name=f"{sub['title']} (`{sub['section_id']}`)",
                    value=f"{sub['available_seats']} seats available",
                    inline=False
                )
            if len(subs) > 10:
                embed.set_footer(text=f"...and {len(subs)-10} more")
    except Exception as e:
        embed = make_embed("⚠️ Error", f"Could not fetch subscriptions: {e}", discord.Color.orange())

    await interaction.followup.send(embed=embed)


# === /xray ===
@bot.tree.command(
    name="xray",
    description="Get detailed availability insights (X-Ray) for a class"
)
@app_commands.describe(class_number="Class number (e.g. 12345)")
async def xray(interaction: discord.Interaction, class_number: str):
    await interaction.response.defer()

    try:
        # 1) fetch xray data from Flask
        xray_response = requests.get(
            f"{FLASK_API_URL}/xray/{class_number}",
            timeout=5
        )
        if xray_response.status_code == 404:
            return await interaction.followup.send(
                embed=make_embed("❌ Class Not Found",
                                 f"Could not find `{class_number}`.",
                                 discord.Color.red())
            )

        # 2) Parse response from Flask
        xray_data = xray_response.json()

        # Extract data
        curr_avail = xray_data.get("current_availability")
        history = xray_data.get("history", [])
        class_status = (
            "❗ **Impacted** (Negative seats)" if curr_avail < 0 else
            "ℹ️ **Not Overloaded** (0 seats)" if curr_avail == 0 else
            "✅ **Open** (Positive seats)"
        )

        # 3) Create embed
        embed = discord.Embed(
            title=f"🔍 X-Ray Insights for `{class_number}`",
            color=discord.Color.blurple()
        )

        # Add current status
        embed.add_field(
            name="📊 Current Status",
            value=f"{class_status}\n**Available Seats:** {curr_avail}",
            inline=False
        )

        # Add history analysis
        if curr_avail < 0:  # Show last 5 SEAT_CHANGE events with negative counts
            embed.add_field(
                name="📉 Last 5 Seat Reductions",
                value="\n".join(
                    f"- **{datetime.fromisoformat(ev['captured_at']).strftime('%B %-d, %Y %I:%M %p')}**: "
                    f"{ev['available_seats']} seats"
                    for ev in history if ev['available_seats'] < 0
                ) or "No recent impacted seat changes found.",
                inline=False
            )
        else:  # Open or at capacity
            embed.add_field(
                name="📜 Recent Seat Adjustments",
                value="\n".join(
                    f"- **{datetime.fromisoformat(ev['captured_at']).strftime('%B %-d, %Y %I:%M %p')}**: "
                    f"{ev['available_seats']} seats"
                    for ev in history[:5]
                ) or "No recent seat changes found.",
                inline=False
            )

    except Exception as e:
        embed = make_embed("⚠️ Error", f"Could not fetch xray data: {e}", discord.Color.orange())

    await interaction.followup.send(embed=embed)


# === /history ===
@bot.tree.command(
    name="history",
    description="Get the last 5 times a class was open/closed"
)
@app_commands.describe(class_number="Class number (e.g. 12345)")
async def history(interaction: discord.Interaction, class_number: str):
    await interaction.response.defer()

    try:
        # 1) lookup section_id
        lu = requests.post(
            f"{FLASK_API_URL}/lookup_section_id",
            json={"class_number": class_number},
            timeout=5
        )
        if lu.status_code != 200:
            return await interaction.followup.send(
                embed=make_embed("❌ Class Not Found",
                                 f"Could not find `{class_number}`.",
                                 discord.Color.red()),
            )
        section_id = lu.json()["section_id"]

        # 2) fetch history
        h = requests.get(
            f"{FLASK_API_URL}/class_open_history/{class_number}",
            timeout=5
        )
        h.raise_for_status()
        raw = h.json().get("history", [])

        # 3) fetch current seats
        status = requests.get(f"{FLASK_API_URL}/section/{section_id}", timeout=5)
        curr_avail = status.json().get("available_seats") if status.status_code == 200 else None

        # 4) parse OPEN/CLOSE events
        events = []
        for ev in raw:
            state = ev["change_type"].upper()
            ts = datetime.fromisoformat(ev["captured_at"])
            if state in ("OPEN", "CLOSE"):
                events.append((state, ts))
        events.sort(key=lambda x: x[1])

        # 5) pair them up
        pairs = []
        open_time = None
        now = datetime.now()
        for state, ts in events:
            if state == "OPEN":
                open_time = ts
            elif state == "CLOSE" and open_time:
                pairs.append((open_time, ts))
                open_time = None
        # if still open according to history but now full → mark closed now
        if open_time:
            if curr_avail == 0:
                pairs.append((open_time, now))
            else:
                pairs.append((open_time, None))

        # 6) keep last 5
        pairs = pairs[-5:]
        if not pairs:
            return await interaction.followup.send(
                embed=make_embed("🔍 No History",
                                 f"No open/close events for `{class_number}`.",
                                 discord.Color.blurple()),
            )

        # 7) build embed
        embed = discord.Embed(
            title=f"📜 Open/Close History for `{class_number}`",
            color=discord.Color.blurple()
        )
        durations = []

        for opened_at, closed_at in reversed(pairs):
            o = opened_at.strftime("%B %-d, %Y at %-I:%M %p")
            if closed_at:
                c = closed_at.strftime("%B %-d, %Y at %-I:%M %p")
                dur = closed_at - opened_at
            else:
                c = "Still open"
                dur = now - opened_at

            durations.append(dur)
            embed.add_field(name=f"Opened: {o}", value=f"Closed: {c}", inline=False)

        # 8) average duration
        avg = sum(durations, timedelta()) / len(durations)
        hrs = int(avg.total_seconds() // 3600)
        mins = int((avg.total_seconds() % 3600) // 60)
        embed.add_field(
            name="⏱️ Average Open Duration",
            value=f"{hrs}h {mins}m over {len(durations)} events",
            inline=False
        )

    except Exception as e:
        embed = make_embed("⚠️ Error", f"Could not fetch history: {e}", discord.Color.orange())

    await interaction.followup.send(embed=embed)

# === on_ready with global sync ===
@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Globally synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

# === Flask notifier for backend-initiated DMs ===
notify_app = Flask("notifier")

@notify_app.route("/notify", methods=["POST"])
def notify():
    data = request.json or {}
    user_id = int(data.get("user_id", 0))
    content = data.get("content", "")

    # fetch the user from cache or API
    user = bot.get_user(user_id) or asyncio.run_coroutine_threadsafe(bot.fetch_user(user_id), bot.loop).result(10)
    if not user:
        logging.error(f"User {user_id} not found")
        return "user not found", 404

    try:
        asyncio.run_coroutine_threadsafe(user.send(content), bot.loop).result(10)
        return "ok", 200
    except Exception as e:
        logging.error(f"Failed to DM {user_id}: {e}")
        return f"send failed: {e}", 500

@bot.tree.command(name="testdm", description="Check if I can send you DMs")
async def testdm(interaction: discord.Interaction):
    user = interaction.user
    try:
        await user.send("✅ I can DM you! You’re all set.")
        await interaction.response.send_message("📬 Sent you a DM! If you didn’t get it, check your privacy settings.")
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I can't DM you. Please check your privacy settings:\n"
            "- Add TrackMyClass to my apps, or\n"
            "- Enable DMs from server members in server settings."
        )

def run_notifier():
    notify_app.run(port=5001)

threading.Thread(target=run_notifier, daemon=True).start()

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN not set")
    else:
        bot.run(DISCORD_TOKEN)