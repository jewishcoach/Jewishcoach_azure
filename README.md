# Jewish Coaching (BSD) - ETL Pipeline for RAG Application

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Azure OpenAI](https://img.shields.io/badge/Azure-OpenAI-brightgreen.svg)](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 📖 Overview

A robust ETL (Extract, Transform, Load) pipeline built by a Senior Data Engineer for ingesting Jewish Coaching methodology books and extracting structured coaching insights using Azure OpenAI GPT-4o.

This pipeline transforms raw PDF and text documents into a structured knowledge base suitable for Retrieval Augmented Generation (RAG) applications.

## 🎯 Project Goal

Build an AI Coach based on the **"Jewish Coaching" (BSD) methodology** by:
- Ingesting raw PDF books and text files
- Analyzing content using Azure OpenAI GPT-4o
- Extracting structured coaching insights
- Building a comprehensive JSON knowledge base

## 🏗️ Complete RAG Architecture

```
┌─────────────────┐
│  PDF/TXT Files  │
│   (data/)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Load & Chunk   │
│  (pypdf + tok)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Azure OpenAI    │
│   GPT-4o        │
│ (Structured Out)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Pydantic Schema │
│  Validation     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Knowledge Base │
│     (JSON)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Generate        │
│ Embeddings      │
│ (Azure OpenAI)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Azure AI Search │
│ (Vector Store)  │
└─────────────────┘
         │
         ▼
    [RAG Ready!]
```

## 📋 Features

### ETL Pipeline (ingest.py)
✅ **Multi-format Support**: PDF and TXT files  
✅ **Intelligent Chunking**: Token-based with overlap  
✅ **Structured Extraction**: Pydantic schema validation  
✅ **Multi-Language**: Hebrew content with English metadata  
✅ **Retry Logic**: Exponential backoff for API errors  
✅ **Progress Tracking**: Real-time progress with tqdm  
✅ **Comprehensive Logging**: File and console logs  
✅ **Error Handling**: Graceful degradation

### Upload Pipeline (upload_to_azure.py)
✅ **Vector Embeddings**: Azure OpenAI text-embedding-3-small  
✅ **Azure AI Search**: Full-text + vector search  
✅ **Batch Upload**: Efficient batch processing  
✅ **Rate Limiting**: Auto-retry on 429 errors  
✅ **Idempotent**: Safe to re-run  
✅ **Hebrew Support**: Hebrew language analyzer  
✅ **Semantic Search**: AI-powered ranking  

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| LLM | Azure OpenAI (GPT-4o) |
| Schema | Pydantic v2 |
| PDF Processing | pypdf |
| Token Counting | tiktoken |
| Progress | tqdm |
| Config | python-dotenv |

## 📦 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Jewishcoach_azure
```

### 2. Run the Setup Script

```bash
chmod +x setup_venv.sh
./setup_venv.sh
```

This will:
- Create a virtual environment
- Install all dependencies
- Create necessary directories
- Generate a template `.env` file

### 3. Configure Azure OpenAI

Edit the `.env` file with your Azure OpenAI credentials:

```bash
nano .env
```

Required configuration:
```env
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

Optional configuration:
```env
CHUNK_SIZE=3000
CHUNK_OVERLAP=500
MAX_RETRIES=3
```

### 4. Add Source Files

Place your PDF or TXT files in the `data/` directory:

```bash
cp your_books/*.pdf data/
```

## 🚀 Usage

### Step 1: Extract Insights from PDFs

Activate the virtual environment and run the ingestion pipeline:

```bash
source venv/bin/activate
python ingest.py
```

### Step 2: Upload to Azure AI Search

After ingestion completes, upload to Azure AI Search:

```bash
python upload_to_azure.py
```

**📘 For detailed Azure setup instructions, see [AZURE_SEARCH_SETUP.md](AZURE_SEARCH_SETUP.md)**

### What Happens

1. **Validation**: Checks configuration and data directory
2. **Discovery**: Finds all PDF/TXT files in `data/`
3. **Loading**: Extracts text from each document
4. **Chunking**: Splits text into ~3000 token chunks with overlap
5. **Extraction**: Sends chunks to GPT-4o for structured extraction
6. **Validation**: Validates extracted insights against Pydantic schema
7. **Aggregation**: Combines all insights into a knowledge base
8. **Output**: Saves to `output/knowledge_base_master.json`

### Output

The pipeline generates:
- `output/knowledge_base_master.json` - Complete knowledge base
- `logs/etl_YYYYMMDD_HHMMSS.log` - Detailed execution log

## 📊 Data Schema

### CoachingInsight Model

Each extracted insight follows this structure:

```python
{
  "phase": "Gap",                           # Enum: Coaching phase
  "original_term": "הפער",                  # Hebrew term from text
  "content_he": "הפער הוא המרחק...",        # Full Hebrew content
  "summary_en": "The Gap is the distance...", # English summary
  "key_question": "מה הפער בין...",         # Optional: Coaching question
  "tool_used": "Gap Analysis Exercise",      # Optional: Tool/exercise
  "source_file": "CoachBook.pdf",           # Source filename
  "page_number": 15,                        # Optional: Page number
  "confidence_score": 0.95                  # Optional: Confidence
}
```

### Coaching Phases

The methodology includes 11 phases:

1. **Situation (המצוי)** - Current vs. desired reality
2. **Gap (הפער)** - The opportunity for change
3. **Pattern (דפוס)** - Recurring behaviors
4. **Paradigm (פרדיגמה)** - Hidden action thoughts
5. **Stance (עמדה)** - Root worldview
6. **KMZ_Source_Nature (כמ"ז)** - Source vs. Nature distinction
7. **New_Choice (בחירה חדשה)** - Choosing new patterns
8. **Vision (חזון)** - Future mission and destiny
9. **PPD_Project (פפ"ד)** - Breakthrough projects
10. **Coaching_Request (בקשה לאימון)** - Coaching formula
11. **General_Concept** - Other relevant insights

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AZURE_OPENAI_API_KEY` | Your Azure OpenAI API key | Required |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | Required |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Model deployment name | `gpt-4o` |
| `AZURE_OPENAI_API_VERSION` | API version | `2024-02-15-preview` |
| `CHUNK_SIZE` | Max tokens per chunk | `3000` |
| `CHUNK_OVERLAP` | Token overlap between chunks | `500` |
| `MAX_RETRIES` | Max API retry attempts | `3` |

### Directory Structure

```
Jewishcoach_azure/
├── data/                    # Input: PDF and TXT files
├── output/                  # Output: knowledge_base_master.json
├── logs/                    # Execution logs
├── venv/                    # Virtual environment
├── schemas.py               # Pydantic data models
├── ingest.py                # Main ETL pipeline
├── requirements.txt         # Python dependencies
├── setup_venv.sh           # Setup script
├── env_template.txt        # Environment template
└── README.md               # This file
```

## 📝 Example Output

```json
{
  "version": "1.0.0",
  "total_insights": 156,
  "sources_processed": [
    "CoachBook.pdf",
    "חוברת מהדורה שלישית.pdf"
  ],
  "insights": [
    {
      "phase": "Gap",
      "original_term": "הפער",
      "content_he": "הפער הוא המרחק בין המצוי לבין הרצוי...",
      "summary_en": "The Gap is the distance between current and desired reality...",
      "key_question": "מה הפער שלי?",
      "tool_used": "Gap Analysis",
      "source_file": "CoachBook.pdf"
    }
  ],
  "metadata": {
    "created_at": "2026-01-13T10:30:00",
    "model_used": "gpt-4o",
    "chunk_size": 3000,
    "chunk_overlap": 500
  }
}
```

## 🐛 Troubleshooting

### Common Issues

**Issue**: `ImportError: No module named 'openai'`  
**Solution**: Activate virtual environment: `source venv/bin/activate`

**Issue**: `Missing required environment variables`  
**Solution**: Create `.env` file from `env_template.txt` and add credentials

**Issue**: `Data directory not found`  
**Solution**: Run `mkdir -p data` and add your source files

**Issue**: `API rate limit exceeded`  
**Solution**: Increase delays between chunks or reduce `CHUNK_SIZE`

**Issue**: `JSON decode error from API`  
**Solution**: Check Azure OpenAI deployment supports JSON mode

## 🔐 Security

- Never commit `.env` file to version control
- Store API keys securely (use Azure Key Vault in production)
- Rotate API keys regularly
- Use managed identities when deploying to Azure

## 📈 Performance

| Metric | Value |
|--------|-------|
| Processing Speed | ~30-60 seconds per chunk |
| API Calls | 1 per chunk (~3000 tokens) |
| Typical Book | 50-100 chunks |
| Total Time | 30-60 minutes per book |

**Optimization Tips:**
- Increase `CHUNK_SIZE` to reduce API calls
- Use batch processing for multiple files
- Implement caching for repeated chunks
- Use GPT-4o-mini for faster/cheaper processing

## 🧪 Testing

Test with a small file first:

```bash
# Create a test file
echo "המצוי: המציאות הנוכחית שלי היא X. הרצוי: אני רוצה Y." > data/test.txt

# Run pipeline
python ingest.py

# Check output
cat output/knowledge_base_master.json | python -m json.tool
```

## 📚 System Prompt

The pipeline uses a specialized system prompt that instructs GPT-4o to:
- Understand the 11 phases of Jewish Coaching
- Extract insights in original Hebrew
- Generate English summaries
- Identify coaching questions and tools
- Classify insights correctly

See `ingest.py` for the full prompt.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## 👥 Authors

- **Senior Data Engineer** - Initial ETL architecture
- **Jewish Coaching (BSD)** - Methodology framework

## 🙏 Acknowledgments

- Jewish Coaching (BSD) methodology
- Azure OpenAI team
- Open source community

## 📞 Support

For issues or questions:
- Open a GitHub issue
- Contact: office@ingotera.com

---

**Built with ❤️ for the Jewish Coaching community**

*B"H* (בס״ד)

