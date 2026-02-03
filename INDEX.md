# 📚 Jewish Coaching RAG Pipeline - Documentation Index

## 🚀 Quick Navigation

### For New Users
1. **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
2. **[README.md](README.md)** - Complete technical documentation
3. **[RUN_PIPELINE.sh](RUN_PIPELINE.sh)** - Automated execution script

### For Azure Setup
1. **[AZURE_SEARCH_SETUP.md](AZURE_SEARCH_SETUP.md)** - Azure AI Search setup guide
2. **[env_template.txt](env_template.txt)** - Environment variables template

### For Understanding the Project
1. **[PIPELINE_COMPLETE.md](PIPELINE_COMPLETE.md)** - Complete pipeline overview
2. **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Original ETL project summary

---

## 📁 Project Files Overview

### 🔧 Core Scripts (1,209 lines of code)

| File | Lines | Purpose |
|------|-------|---------|
| **ingest.py** | 487 | ETL pipeline - Extract insights from PDFs |
| **upload_to_azure.py** | 513 | Upload pipeline - Push to Azure AI Search |
| **schemas.py** | 209 | Pydantic data models and validation |

### 📚 Documentation (1,670 lines)

| File | Lines | Purpose |
|------|-------|---------|
| **README.md** | 392 | Complete technical documentation |
| **PIPELINE_COMPLETE.md** | 472 | Full pipeline overview |
| **AZURE_SEARCH_SETUP.md** | 362 | Azure AI Search setup guide |
| **PROJECT_SUMMARY.md** | 326 | Original ETL summary |
| **QUICKSTART.md** | 118 | 5-minute quick start |

### ⚙️ Configuration & Setup

| File | Purpose |
|------|---------|
| **setup_venv.sh** | Virtual environment setup script |
| **RUN_PIPELINE.sh** | Complete pipeline execution script |
| **requirements.txt** | Python dependencies |
| **env_template.txt** | Environment variables template |
| **.gitignore** | Git ignore rules |

### 📁 Directories

| Directory | Purpose |
|-----------|---------|
| **data/** | Input: PDF and TXT source files |
| **output/** | Output: knowledge_base_master.json |
| **logs/** | Execution logs (ETL and upload) |
| **venv/** | Python virtual environment |

---

## 🎯 Usage Paths

### Path 1: First Time Setup
```
1. Read: QUICKSTART.md
2. Run: ./setup_venv.sh
3. Edit: .env (copy from env_template.txt)
4. Run: ./RUN_PIPELINE.sh
```

### Path 2: Understanding the System
```
1. Read: README.md (architecture & features)
2. Read: PIPELINE_COMPLETE.md (complete overview)
3. Review: schemas.py (data models)
4. Review: ingest.py & upload_to_azure.py (implementation)
```

### Path 3: Azure Setup
```
1. Read: AZURE_SEARCH_SETUP.md
2. Create: Azure AI Search service
3. Update: .env with Azure credentials
4. Run: python upload_to_azure.py
```

### Path 4: Troubleshooting
```
1. Check: logs/ directory
2. Read: README.md → Troubleshooting section
3. Read: AZURE_SEARCH_SETUP.md → Troubleshooting
4. Review: Terminal output for errors
```

---

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Total Code Lines** | 1,209 |
| **Total Documentation Lines** | 1,670 |
| **Total Files** | 13 |
| **Python Scripts** | 3 |
| **Documentation Files** | 5 |
| **Setup Scripts** | 2 |
| **Time to Complete** | ~3 hours |

---

## 🔑 Key Concepts

### ETL Pipeline (ingest.py)
- Loads PDF/TXT files
- Chunks text intelligently
- Extracts insights with GPT-4o
- Validates with Pydantic
- Outputs structured JSON

### Upload Pipeline (upload_to_azure.py)
- Generates embeddings
- Creates Azure AI Search index
- Uploads documents in batches
- Handles rate limiting
- Enables semantic search

### Data Schema (schemas.py)
- 11 coaching phases
- Multi-language support
- Hebrew content + English metadata
- Pydantic validation
- Type safety

---

## 🎓 Learning Resources

### For Python Developers
- **schemas.py** - Pydantic v2 usage
- **ingest.py** - Azure OpenAI integration, error handling
- **upload_to_azure.py** - Azure SDK usage, batch processing

### For Data Engineers
- **ingest.py** - ETL patterns, chunking strategies
- **upload_to_azure.py** - Vector embeddings, batch uploads
- **README.md** - Architecture and design decisions

### For Azure Users
- **AZURE_SEARCH_SETUP.md** - Azure AI Search setup
- **env_template.txt** - Required Azure services
- **upload_to_azure.py** - Azure SDK implementation

---

## 🚀 Quick Commands

```bash
# Setup
./setup_venv.sh
source venv/bin/activate

# Run complete pipeline
./RUN_PIPELINE.sh

# Or run step by step
python ingest.py
python upload_to_azure.py

# View results
cat output/knowledge_base_master.json | jq
tail -f logs/*.log
```

---

## 📞 Getting Help

| Question | See |
|----------|-----|
| How do I get started? | QUICKSTART.md |
| How does it work? | README.md |
| How to setup Azure? | AZURE_SEARCH_SETUP.md |
| What's the complete flow? | PIPELINE_COMPLETE.md |
| What was built originally? | PROJECT_SUMMARY.md |
| How to run everything? | RUN_PIPELINE.sh |

---

## ✅ Completion Checklist

Before running the pipeline, ensure:

- [ ] Virtual environment created (`./setup_venv.sh`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with credentials
- [ ] Azure OpenAI service deployed
- [ ] Azure AI Search service created (for upload)
- [ ] PDF/TXT files in `data/` directory

---

## 🎯 Next Steps After Pipeline

1. **Test Search** - Query Azure AI Search
2. **Build API** - Create FastAPI query endpoint
3. **Create UI** - Build chat interface
4. **Add Analytics** - Track usage and quality
5. **Deploy** - Deploy to Azure App Service

---

## 📝 File Dependencies

```
setup_venv.sh
    ↓
requirements.txt
    ↓
schemas.py ← ingest.py ← upload_to_azure.py
    ↓            ↓              ↓
data/       output/      Azure AI Search
```

---

## 🏆 Project Achievements

✅ Complete ETL pipeline (487 lines)  
✅ Vector upload pipeline (513 lines)  
✅ Pydantic schemas (209 lines)  
✅ Comprehensive documentation (1,670 lines)  
✅ Automated setup scripts  
✅ Error handling & retry logic  
✅ Progress tracking  
✅ Multi-language support  
✅ Production-ready code  

---

## 📧 Contact & Support

**Project**: Jewish Coaching RAG Pipeline  
**Status**: Production Ready  
**Date**: January 2026  
**Contact**: office@ingotera.com

---

**🎉 Welcome to the Jewish Coaching RAG Pipeline!**

*Start with [QUICKSTART.md](QUICKSTART.md) to get up and running in 5 minutes.*

*בס״ד*






