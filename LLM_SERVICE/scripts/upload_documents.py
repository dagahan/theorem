#!/usr/bin/env python3

import os
import sys
import argparse
import asyncio
from pathlib import Path

import grpc
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent / "embedder_python"))

from src.services.parsers.document_parser import DocumentParser
import proto.embedder_pb2 as embedder_pb2
import proto.embedder_pb2_grpc as embedder_pb2_grpc
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


class DocumentUploader:
    def __init__(self, embedder_host: str, qdrant_host: str, collection_name: str):
        self.embedder_host = embedder_host
        self.qdrant_host = qdrant_host
        self.collection_name = collection_name
        self.embedder_channel = None
        self.embedder_stub = None
        self.qdrant_client = None

    async def connect(self):
        self.embedder_channel = grpc.aio.insecure_channel(self.embedder_host)
        self.embedder_stub = embedder_pb2_grpc.EmbedderServiceStub(self.embedder_channel)
        
        self.qdrant_client = QdrantClient(host=self.qdrant_host.split(':')[0], 
                                        port=int(self.qdrant_host.split(':')[1]))

    async def disconnect(self):
        if self.embedder_channel:
            await self.embedder_channel.close()

    async def create_collection(self, vector_size: int):
        try:
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )
            logger.info(f"Created collection '{self.collection_name}' with vector size {vector_size}")
        except Exception as e:
            if "already exists" in str(e):
                logger.info(f"Collection '{self.collection_name}' already exists")
            else:
                raise

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        request = embedder_pb2.EmbedBatchRequest(texts=texts)
        response = await self.embedder_stub.EmbedBatch(request)
        
        if not response.success:
            raise Exception(f"Embedding failed: {response.error}")
        
        embeddings = []
        for result in response.results:
            if not result.success:
                raise Exception(f"Embedding failed: {result.error}")
            embeddings.append(list(result.embedding))
        
        return embeddings

    async def upload_documents(self, file_path: str, chunk_size: int = 250, chunk_overlap: int = 50):
        logger.info(f"Processing file: {file_path}")
        
        documents = DocumentParser.parse_document(file_path)
        logger.info(f"Parsed {len(documents)} documents")
        
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        combined_text = " ".join(documents)
        chunks = text_splitter.split_text(combined_text)
        logger.info(f"Split into {len(chunks)} chunks")
        
        await self.connect()
        
        try:
            embeddings = await self.embed_texts(chunks)
            vector_size = len(embeddings[0]) if embeddings else 384
            
            await self.create_collection(vector_size)
            
            points = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                points.append(PointStruct(
                    id=str(i),
                    vector=embedding,
                    payload={"text": chunk}
                ))
            
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Successfully uploaded {len(points)} chunks to Qdrant")
            
        finally:
            await self.disconnect()


async def main():
    parser = argparse.ArgumentParser(description="Upload documents to Qdrant")
    parser.add_argument("file_path", help="Path to document file (.xlsx or .xml)")
    parser.add_argument("--embedder-host", default="localhost:50051", help="Embedder service host")
    parser.add_argument("--qdrant-host", default="localhost:6333", help="Qdrant host")
    parser.add_argument("--collection-name", default="documents", help="Collection name")
    parser.add_argument("--chunk-size", type=int, default=250, help="Chunk size")
    parser.add_argument("--chunk-overlap", type=int, default=50, help="Chunk overlap")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file_path):
        logger.error(f"File not found: {args.file_path}")
        sys.exit(1)
    
    uploader = DocumentUploader(
        embedder_host=args.embedder_host,
        qdrant_host=args.qdrant_host,
        collection_name=args.collection_name
    )
    
    try:
        await uploader.upload_documents(
            file_path=args.file_path,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap
        )
        logger.info("Upload completed successfully")
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())