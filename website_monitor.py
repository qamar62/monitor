import requests
import time
import datetime
import os
import logging
import json
import discord
from discord.ext import tasks
import asyncio
import socket

# Configuration
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

CONFIG = {
    "website_url": "https://five.tours",
    "server_ip": "165.154.245.246",
    "check_interval": 60,  # seconds
    "discord_bot_token": os.getenv("DISCORD_BOT_TOKEN", ""),
    "discord_channel_id": int(os.getenv("DISCORD_CHANNEL_ID", "1370003857643536496")),
    "timeout": 10,  # Request timeout in seconds
    "log_file": "website_monitor.log",
    "status_file": "status_history.json"
}

# Setup logging
logging.basicConfig(
    filename=CONFIG["log_file"],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)
logger = logging.getLogger('')

# Status codes
class Status:
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"

# Initialize Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
channel = None

@client.event
async def on_ready():
    """Called when the Discord bot is ready"""
    global channel
    logger.info(f'Logged in as {client.user}')
    
    # Get the channel object
    try:
        channel = client.get_channel(CONFIG["discord_channel_id"])
        if not channel:
            logger.error(f"Could not find channel with ID {CONFIG['discord_channel_id']}")
            logger.info("Available channels:")
            for guild in client.guilds:
                logger.info(f"Guild: {guild.name}")
                for ch in guild.channels:
                    logger.info(f"  - {ch.name} (ID: {ch.id})")
        else:
            logger.info(f"Connected to Discord channel: {channel.name}")
            
            # Test if we can send a message
            try:
                await channel.send("🟢 Five.Tours monitoring bot is now online and monitoring your website!")
                logger.info("Successfully sent test message to channel")
            except Exception as e:
                logger.error(f"Error sending message to channel: {e}")
                logger.error("Bot may not have permission to send messages in this channel")
    except Exception as e:
        logger.error(f"Error setting up Discord channel: {e}")
    
    # Start the monitoring task
    monitor_task.start()

def load_status_history():
    """Load the status history file if it exists"""
    try:
        if os.path.exists(CONFIG["status_file"]):
            with open(CONFIG["status_file"], "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading status history: {e}")
    
    return {
        "last_status": Status.UNKNOWN,
        "last_check": None,
        "downtime_started": None,
        "total_downtime": 0,
        "incidents": []
    }

def save_status_history(history):
    """Save the status history to a file"""
    try:
        with open(CONFIG["status_file"], "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving status history: {e}")

async def ping_server_async(host, timeout=2):
    """Ping the server using async sockets instead of subprocess to avoid blocking"""
    try:
        # Create a socket connection to test if server is reachable
        # This is more reliable in Docker than using subprocess ping
        start_time = time.time()
        
        future = asyncio.open_connection(host, 80)
        try:
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return True, f"Connection successful in {time.time() - start_time:.2f}s"
        except asyncio.TimeoutError:
            return False, f"Connection timeout after {timeout}s"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

def check_http_status(url):
    """Check the HTTP status of the website"""
    try:
        response = requests.get(url, timeout=CONFIG["timeout"])
        return response.status_code, response.elapsed.total_seconds(), response.text
    except requests.exceptions.RequestException as e:
        return None, None, str(e)

async def check_website():
    """Check website availability and performance"""
    logger.info(f"Checking website: {CONFIG['website_url']}")
    
    # First check - HTTP request
    status_code, response_time, error_text = check_http_status(CONFIG["website_url"])
    
    # Second check - server connection (async version)
    ping_success, ping_output = await ping_server_async(CONFIG["server_ip"])
    
    # Determine overall status based on both checks
    if status_code and 200 <= status_code < 300 and ping_success:
        current_status = Status.ONLINE
    elif status_code and 200 <= status_code < 300 and not ping_success:
        current_status = Status.DEGRADED
    elif status_code and status_code >= 300:
        current_status = Status.DEGRADED
    else:
        current_status = Status.OFFLINE
    
    # Additional data to include in reports
    details = {
        "status_code": status_code,
        "response_time": response_time,
        "ping_successful": ping_success,
        "ping_output": ping_output,
        "timestamp": datetime.datetime.now().isoformat(),
        "error_text": error_text if not status_code else None
    }
    
    return current_status, details

def format_duration(seconds):
    """Format seconds into a human-readable duration string"""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        if minutes > 0:
            return f"{hours} hour{'s' if hours != 1 else ''} and {minutes} minute{'s' if minutes != 1 else ''}"
        return f"{hours} hour{'s' if hours != 1 else ''}"

async def send_discord_notification(status, details, history):
    """Send a notification to Discord about the website status"""
    global channel
    
    if not channel:
        logger.warning("Discord channel not available. Skipping notification.")
        return False
    
    try:
        # Create the embed based on status
        if status == Status.ONLINE and history["last_status"] != Status.ONLINE:
            # Site recovered
            embed = discord.Embed(
                title="✅ Website is ONLINE",
                description=f"{CONFIG['website_url']} is back online!",
                color=0x00FF00  # Green
            )
            
            # Add downtime information if we have it
            if history["downtime_started"]:
                downtime_duration = time.time() - history["downtime_started"]
                embed.add_field(
                    name="Downtime Duration", 
                    value=format_duration(downtime_duration),
                    inline=False
                )
        
        elif status == Status.OFFLINE and history["last_status"] != Status.OFFLINE:
            # Site went down
            embed = discord.Embed(
                title="❌ Website is DOWN",
                description=f"{CONFIG['website_url']} is not responding!",
                color=0xFF0000  # Red
            )
            
            # Add error details
            if details.get("error_text"):
                error_preview = details["error_text"][:100] + "..." if len(details["error_text"]) > 100 else details["error_text"]
                embed.add_field(name="Error", value=f"```{error_preview}```", inline=False)
        
        elif status == Status.DEGRADED and history["last_status"] != Status.DEGRADED:
            # Site is having issues
            embed = discord.Embed(
                title="⚠️ Website Performance Issues",
                description=f"{CONFIG['website_url']} is experiencing degraded performance.",
                color=0xFFA500  # Orange
            )
            
            # Add degradation details
            if details.get("ping_output") and not details.get("ping_successful"):
                embed.add_field(name="Connection Issue", value=details["ping_output"], inline=False)
        
        else:
            # No status change, don't send notification
            return True
        
        # Add common fields
        embed.add_field(name="Server IP", value=CONFIG["server_ip"])
        
        if details.get("status_code"):
            embed.add_field(name="HTTP Status", value=str(details["status_code"]))
        
        if details.get("response_time"):
            embed.add_field(name="Response Time", value=f"{details['response_time']:.2f}s")
        
        embed.add_field(name="Connection Test", value="Successful" if details.get("ping_successful") else "Failed")
        embed.timestamp = datetime.datetime.now()
        
        # Add footer
        embed.set_footer(text="Five.Tours Monitoring System")
        
        # Send the notification
        await channel.send(embed=embed)
        logger.info(f"Discord notification sent. Status: {status}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")
        return False

def update_status_history(status, details, history):
    """Update the status history with the new status"""
    current_time = time.time()
    
    # If transitioning from OFFLINE/UNKNOWN to ONLINE, calculate downtime
    if status == Status.ONLINE and (history["last_status"] == Status.OFFLINE or history["last_status"] == Status.UNKNOWN):
        if history["downtime_started"]:
            downtime = current_time - history["downtime_started"]
            history["total_downtime"] += downtime
            
            # Record the incident
            history["incidents"].append({
                "start_time": datetime.datetime.fromtimestamp(history["downtime_started"]).isoformat(),
                "end_time": datetime.datetime.fromtimestamp(current_time).isoformat(),
                "duration_seconds": downtime,
                "duration_formatted": format_duration(downtime),
                "recovery_details": details
            })
            
            # Reset downtime tracking
            history["downtime_started"] = None
    
    # If transitioning to OFFLINE, start tracking downtime
    elif status == Status.OFFLINE and history["last_status"] != Status.OFFLINE:
        history["downtime_started"] = current_time
    
    # Update the last status and check time
    history["last_status"] = status
    history["last_check"] = current_time
    
    return history

@tasks.loop(seconds=CONFIG["check_interval"])
async def monitor_task():
    """Regular task to check website status"""
    # Load status history
    history = load_status_history()
    
    try:
        # Check website status
        status, details = await check_website()
        
        # Log status
        logger.info(f"Status: {status}")
        if details.get("status_code"):
            logger.info(f"HTTP Status Code: {details['status_code']}")
        if details.get("response_time"):
            logger.info(f"Response Time: {details['response_time']:.2f}s")
        
        # Update status history
        history = update_status_history(status, details, history)
        save_status_history(history)
        
        # Send notifications if needed
        await send_discord_notification(status, details, history)
    
    except Exception as e:
        logger.error(f"Monitoring error: {e}")
        # Try to send an alert about the monitor itself failing
        try:
            if channel:
                await channel.send(f"⚠️ **ALERT**: The monitoring system has encountered an error: {e}")
        except:
            pass

def run_monitor():
    """Main function to run the monitor"""
    logger.info("Starting website monitoring service")
    logger.info(f"Monitoring {CONFIG['website_url']} (Server IP: {CONFIG['server_ip']})")
    logger.info(f"Check interval: {CONFIG['check_interval']} seconds")
    
    # Check if Discord bot token is configured
    if not CONFIG["discord_bot_token"]:
        logger.warning("Discord bot token not set. Please update the CONFIG in the script.")
        print("\n⚠️  Please set your Discord bot token in the CONFIG section of the script.")
        print("    You can create a bot at https://discord.com/developers/applications\n")
        return
    
    # Start the Discord client
    try:
        client.run(CONFIG["discord_bot_token"])
    except Exception as e:
        logger.error(f"Failed to start Discord client: {e}")
        print(f"\n❌ Error starting Discord client: {e}")
        print("  Please check your bot token and ensure it has proper permissions.\n")

if __name__ == "__main__":
    run_monitor()