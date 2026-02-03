# 🔍 Azure AI Search Setup Guide

## Overview

This guide explains how to set up Azure AI Search and upload your Jewish Coaching knowledge base for RAG queries.

---

## 📋 Prerequisites

1. ✅ Azure subscription with credits
2. ✅ Knowledge base created (`output/knowledge_base_master.json`)
3. ✅ Azure OpenAI service with embeddings model deployed

---

## 🚀 Step-by-Step Setup

### Step 1: Create Azure AI Search Service

#### Option A: Using Azure Portal (Recommended for beginners)

1. **Navigate to Azure Portal**
   ```
   https://portal.azure.com
   ```

2. **Create Resource**
   - Click "Create a resource"
   - Search for "Azure AI Search"
   - Click "Create"

3. **Configure Service**
   - **Resource Group**: Create new or select existing
   - **Service name**: e.g., `jewish-coach-search`
   - **Location**: Choose same as OpenAI (e.g., East US)
   - **Pricing tier**: 
     - Development: `Free` (limited features)
     - Production: `Basic` or `Standard` (recommended)

4. **Review + Create**
   - Click "Create"
   - Wait 2-5 minutes for deployment

5. **Get Credentials**
   - Go to your new Search service
   - Navigate to "Keys" in left menu
   - Copy:
     - **URL** (e.g., `https://jewish-coach-search.search.windows.net`)
     - **Primary admin key**

#### Option B: Using Azure CLI

```bash
# Set variables
RESOURCE_GROUP="jewish-coaching-rg"
SEARCH_SERVICE="jewish-coach-search"
LOCATION="eastus"

# Create resource group (if needed)
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure AI Search service
az search service create \
  --name $SEARCH_SERVICE \
  --resource-group $RESOURCE_GROUP \
  --sku Basic \
  --location $LOCATION

# Get admin key
az search admin-key show \
  --service-name $SEARCH_SERVICE \
  --resource-group $RESOURCE_GROUP
```

---

### Step 2: Configure Environment Variables

1. **Open your `.env` file**
   ```bash
   nano .env
   ```

2. **Add Azure AI Search credentials**
   ```env
   # Azure AI Search Configuration
   AZURE_SEARCH_SERVICE_ENDPOINT=https://your-search-service.search.windows.net
   AZURE_SEARCH_INDEX_NAME=jewish-coaching-index
   AZURE_SEARCH_ADMIN_KEY=your-admin-key-here
   ```

3. **Verify Azure OpenAI embeddings**
   
   Make sure you have an embeddings model deployed:
   - Model: `text-embedding-3-small`
   - Or update `EMBEDDING_MODEL` in `upload_to_azure.py` if using different model

---

### Step 3: Install New Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install Azure Search libraries
pip install azure-search-documents==11.4.0 azure-identity==1.15.0

# Or reinstall all requirements
pip install -r requirements.txt
```

---

### Step 4: Run the Upload Script

```bash
python upload_to_azure.py
```

**Expected output:**
```
================================================================================
Jewish Coaching - Azure AI Search Upload Pipeline
================================================================================

✓ Configuration validated successfully
Loading knowledge base from: output/knowledge_base_master.json
✓ Loaded 250 insights

Initializing Azure clients...
✓ All clients initialized successfully

Creating search index: jewish-coaching-index
✓ Index 'jewish-coaching-index' created successfully

================================================================================
Preparing 250 documents with embeddings...
Generating embeddings: 100%|████████████████| 250/250 [02:15<00:00,  1.85it/s]
✓ Prepared 250 documents

================================================================================
Uploading 250 documents in batches of 50...
Uploading batches: 100%|██████████████████████| 5/5 [00:15<00:00,  3.12s/it]

================================================================================
✓ Upload complete!
  Total uploaded: 250
================================================================================

UPLOAD PIPELINE COMPLETED SUCCESSFULLY
================================================================================
Index name: jewish-coaching-index
Service endpoint: https://jewish-coach-search.search.windows.net
Total documents uploaded: 250
Embedding model: text-embedding-3-small
Vector dimensions: 1536

You can now query the index using Azure AI Search!
================================================================================
```

---

## 🔍 What Was Created?

### Azure AI Search Index Structure

| Field | Type | Purpose |
|-------|------|---------|
| `id` | String (Key) | Unique document identifier (SHA256 hash) |
| `phase` | String | Coaching phase (filterable) |
| `original_term` | String | Hebrew term from source |
| `content_he` | String | Full Hebrew content (searchable) |
| `summary_en` | String | English summary (searchable) |
| `key_question` | String | Coaching question (searchable) |
| `tool_used` | String | Tool/exercise name (filterable) |
| `source_file` | String | Source PDF filename (filterable) |
| `page_number` | Int32 | Page number in source |
| `content_vector` | Vector(1536) | Embedding for semantic search |

### Search Capabilities

✅ **Keyword Search** - Search Hebrew and English text  
✅ **Vector Search** - Semantic similarity search  
✅ **Hybrid Search** - Combine keyword + vector  
✅ **Filtering** - Filter by phase, source, tool  
✅ **Faceting** - Group by phase or source  
✅ **Semantic Ranking** - AI-powered relevance  

---

## 📊 Performance & Costs

### Upload Performance

| Metric | Typical Value |
|--------|---------------|
| **Embedding Generation** | ~1-2 seconds/document |
| **Total Time (250 docs)** | 5-10 minutes |
| **Batch Upload** | 50 documents/batch |
| **Rate Limiting** | Auto-handled with retry |

### Azure Costs

**Azure AI Search:**
- Free tier: $0 (limited features, 50MB)
- Basic: ~$75/month (2GB, production-ready)
- Standard: ~$250/month (25GB, high performance)

**Azure OpenAI (Embeddings):**
- text-embedding-3-small: $0.02 / 1M tokens
- For 250 docs (~500 words each): $0.02-0.05

**Total for setup**: < $0.10

---

## 🧪 Testing the Index

### Option 1: Azure Portal

1. Go to Azure Portal → Your Search Service
2. Click "Search explorer"
3. Try queries:
   ```json
   {
     "search": "הפער",
     "select": "phase,content_he,summary_en",
     "top": 5
   }
   ```

### Option 2: Using Python

```python
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# Initialize client
search_client = SearchClient(
    endpoint="https://your-service.search.windows.net",
    index_name="jewish-coaching-index",
    credential=AzureKeyCredential("your-key")
)

# Simple text search
results = search_client.search(
    search_text="הפער",
    select=["phase", "content_he", "summary_en"],
    top=5
)

for result in results:
    print(f"Phase: {result['phase']}")
    print(f"Content: {result['content_he'][:100]}...")
    print("---")
```

### Option 3: Vector Search

```python
from openai import AzureOpenAI

# Get embedding for query
openai_client = AzureOpenAI(...)
response = openai_client.embeddings.create(
    model="text-embedding-3-small",
    input="מהו הפער בין המציאות לרצון?"
)
query_vector = response.data[0].embedding

# Vector search
results = search_client.search(
    search_text=None,
    vector_queries=[{
        "vector": query_vector,
        "k_nearest_neighbors": 5,
        "fields": "content_vector"
    }]
)
```

---

## 🐛 Troubleshooting

### Issue: "Missing environment variables"
**Solution**: Make sure `.env` has all required Azure Search credentials

### Issue: "Index already exists"
**Solution**: This is OK! The script is idempotent. It will use existing index.

### Issue: "Rate limit exceeded (429)"
**Solution**: Script auto-handles this with retry logic. Just wait.

### Issue: "Embedding generation failed"
**Solution**: 
- Verify OpenAI endpoint and key
- Check that embeddings model is deployed
- Verify model name in script matches deployment

### Issue: "Upload failed for some documents"
**Solution**: 
- Check logs in `logs/upload_*.log`
- Verify document size < 16MB
- Check for special characters in content

---

## 🔄 Re-uploading Data

If you need to re-upload after modifying the knowledge base:

```bash
# Option 1: Delete and recreate index
az search index delete \
  --service-name jewish-coach-search \
  --name jewish-coaching-index

# Option 2: Update documents (merge)
# Modify upload_to_azure.py to use merge_or_upload instead of upload_documents
```

---

## 📈 Next Steps

After successful upload, you can:

1. **Build Query Interface**
   - Create a search API with FastAPI
   - Implement hybrid search (keyword + vector)
   - Add filtering by phase/source

2. **Create Chatbot**
   - Use retrieved documents as context
   - Send to GPT-4o for coaching responses
   - Implement conversation history

3. **Add Analytics**
   - Track popular queries
   - Monitor search relevance
   - Optimize ranking

See `RAG_IMPLEMENTATION.md` for building the query layer.

---

## 📞 Support

**Logs**: Check `logs/upload_*.log` for detailed information  
**Azure Portal**: Monitor index in Azure Portal → Search Service  
**Pricing**: [Azure AI Search Pricing](https://azure.microsoft.com/pricing/details/search/)

---

**✅ Setup Complete! Your knowledge base is now searchable in Azure AI Search.**

*בס״ד*






