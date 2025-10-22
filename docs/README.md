# Documentation for Video Transcription Service

<a name="documentation-for-api-endpoints"></a>
## Documentation for API Endpoints

All URIs are relative to */transcribe*

| Class | Method | HTTP request | Description |
|------------ | ------------- | ------------- | -------------|
| *DefaultApi* | [**healthCheckHealthGet**](Apis/DefaultApi.md#healthCheckHealthGet) | **GET** /health | Health Check |
*DefaultApi* | [**statusStatusJobIdGet**](Apis/DefaultApi.md#statusStatusJobIdGet) | **GET** /status/{job_id} | Status |
*DefaultApi* | [**transcribeTranscribePost**](Apis/DefaultApi.md#transcribeTranscribePost) | **POST** /transcribe | Transcribe |


<a name="documentation-for-models"></a>
## Documentation for Models

 - [HTTPValidationError](./Models/HTTPValidationError.md)
 - [TranscriptionRequest](./Models/TranscriptionRequest.md)
 - [ValidationError](./Models/ValidationError.md)
 - [ValidationError_loc_inner](./Models/ValidationError_loc_inner.md)


<a name="documentation-for-authorization"></a>
## Documentation for Authorization

All endpoints do not require authorization.
