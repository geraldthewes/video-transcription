import os

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Consul Configuration
CONSUL_HOST = os.getenv("CONSUL_HOST", "localhost")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", 8500))

# Application Configuration
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", 8000))
ROOT_PATH = os.getenv("ROOT_PATH", "")
