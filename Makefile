.PHONY: build deploy test


build:
	jobforge submit-job --image-tags "latest" --watch deploy/build.yaml


deploy:
	nomad job run nomad/video-transcription.hcl


INPUT_FILE='s3://ai-storage/transcriber/tests/test001.mp4'
OUTPUT_FILE='s3://ai-storage/transcriber/tests/outpu001.md'

test: test-poll test-consul

test-poll:
	python scripts/transcribe.py -d --service-url fabio.service.consul:9999/transcribe --input-s3-path $(INPUT_FILE)  --output-s3-path $(OUTPUT_FILE) 


test-consul:
	python scripts/transcribe.py -d --service-url fabio.service.consul:9999/transcribe --wait consul --input-s3-path $(INPUT_FILE)  --output-s3-path $(OUTPUT_FILE) 
