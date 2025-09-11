# Theorem Ingestor API Endpoints

## Base URL
```
http://localhost:8000/ingestor
```

## Available Endpoints

### 1. Health Check
- **Method**: `GET`
- **Path**: `/health`
- **Description**: Check service health status
- **Response**: `HealthResponse`

### 2. Service Statistics
- **Method**: `GET`
- **Path**: `/service_stats`
- **Description**: Get service statistics including collections count, vectors count, embedder status
- **Response**: `ServiceStats`

### 3. List Collections
- **Method**: `GET`
- **Path**: `/list_collections`
- **Description**: Get list of all available collections with document names
- **Response**: `ListCollectionsResponse`
- **Example Response**:
  ```json
  {
    "collections": [
      {
        "name": "docs_active",
        "status": "active",
        "documents": ["document1", "document2"]
      },
      {
        "name": "fipi_documents", 
        "status": "active",
        "documents": ["first", "second"]
      }
    ],
    "total_collections": 2,
    "status": "success"
  }
  ```

### 4. Get Document Info
- **Method**: `GET`
- **Path**: `/get_document_info/{doc_id}`
- **Query Parameters**:
  - `collection_name` (optional): Collection name
- **Description**: Get document information including chunks count
- **Response**: `GetDocumentResponse`

### 5. Get Document Embedded Vectors
- **Method**: `GET`
- **Path**: `/get_document_embedded/{doc_id}`
- **Query Parameters**:
  - `collection_name` (optional): Collection name
- **Description**: Get document embedded vectors
- **Response**: `{"doc_id": str, "vectors": List[List[float]], "vector_count": int, "status": str}`

### 6. Get Document Text
- **Method**: `GET`
- **Path**: `/get_document_text/{doc_id}`
- **Query Parameters**:
  - `collection_name` (optional): Collection name
- **Description**: Get document text chunks
- **Response**: `{"doc_id": str, "texts": List[str], "text_count": int, "status": str}`

### 7. Search with Context
- **Method**: `POST`
- **Path**: `/search_with_context`
- **Body** (JSON):
  ```json
  {
    "query": "mathematics problem",
    "collection_name": "fipi_documents",
    "top_k": 25,
    "neighbor_window": 2,
    "include_whole_paragraph": true
  }
  ```
- **Description**: Search documents with context expansion
- **Response**: `{"chunks": List[Dict], "merged_text": str}`

### 8. Delete Document
- **Method**: `DELETE`
- **Path**: `/delete_document`
- **Body** (JSON):
  ```json
  {
    "doc_id": "string",
    "collection_name": "string"
  }
  ```
- **Description**: Delete document from collection
- **Response**: `DeleteDocumentResponse`

### 9. Ingest Files
- **Method**: `POST`
- **Path**: `/ingest_files`
- **Body** (form-data):
  - `files`: Files to ingest (multipart)
  - `collection_name` (optional): Collection name
  - `metadata` (optional): Metadata as JSON string
- **Description**: Ingest files into the vector database
- **Response**: `IngestFilesResponse`

## Environment Variables

Create a Postman environment with these variables:
- `base_url`: `http://localhost:8000`
- `doc_id`: `sample-document`
- `collection_name`: `default`
- `search_query`: `mathematics problem`

## Usage Notes

1. **Document ID**: Document IDs are automatically generated from filename (without extension) using slug format
2. **File Upload**: Supported file types depend on the FileTextExtractor implementation
3. **Search**: The search functionality uses semantic similarity based on embeddings
4. **Collections**: All operations support optional collection_name parameter for multi-tenant usage
5. **Error Handling**: All endpoints return appropriate HTTP status codes and error messages

## Import Instructions

1. Import `Theorem_Ingestor_API.postman_collection.json` into Postman
2. Import `Theorem_Ingestor_Environment.postman_environment.json` as environment
3. Select the environment in Postman
4. Update environment variables as needed for your setup