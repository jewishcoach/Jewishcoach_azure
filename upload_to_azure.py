"""
Jewish Coaching (BSD) - Azure AI Search Upload Script
Upload structured coaching insights with vector embeddings to Azure AI Search

This script completes the RAG pipeline by:
1. Loading the knowledge base JSON
2. Creating an Azure AI Search index with vector search
3. Generating embeddings using Azure OpenAI
4. Uploading documents to Azure AI Search
"""

import os
import sys
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Third-party imports
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
)
from azure.core.exceptions import ResourceExistsError
from tqdm import tqdm

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load environment variables
load_dotenv()

# Azure AI Search Configuration
AZURE_SEARCH_SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "jewish-coaching-index")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Embedding Configuration
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
BATCH_SIZE = 50  # Documents per batch upload
MAX_RETRIES = 3
RATE_LIMIT_SLEEP = 2  # Seconds to wait on rate limit

# File paths
OUTPUT_DIR = Path("output")
KNOWLEDGE_BASE_FILE = OUTPUT_DIR / "knowledge_base_master.json"
LOGS_DIR = Path("logs")

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            LOGS_DIR / f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_config():
    """Validate that all required configuration is present."""
    missing = []
    
    if not AZURE_SEARCH_SERVICE_ENDPOINT:
        missing.append("AZURE_SEARCH_SERVICE_ENDPOINT")
    if not AZURE_SEARCH_ADMIN_KEY:
        missing.append("AZURE_SEARCH_ADMIN_KEY")
    if not AZURE_OPENAI_API_KEY:
        missing.append("AZURE_OPENAI_API_KEY")
    if not AZURE_OPENAI_ENDPOINT:
        missing.append("AZURE_OPENAI_ENDPOINT")
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please update your .env file with Azure AI Search credentials.")
        logger.error("See env_template.txt for an example.")
        sys.exit(1)
    
    if not KNOWLEDGE_BASE_FILE.exists():
        logger.error(f"Knowledge base file not found: {KNOWLEDGE_BASE_FILE}")
        logger.error("Please run ingest.py first to create the knowledge base.")
        sys.exit(1)
    
    logger.info("✓ Configuration validated successfully")


def generate_document_id(insight: Dict[str, Any]) -> str:
    """
    Generate a unique document ID from insight content.
    Uses SHA256 hash of phase + content + source file.
    """
    content = f"{insight['phase']}_{insight['content_he']}_{insight.get('source_file', '')}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:32]


def create_search_index(index_client: SearchIndexClient) -> None:
    """
    Create Azure AI Search index with vector search capabilities.
    Index is idempotent - if it exists, it will not be recreated.
    """
    logger.info(f"Creating search index: {AZURE_SEARCH_INDEX_NAME}")
    
    # Define fields
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True
        ),
        SearchableField(
            name="phase",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True
        ),
        SearchableField(
            name="original_term",
            type=SearchFieldDataType.String,
            filterable=True
        ),
        SearchableField(
            name="content_he",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name="he.microsoft"  # Hebrew analyzer
        ),
        SearchableField(
            name="summary_en",
            type=SearchFieldDataType.String,
            searchable=True
        ),
        SearchableField(
            name="key_question",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name="he.microsoft"
        ),
        SearchableField(
            name="tool_used",
            type=SearchFieldDataType.String,
            filterable=True
        ),
        SimpleField(
            name="source_file",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True
        ),
        SimpleField(
            name="page_number",
            type=SearchFieldDataType.Int32,
            filterable=True
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name="my-vector-profile"
        ),
    ]
    
    # Configure vector search
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="my-hnsw",
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine"
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="my-vector-profile",
                algorithm_configuration_name="my-hnsw"
            )
        ]
    )
    
    # Configure semantic search
    semantic_config = SemanticConfiguration(
        name="my-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="phase"),
            content_fields=[
                SemanticField(field_name="content_he"),
                SemanticField(field_name="summary_en")
            ],
            keywords_fields=[
                SemanticField(field_name="original_term"),
                SemanticField(field_name="tool_used")
            ]
        )
    )
    
    semantic_search = SemanticSearch(
        configurations=[semantic_config]
    )
    
    # Create the index
    index = SearchIndex(
        name=AZURE_SEARCH_INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search
    )
    
    try:
        result = index_client.create_index(index)
        logger.info(f"✓ Index '{result.name}' created successfully")
    except ResourceExistsError:
        logger.info(f"✓ Index '{AZURE_SEARCH_INDEX_NAME}' already exists")
    except Exception as e:
        logger.error(f"Error creating index: {e}")
        raise


def generate_embedding(
    client: AzureOpenAI,
    text: str,
    retry_count: int = 0
) -> Optional[List[float]]:
    """
    Generate embedding vector for text using Azure OpenAI.
    Includes retry logic for rate limiting.
    """
    if retry_count > MAX_RETRIES:
        logger.error(f"Max retries exceeded for embedding generation")
        return None
    
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        
        return response.data[0].embedding
    
    except Exception as e:
        error_message = str(e)
        
        # Handle rate limiting (429)
        if "429" in error_message or "rate limit" in error_message.lower():
            wait_time = RATE_LIMIT_SLEEP * (2 ** retry_count)
            logger.warning(f"Rate limit hit. Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            return generate_embedding(client, text, retry_count + 1)
        
        # Handle other errors
        logger.error(f"Error generating embedding: {e}")
        
        # Exponential backoff for general errors
        if retry_count < MAX_RETRIES:
            wait_time = 2 ** retry_count
            logger.info(f"Retrying in {wait_time}s...")
            time.sleep(wait_time)
            return generate_embedding(client, text, retry_count + 1)
        
        return None


def prepare_documents(
    insights: List[Dict[str, Any]],
    openai_client: AzureOpenAI
) -> List[Dict[str, Any]]:
    """
    Prepare documents for upload by generating embeddings.
    Returns list of documents ready for Azure AI Search.
    """
    logger.info(f"Preparing {len(insights)} documents with embeddings...")
    
    documents = []
    failed_count = 0
    
    for insight in tqdm(insights, desc="Generating embeddings"):
        try:
            # Generate unique ID
            doc_id = generate_document_id(insight)
            
            # Generate embedding for Hebrew content
            embedding = generate_embedding(openai_client, insight['content_he'])
            
            if embedding is None:
                logger.warning(f"Failed to generate embedding for insight: {insight.get('phase')}")
                failed_count += 1
                continue
            
            # Prepare document
            document = {
                "id": doc_id,
                "phase": insight['phase'],
                "original_term": insight['original_term'],
                "content_he": insight['content_he'],
                "summary_en": insight['summary_en'],
                "key_question": insight.get('key_question'),
                "tool_used": insight.get('tool_used'),
                "source_file": insight.get('source_file'),
                "page_number": insight.get('page_number'),
                "content_vector": embedding
            }
            
            documents.append(document)
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Error preparing document: {e}")
            failed_count += 1
            continue
    
    logger.info(f"✓ Prepared {len(documents)} documents")
    if failed_count > 0:
        logger.warning(f"⚠ Failed to prepare {failed_count} documents")
    
    return documents


def upload_documents_in_batches(
    search_client: SearchClient,
    documents: List[Dict[str, Any]],
    batch_size: int = BATCH_SIZE
) -> None:
    """
    Upload documents to Azure AI Search in batches.
    """
    logger.info(f"Uploading {len(documents)} documents in batches of {batch_size}...")
    
    total_uploaded = 0
    total_failed = 0
    
    # Split documents into batches
    for i in tqdm(range(0, len(documents), batch_size), desc="Uploading batches"):
        batch = documents[i:i + batch_size]
        
        try:
            result = search_client.upload_documents(documents=batch)
            
            # Count successes and failures
            succeeded = sum(1 for r in result if r.succeeded)
            failed = len(batch) - succeeded
            
            total_uploaded += succeeded
            total_failed += failed
            
            if failed > 0:
                logger.warning(f"Batch {i//batch_size + 1}: {succeeded} succeeded, {failed} failed")
            
            # Small delay between batches
            time.sleep(0.5)
        
        except Exception as e:
            logger.error(f"Error uploading batch {i//batch_size + 1}: {e}")
            total_failed += len(batch)
            continue
    
    logger.info(f"\n{'='*80}")
    logger.info(f"✓ Upload complete!")
    logger.info(f"  Total uploaded: {total_uploaded}")
    if total_failed > 0:
        logger.warning(f"  Total failed: {total_failed}")
    logger.info(f"{'='*80}\n")


# ============================================================================
# MAIN UPLOAD PIPELINE
# ============================================================================

def main():
    """Main upload pipeline execution."""
    
    logger.info("\n" + "="*80)
    logger.info("Jewish Coaching - Azure AI Search Upload Pipeline")
    logger.info("="*80 + "\n")
    
    # Step 1: Validate configuration
    validate_config()
    
    # Step 2: Load knowledge base
    logger.info(f"Loading knowledge base from: {KNOWLEDGE_BASE_FILE}")
    
    try:
        with open(KNOWLEDGE_BASE_FILE, 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)
        
        insights = knowledge_base.get('insights', [])
        logger.info(f"✓ Loaded {len(insights)} insights")
        
        if not insights:
            logger.error("No insights found in knowledge base!")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Error loading knowledge base: {e}")
        sys.exit(1)
    
    # Step 3: Initialize clients
    logger.info("\nInitializing Azure clients...")
    
    try:
        # Azure AI Search clients
        credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)
        
        index_client = SearchIndexClient(
            endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
            credential=credential
        )
        
        search_client = SearchClient(
            endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
            index_name=AZURE_SEARCH_INDEX_NAME,
            credential=credential
        )
        
        # Azure OpenAI client
        openai_client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        
        logger.info("✓ All clients initialized successfully")
    
    except Exception as e:
        logger.error(f"Error initializing clients: {e}")
        sys.exit(1)
    
    # Step 4: Create search index
    try:
        create_search_index(index_client)
    except Exception as e:
        logger.error(f"Failed to create index: {e}")
        sys.exit(1)
    
    # Step 5: Prepare documents with embeddings
    logger.info("\n" + "="*80)
    documents = prepare_documents(insights, openai_client)
    
    if not documents:
        logger.error("No documents to upload!")
        sys.exit(1)
    
    # Step 6: Upload documents
    logger.info("\n" + "="*80)
    upload_documents_in_batches(search_client, documents)
    
    # Step 7: Print summary
    logger.info("\n" + "="*80)
    logger.info("UPLOAD PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("="*80)
    logger.info(f"Index name: {AZURE_SEARCH_INDEX_NAME}")
    logger.info(f"Service endpoint: {AZURE_SEARCH_SERVICE_ENDPOINT}")
    logger.info(f"Total documents uploaded: {len(documents)}")
    logger.info(f"Embedding model: {EMBEDDING_MODEL}")
    logger.info(f"Vector dimensions: {EMBEDDING_DIMENSIONS}")
    logger.info("\nYou can now query the index using Azure AI Search!")
    logger.info("="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nUpload interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\nUnexpected error: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)






