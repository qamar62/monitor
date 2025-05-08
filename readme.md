# Five.Tours Website Monitor

A Docker-based monitoring system for the Five.Tours website that sends alerts to Discord when the site status changes.

## Features

- Regular website availability monitoring
- HTTP status code checking
- Response time monitoring
- Server ping checks
- Discord bot integration for status notifications
- Downtime tracking and reporting
- Containerized solution for easy deployment

## Setup Instructions

### 1. Create a Discord Bot

Follow the detailed instructions in the [Discord Bot Setup Guide](Discord%20Bot%20Setup%20Guide.md) to:
- Create a Discord application
- Set up a bot user
- Get your bot token
- Add the bot to your server

### 2. Configure the Monitor

Edit the `website_monitor.py` file and update the `CONFIG` section:

```python
CONFIG = {
    "website_url": "https://five.tours",
    "server_ip": "165.154.245.246",
    "check_interval": 60,  # seconds
    "discord_bot_token": "YOUR_BOT_TOKEN_HERE",  # Paste your Discord bot token here
    "discord_channel_id": 1370003857643536496,  # Your channel ID (update if needed)
    "timeout": 10,  # Request timeout in seconds
    "ping_count": 3,  # Number of ping attempts
    "log_file": "website_monitor.log",
    "status_file": "status_history.json"
}
```

### 3. Build and Run with Docker

```bash
# Create a logs directory
mkdir -p logs

# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f
```

## Monitoring Information

The system will check your website every minute (configurable) and send Discord notifications when:

- The website goes down
- The website comes back online
- The website experiences degraded performance

### Status Types

- **ONLINE**: Website is fully operational
- **OFFLINE**: Website is completely down
- **DEGRADED**: Website is responding but with issues (high latency or non-200 status codes)

## File Structure

- `website_monitor.py` - The main monitoring script with Discord bot integration
- `Dockerfile` - Instructions for building the Docker image
- `docker-compose.yml` - Compose file for easy deployment
- `requirements.txt` - Python dependencies
- `logs/` - Directory for log files
- `status_history.json` - JSON file storing historical status data

## Customization

You can customize the monitoring behavior by editing the `CONFIG` dictionary in `website_monitor.py`:

- `check_interval`: How frequently to check the website (in seconds)
- `timeout`: How long to wait for HTTP responses
- `ping_count`: Number of ICMP ping attempts

## Troubleshooting

If you're not receiving Discord notifications:
1. Check that your bot token is correct
2. Verify the channel ID is correct
3. Check the container logs: `docker-compose logs`
4. Ensure your bot has proper permissions in the channel
5. Make sure the bot is online in your Discord server

## License

This project is provided as-is for your personal use.