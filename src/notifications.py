import requests
import consul
import logging

from src.config import CONSUL_HOST, CONSUL_PORT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_webhook_notification(url, data):
    """Sends a POST request to the specified webhook URL."""
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        logger.info(f"Webhook notification sent to {url}.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send webhook notification: {e}")
        return False

def send_consul_notification(key, value):
    """Sends a notification to Consul by updating a key-value pair."""
    try:
        c = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)
        c.kv.put(key, value)
        logger.info(f"Consul notification sent for key {key}.")
        return True
    except consul.ConsulException as e:
        logger.error(f"Consul error when sending notification: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error when sending Consul notification: {e}")
        return False
