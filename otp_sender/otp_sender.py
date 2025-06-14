import os
import sys
import time
import logging
import threading
import requests
import traceback
import base64
from urllib.parse import urlparse, parse_qs
from pyzbar.pyzbar import decode
from PIL import Image
import pyotp

# Configure logging with explicit file handling
log_file = 'otp_sender.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Ensure logs are written immediately
logging.getLogger().handlers[0].flush = sys.stdout.flush

# Global configuration
CONFIG = {
    'MAX_RETRIES': 3,
    'TIMEOUT': 10,
    'RETRY_DELAY': 3,
    'FALLBACK_METHOD': 'print'
}

# Global flag to control the OTP generation loop
running = False

# Get the absolute path of the QR code file
QR_CODE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qrcode.jpg')

def log_and_print(message, level='info'):
    """Log message and print to console"""
    print(message)
    if level == 'info':
        logging.info(message)
    elif level == 'error':
        logging.error(message)
    elif level == 'warning':
        logging.warning(message)
    
    # Explicitly flush the log file
    logging.getLogger().handlers[0].flush()

def fallback_send_otp(message):
    """Send OTP using alternative methods"""
    try:
        log_and_print(f"FALLBACK MESSAGE: {message}")
        
        # Write to file
        with open('otp_fallback.txt', 'a') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception as e:
        log_and_print(f"Fallback sending failed: {e}", 'error')

def send_telegram_message(bot_token, chat_id, message):
    """Send Telegram message with error handling"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    for attempt in range(CONFIG['MAX_RETRIES']):
        try:
            log_and_print(f"Telegram Message Sending - Attempt {attempt + 1}")
            
            response = requests.post(
                url, 
                json={'chat_id': chat_id, 'text': message},
                timeout=CONFIG['TIMEOUT']
            )
            
            log_and_print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                response_json = response.json()
                if response_json.get('ok', False):
                    log_and_print("Message sent successfully")
                    return True
                else:
                    log_and_print(f"Telegram API returned error: {response_json}", 'warning')
            else:
                log_and_print(f"HTTP Error: {response.status_code}", 'error')
        
        except requests.exceptions.RequestException as req_err:
            log_and_print(f"Network Request Error: {req_err}", 'error')
        
        except Exception as e:
            log_and_print(f"Unexpected Error: {e}", 'error')
        
        # Wait before retry
        time.sleep(CONFIG['RETRY_DELAY'])
    
    # Fallback if all attempts fail
    fallback_send_otp(message)
    return False

def read_qr_code(file_path):
    """Read secret from QR code"""
    try:
        log_and_print(f"Reading QR code from: {file_path}")
        
        image = Image.open(file_path)
        decoded_objects = decode(image)
        
        if not decoded_objects:
            log_and_print("No QR codes found in the image", 'error')
            return None
        
        for obj in decoded_objects:
            uri = obj.data.decode('utf-8')
            log_and_print(f"Full QR Code URI: {uri}")
            
            parsed_uri = urlparse(uri)
            query_params = parse_qs(parsed_uri.query)
            
            if 'secret' in query_params:
                secret = query_params['secret'][0]
                log_and_print(f"Extracted Secret: {secret}")
                return secret
        
        log_and_print("No secret found in QR code", 'error')
        return None
    
    except Exception as e:
        log_and_print(f"QR Code Reading Error: {e}", 'error')
        return None

def get_updates(bot_token, offset=None):
    """Get updates from Telegram"""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params = {'timeout': 30}  # Long polling waits up to 30 seconds
    if offset:
        params['offset'] = offset

    try:
        # INCREASE timeout from CONFIG['TIMEOUT'] to a higher value like 40
        response = requests.get(url, params=params, timeout=40)
        return response.json()
    except requests.exceptions.ReadTimeout:
        # Timeout is expected sometimes during long polling
        log_and_print("Telegram long-polling timed out (harmless). Retrying...", 'warning')
        return None
    except Exception as e:
        log_and_print(f"Error getting updates: {e}", 'error')
        return None
def generate_and_send_otp(secret, bot_token, chat_id):
    """Generate and send a single OTP"""
    try:
        totp = pyotp.TOTP(secret)
        otp = totp.now()
        log_and_print(f"Generated OTP: {otp}")
        
        # Send OTP via Telegram
        send_telegram_message(bot_token, chat_id, f"Your OTP is: {otp}")
    except Exception as e:
        log_and_print(f"OTP Generation/Sending Error: {e}", 'error')

def main():
    log_and_print("Starting OTP Sender")
    
    bot_token = '7753763767:AAHSfbg1sHNsF2zfh-5j5yNoA464LaAHNuk'
    chat_id = '-4613085263'
    
    # Read QR code
    secret = read_qr_code(QR_CODE_FILE)
    if not secret:
        log_and_print("QR Code reading failed", 'error')
        return
    
    # Validate secret
    try:
        base64.b32decode(secret.upper())
    except Exception as e:
        log_and_print(f"Invalid secret: {e}", 'error')
        return
    
    log_and_print("OTP Sender is running. Waiting for /getotp command in the group...")
    
    last_update_id = None
    try:
        while True:
            updates = get_updates(bot_token, last_update_id)
            if updates and updates.get('ok'):
                for update in updates['result']:
                    last_update_id = update['update_id'] + 1
                    
                    # Check if message is from the configured group
                    if 'message' in update and 'chat' in update['message']:
                        message = update['message']
                        if str(message['chat']['id']) == str(chat_id):
                            if 'text' in message and message['text'].lower() == '/getotp':
                                generate_and_send_otp(secret, bot_token, chat_id)
            
            time.sleep(1)
    except KeyboardInterrupt:
        log_and_print("OTP Sender Stopped")

if __name__ == "__main__":
    main()
