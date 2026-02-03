# 🚀 Quick Start Guide - Jewish Coaching ETL

## ⚡ 5-Minute Setup

### Step 1: Setup Environment (2 minutes)

```bash
# Make setup script executable
chmod +x setup_venv.sh

# Run setup
./setup_venv.sh

# Activate virtual environment
source venv/bin/activate
```

### Step 2: Configure Azure OpenAI (1 minute)

```bash
# Copy template
cp env_template.txt .env

# Edit with your credentials
nano .env
```

Add your Azure OpenAI credentials:
```
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```

### Step 3: Run the ETL Pipeline (2 minutes setup, ~30-60 min processing)

```bash
# Your PDFs are already in data/
ls data/

# Run the ETL pipeline
python ingest.py
```

### Step 4: Upload to Azure AI Search (5-10 min processing)

```bash
# Upload knowledge base to Azure AI Search
python upload_to_azure.py
```

That's it! ✅

**📘 Need help with Azure AI Search setup? See [AZURE_SEARCH_SETUP.md](AZURE_SEARCH_SETUP.md)**

## 📊 View Results

```bash
# View the knowledge base (after ingestion)
cat output/knowledge_base_master.json | python -m json.tool | less

# Check ingestion logs
tail -f logs/etl_*.log

# Check upload logs
tail -f logs/upload_*.log
```

## 🎯 What You Get

- **Input**: Raw PDF/TXT coaching books
- **Output 1**: Structured JSON knowledge base (`knowledge_base_master.json`)
- **Output 2**: Searchable vector database in Azure AI Search
- **Format**: Multi-language (Hebrew content + English metadata)
- **Structure**: 11 coaching phases with extracted insights
- **Search**: Keyword + Vector + Semantic search enabled

## 📈 Expected Output

```json
{
  "total_insights": 150-300,
  "sources_processed": ["CoachBook.pdf", "חוברת..."],
  "insights": [
    {
      "phase": "Gap",
      "original_term": "הפער",
      "content_he": "...",
      "summary_en": "...",
      ...
    }
  ]
}
```

## 🐛 Troubleshooting

**Problem**: Virtual environment activation fails  
**Fix**: `python3 -m venv venv && source venv/bin/activate`

**Problem**: Missing API credentials  
**Fix**: Make sure `.env` file exists with valid Azure OpenAI keys

**Problem**: No files in data directory  
**Fix**: `mv *.pdf data/`

## 📞 Need Help?

- Check `README.md` for detailed documentation
- Review logs in `logs/` directory
- Verify Azure OpenAI deployment is active

---

**Ready to build your Jewish Coaching AI! 🎉**

*בס״ד*

