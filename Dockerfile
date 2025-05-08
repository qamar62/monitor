FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install ping utility (required by the monitor)
RUN apt-get update && apt-get install -y iputils-ping && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the monitoring script
COPY website_monitor.py .

# Run the monitor script
CMD ["python", "website_monitor.py"]
