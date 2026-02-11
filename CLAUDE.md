# Video Transcription Service - Agent Instructions

## Project Overview

A FastAPI service that transcribes video/audio files using Faster Whisper ASR models. Files are read from and written to S3-compatible storage. The service runs on GPU nodes in a Nomad cluster behind a Fabio load balancer.

## Architecture

```
Client -> Fabio LB (/transcribe) -> FastAPI Service -> Background Job -> S3 Storage
```

- **Entry point:** `src/main.py`
- **Key modules:**
  - `src/config.py` - Environment configuration
  - `src/transcription.py` - Whisper transcription logic
  - `src/s3.py` - S3 file operations
  - `src/jobs.py` - Job status management
  - `src/notifications.py` - Webhook and Consul notifications

## Build and Deploy

Uses jobforge for building and Nomad for deployment:

```bash
# Build and push Docker image
make build

# Deploy to Nomad cluster
make deploy
```

Build configuration is in `deploy/build.yaml`. The service uses `Dockerfile.gpu` for GPU support.

## Running Integration Tests

### Against Deployed Service

The integration test submits a real transcription job and polls until completion:

```bash
python tests/test.py
```

This tests against the deployed service at `http://fabio.service.consul:9999/transcribe`.

You can also configure the target via environment variables:
- `SERVICE_HOST` - Host of the service
- `SERVICE_PORT` - Port (default: 9999)
- `SERVICE_PREFIX` - URL prefix (default: none)

### Health Check

Verify the deployed service is running:

```bash
curl http://fabio.service.consul:9999/transcribe/health
```

### Test Data

Integration tests use:
- Input: `s3://ai-storage/transcriber/tests/test001.mp4`
- Output: `s3://ai-storage/transcriber/tests/output001.md`

## API Endpoints

All endpoints are prefixed with `/transcribe` when accessed via the load balancer.

- `POST /transcribe` - Submit transcription job
- `GET /status/{job_id}` - Get job status
- `GET /health` - Health check

## Environment Variables

Key configuration (see README.md for full list):
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` - S3 credentials
- `S3_ENDPOINT` - Custom S3 endpoint (for non-AWS)
- `ROOT_PATH` - URL prefix for load balancer (set to `/transcribe` in production)
- `LOG_LEVEL` - Logging verbosity (default: INFO)

## Development Notes

- The service requires GPU for transcription (uses CUDA)
- Secrets are managed via Vault (see `deploy/build.yaml` for vault policies)
- When running behind Fabio, the `ROOT_PATH` must match the route prefix
- The Makefile `test-poll` and `test-consul` targets have import issues; use `python tests/test.py` instead
