# RAG Chatbot API Documentation

This document provides comprehensive API documentation for the RAG Chatbot system.

## Base URLs

- **Interface Layer**: `http://localhost:5000`
- **AI Backend**: `http://localhost:8000`
- **Frontend**: `http://localhost:3000`

## Authentication

Currently, the API does not require authentication. In production, implement proper authentication mechanisms.

## Rate Limiting

- **Default**: 100 requests per minute per IP
- **Chat Endpoints**: 50 requests per minute per IP
- **File Upload**: 10 requests per minute per IP

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": "Error message",
  "status_code": 400,
  "path": "/api/endpoint"
}
```

## Interface Layer API

### Health Check

#### GET /health

Check service health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "uptime": 3600
}
```

### Document Management

#### POST /api/upload

Upload and process a document.

**Request:**
- **Content-Type**: `multipart/form-data`
- **Body**: File upload with field name `file`

**Supported Formats:**
- PDF (.pdf)
- Text (.txt)
- Word Document (.docx)

**Response:**
```json
{
  "message": "Document uploaded and processed successfully",
  "upload_id": "uuid-string",
  "filename": "document.pdf",
  "chunks_created": 25
}
```

**Error Responses:**
- `400`: No file uploaded or invalid file type
- `413`: File too large (>10MB)
- `500`: Processing failed

#### GET /api/documents

Get list of processed documents.

**Response:**
```json
{
  "documents": [
    {
      "id": 1,
      "filename": "document.pdf",
      "file_size": 1024000,
      "content_type": "application/pdf",
      "chunks_count": 25,
      "upload_date": "2024-01-01T00:00:00Z",
      "metadata": "{\"upload_id\": \"uuid\"}"
    }
  ]
}
```

#### DELETE /api/documents/{id}

Delete a document and its chunks.

**Response:**
```json
{
  "message": "Document deleted successfully"
}
```

**Error Responses:**
- `404`: Document not found
- `500`: Deletion failed

### Chat API

#### POST /api/chat

Send a chat message and get AI response.

**Request:**
```json
{
  "message": "What is the main topic of the document?",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "answer": "The main topic of the document is...",
  "sources": ["document.pdf", "report.docx"],
  "response_time": 1.234,
  "session_id": "session-id"
}
```

**Error Responses:**
- `400`: Empty message or message too long
- `500`: Processing failed

#### GET /api/chat/history/{session_id}

Get chat history for a session.

**Query Parameters:**
- `limit` (optional): Number of messages to return (default: 50)

**Response:**
```json
{
  "history": [
    {
      "id": 1,
      "message_type": "user",
      "content": "What is the main topic?",
      "sources": null,
      "created_at": "2024-01-01T00:00:00Z",
      "response_time": null
    },
    {
      "id": 2,
      "message_type": "assistant",
      "content": "The main topic is...",
      "sources": "[\"document.pdf\"]",
      "created_at": "2024-01-01T00:00:01Z",
      "response_time": 1.234
    }
  ]
}
```

#### DELETE /api/chat/session/{session_id}

Clear chat session and history.

**Response:**
```json
{
  "message": "Session cleared successfully"
}
```

## AI Backend API

### Health Check

#### GET /api/health

Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "service": "rag-chatbot-ai-backend",
  "version": "1.0.0"
}
```

#### GET /api/health/detailed

Detailed health check with service dependencies.

**Response:**
```json
{
  "status": "healthy",
  "service": "rag-chatbot-ai-backend",
  "version": "1.0.0",
  "checks": {
    "database": "healthy",
    "vector_db": "healthy",
    "vector_db_documents": 150
  }
}
```

### Document Processing

#### POST /api/documents/upload

Upload and process document (internal endpoint).

**Request:**
- **Content-Type**: `multipart/form-data`
- **Body**: File upload

**Response:**
```json
{
  "upload_id": "uuid-string",
  "filename": "document.pdf",
  "chunks_created": 25,
  "processing_time": 5.678
}
```

#### GET /api/documents

Get processed documents (internal endpoint).

**Response:**
```json
{
  "documents": [
    {
      "id": 1,
      "filename": "document.pdf",
      "chunks_count": 25,
      "upload_date": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### DELETE /api/documents/{id}

Delete document (internal endpoint).

**Response:**
```json
{
  "message": "Document deleted successfully"
}
```

### Chat Processing

#### POST /api/chat

Process chat message (internal endpoint).

**Request:**
```json
{
  "message": "What is the main topic?",
  "session_id": "session-id"
}
```

**Response:**
```json
{
  "answer": "The main topic is...",
  "sources": ["document.pdf"],
  "response_time": 1.234,
  "session_id": "session-id"
}
```

#### POST /api/chat/stream

Process chat message with streaming (internal endpoint).

**Request:**
```json
{
  "message": "What is the main topic?",
  "session_id": "session-id"
}
```

**Response:**
```json
{
  "answer": "The main topic is...",
  "sources": ["document.pdf"],
  "response_time": 1.234,
  "session_id": "session-id"
}
```

## WebSocket API

### Connection

Connect to WebSocket at: `ws://localhost:5000`

### Events

#### Client Events

**message**
```json
{
  "content": "What is the main topic?",
  "session_id": "optional-session-id"
}
```

**typing**
```json
{
  "is_typing": true
}
```

#### Server Events

**message**
```json
{
  "id": "message-id",
  "content": "The main topic is...",
  "sources": ["document.pdf"],
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**error**
```json
{
  "message": "Error message"
}
```

**system**
```json
{
  "type": "heartbeat",
  "timestamp": "2024-01-01T00:00:00Z",
  "connected_clients": 5
}
```

## Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request |
| 404 | Not Found |
| 413 | Payload Too Large |
| 422 | Validation Error |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

## Rate Limiting Headers

When rate limiting is applied, the following headers are included:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Pagination

For endpoints that return lists, pagination is supported:

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 50)

**Response Headers:**
```
X-Total-Count: 150
X-Page: 1
X-Per-Page: 50
X-Total-Pages: 3
```

## Filtering and Sorting

Some endpoints support filtering and sorting:

**Query Parameters:**
- `filter`: Filter criteria (JSON string)
- `sort`: Sort field and direction (e.g., `created_at:desc`)
- `search`: Search term

**Example:**
```
GET /api/documents?filter={"content_type":"application/pdf"}&sort=upload_date:desc&search=report
```

## Webhooks

Webhook support for document processing events:

**Configuration:**
```json
{
  "webhook_url": "https://your-app.com/webhook",
  "events": ["document.uploaded", "document.processed", "document.failed"]
}
```

**Webhook Payload:**
```json
{
  "event": "document.processed",
  "data": {
    "upload_id": "uuid",
    "filename": "document.pdf",
    "chunks_created": 25
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## SDK Examples

### JavaScript/Node.js

```javascript
// Upload document
const formData = new FormData();
formData.append('file', file);

const response = await fetch('/api/upload', {
  method: 'POST',
  body: formData
});

// Send chat message
const chatResponse = await fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: 'What is the main topic?',
    session_id: 'my-session'
  })
});

// WebSocket connection
const socket = io('ws://localhost:5000');
socket.emit('message', {
  content: 'Hello',
  session_id: 'my-session'
});
```

### Python

```python
import requests
import websocket

# Upload document
with open('document.pdf', 'rb') as f:
    response = requests.post('/api/upload', files={'file': f})

# Send chat message
response = requests.post('/api/chat', json={
    'message': 'What is the main topic?',
    'session_id': 'my-session'
})

# WebSocket connection
def on_message(ws, message):
    print(message)

ws = websocket.WebSocketApp('ws://localhost:5000', on_message=on_message)
ws.run_forever()
```

### cURL Examples

```bash
# Health check
curl http://localhost:5000/health

# Upload document
curl -X POST -F "file=@document.pdf" http://localhost:5000/api/upload

# Send chat message
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the main topic?", "session_id": "my-session"}' \
  http://localhost:5000/api/chat

# Get chat history
curl http://localhost:5000/api/chat/history/my-session
```

## Testing

### Postman Collection

Import the provided Postman collection for easy API testing:

```json
{
  "info": {
    "name": "RAG Chatbot API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/health",
          "host": ["{{base_url}}"],
          "path": ["health"]
        }
      }
    }
  ]
}
```

### API Testing Scripts

```bash
# Run API tests
npm test

# Run load tests
k6 run tests/load-test.js

# Run WebSocket tests
k6 run tests/websocket-test.js
```

## Changelog

### Version 1.0.0
- Initial API release
- Document upload and processing
- Chat functionality
- WebSocket support
- Health checks
- Rate limiting

## Support

For API support and questions:

1. Check the health endpoints
2. Review error responses
3. Check rate limiting headers
4. Contact the development team
