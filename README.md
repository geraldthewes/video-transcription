# Video Transcription Service

A service for transcribing video/audio files using Whisper ASR models. It supports processing audio files from S3 and uploading transcriptions back to S3.

## Features

- Transcribe audio files using Faster Whisper
- Support for S3 storage (both AWS and compatible services)
- Webhook and Consul notifications
- Background job processing
- Health check endpoint

## Architecture

```
Client → API Server → Background Job → S3 Storage
```

## Running with Docker

### Prerequisites

- Docker installed on your system

### Building the Image

```bash
docker build -t video-transcription .
```

### Running the Container

```bash
docker run -d \
  --name video-transcription \
  -p 8000:8000 \
  -e AWS_ACCESS_KEY_ID="your-access-key-id" \
  -e AWS_SECRET_ACCESS_KEY="your-secret-access-key" \
  -e AWS_REGION="us-east-1" \
  -e CONSUL_HOST="localhost" \
  -e CONSUL_PORT="8500" \
  -e APP_HOST="0.0.0.0" \
  -e APP_PORT="8000" \
  video-transcription
```

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `AWS_ACCESS_KEY_ID` | AWS Access Key ID for S3 access | Yes | - |
| `AWS_SECRET_ACCESS_KEY` | AWS Secret Access Key for S3 access | Yes | - |
| `AWS_REGION` | AWS Region for S3 access | No | `us-east-1` |
| `CONSUL_HOST` | Host for Consul service | No | `localhost` |
| `CONSUL_PORT` | Port for Consul service | No | `8500` |
| `APP_HOST` | Host for the application | No | `0.0.0.0` |
| `APP_PORT` | Port for the application | No | `8000` |
| `S3_ENDPOINT` | Custom S3 endpoint URL (for non-AWS S3) | No | - |

### Using with Custom S3 Endpoint

To use with a custom S3-compatible service (like MinIO):

```bash
docker run -d \
  --name video-transcription \
  -p 8000:8000 \
  -e AWS_ACCESS_KEY_ID="your-access-key-id" \
  -e AWS_SECRET_ACCESS_KEY="your-secret-access-key" \
  -e S3_ENDPOINT="http://minio:9000" \
  -e AWS_REGION="us-east-1" \
  video-transcription
```

## API Endpoints

Auto generated API [documentation](docs/README.md)

### POST /transcribe

Initiates a transcription job.

**Request Body:**
```json
{
  "input_s3_path": "bucket-name/object-key",
  "output_s3_path": "bucket-name/object-key",
  "webhook_url": "https://example.com/webhook",
  "consul_notification": true
}
```

**Response:**
```json
{
  "job_id": "job-uuid",
  "consul_key": "services/video-transcription/job-uuid"
}
```

### GET /status/{job_id}

Gets the status of a transcription job.

**Response:**
```json
{
  "status": "completed",
  "result": {
    "output_s3_path": "bucket-name/object-key"
  }
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

## Development

### Running Locally

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_REGION="us-east-1"
```

3. Run the application:
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Using the Transcribe Script

The `scripts/transcribe.py` script provides a command-line interface for transcribing audio files from S3 by calling the transcription service API.

#### Usage

```bash
python scripts/transcribe.py --service-url "fabio.service.consul:9999" --input-s3-path "s3://bucket-name/input-file.mp3" --output-s3-path "s3://bucket-name/output-file.txt"
```

#### Requirements

Install the required packages:
```bash
pip install -r scripts/requirements.txt
```

#### Features

- Makes HTTP request to transcription service API
- Waits for job completion using Consul callback pattern
- Reports job ID, success/failure status, and elapsed time
- Supports optional webhook and consul key parameters
- Handles service URLs with load balancer configurations
- Includes debug mode for troubleshooting

#### Troubleshooting

If you encounter import errors, make sure you're running the script from the project root directory:
```bash
cd /media/gerald/SSDT71/gerald/video-transcription
python scripts/transcribe.py --help
```

#### Debug Mode

Use the `--debug` or `-d` flag to enable detailed logging of HTTP requests and responses:
```bash
python scripts/transcribe.py --debug --service-url "fabio.service.consul:9999" --input-s3-path "s3://bucket-name/input-file.mp3" --output-s3-path "s3://bucket-name/output-file.txt"
```

#### Service URL Format

The script accepts service URLs in various formats:
- Standard: `http://localhost:8000`
- Without scheme: `fabio.service.consul:9999`
- With path: `fabio.service.consul:9999/transcribe`

The script automatically normalizes URLs to ensure proper API endpoint construction.

## License

MIT

## Documentation Fix

When running behind a load balancer that prefixes all routes with `/transcribe`, the OpenAPI documentation endpoints (`/openapi.json`, `/docs`, `/redoc`) may not be accessible due to incorrect path resolution.

To fix this issue, the application now properly handles path prefixes by:

1. Setting the `ROOT_PATH` environment variable to `/transcribe`
2. Configuring FastAPI to use the correct paths for documentation endpoints
3. Ensuring that all API endpoints maintain their correct paths

This allows the documentation to be accessible at:
- `http://fabio.service.consul:9999/transcribe/docs`
- `http://fabio.service.consul:9999/transcribe/redoc`
- `http://fabio.service.consul:9999/transcribe/openapi.json`
