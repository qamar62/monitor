# Discord Bot Setup Guide

This guide will help you create a Discord bot and obtain the necessary token for your Five.Tours monitoring system.

## Step 1: Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click on "New Application" in the top right corner
3. Give your application a name (e.g., "Five.Tours Monitor")
4. Click "Create"

## Step 2: Create a Bot User

1. In your application page, click on the "Bot" tab in the left sidebar
2. Click "Add Bot" and confirm by clicking "Yes, do it!"
3. Under the "TOKEN" section, click "Reset Token" and confirm
4. Copy the token that appears - **IMPORTANT**: This token is like a password, don't share it publicly!

## Step 3: Set Bot Permissions

1. Still in the Bot tab, scroll down to "Bot Permissions"
2. Enable the following permissions:
   - Read Messages/View Channels
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
3. Under "Privileged Gateway Intents", enable "Message Content Intent"

## Step 4: Invite the Bot to Your Server

1. Go to the "OAuth2" tab in the left sidebar
2. Click on "URL Generator"
3. Under "Scopes", select "bot"
4. Under "Bot Permissions", select the same permissions as above
5. Copy the generated URL at the bottom
6. Open this URL in a new browser tab
7. Select your server and click "Authorize"

## Step 5: Configure the Monitoring Script

1. Open the `website_monitor.py` file
2. Find the `CONFIG` section
3. Paste your bot token into the `"discord_bot_token"` field:
   ```python
   "discord_bot_token": "YOUR_BOT_TOKEN_HERE",
   ```
4. Make sure the `"discord_channel_id"` matches your channel ID (currently set to 1370003857643536496)

## Step 6: Start the Monitor

Run the monitor using Docker Compose:
```bash
docker-compose up -d
```

## Troubleshooting

If the bot doesn't connect or send messages:

1. **Check the token**: Make sure you've copied the entire token correctly
2. **Verify channel ID**: Ensure the channel ID is correct
3. **Check logs**: Run `docker-compose logs` to see any error messages
4. **Bot permissions**: Verify the bot has permission to see and send messages in the channel
5. **Server settings**: Check that the bot role has proper permissions in your server

## Security Note

Keep your bot token secure - don't commit it to public repositories or share it with others. If you believe your token has been compromised, immediately reset it in the Discord Developer Portal.
