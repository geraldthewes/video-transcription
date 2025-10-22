# DefaultApi

All URIs are relative to */transcribe*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**healthCheckHealthGet**](DefaultApi.md#healthCheckHealthGet) | **GET** /health | Health Check |
| [**statusStatusJobIdGet**](DefaultApi.md#statusStatusJobIdGet) | **GET** /status/{job_id} | Status |
| [**transcribeTranscribePost**](DefaultApi.md#transcribeTranscribePost) | **POST** /transcribe | Transcribe |


<a name="healthCheckHealthGet"></a>
# **healthCheckHealthGet**
> oas_any_type_not_mapped healthCheckHealthGet()

Health Check

### Parameters
This endpoint does not need any parameter.

### Return type

[**oas_any_type_not_mapped**](../Models/AnyType.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

<a name="statusStatusJobIdGet"></a>
# **statusStatusJobIdGet**
> oas_any_type_not_mapped statusStatusJobIdGet(job\_id)

Status

### Parameters

|Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **job\_id** | **String**|  | [default to null] |

### Return type

[**oas_any_type_not_mapped**](../Models/AnyType.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

<a name="transcribeTranscribePost"></a>
# **transcribeTranscribePost**
> oas_any_type_not_mapped transcribeTranscribePost(TranscriptionRequest)

Transcribe

### Parameters

|Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **TranscriptionRequest** | [**TranscriptionRequest**](../Models/TranscriptionRequest.md)|  | |

### Return type

[**oas_any_type_not_mapped**](../Models/AnyType.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

