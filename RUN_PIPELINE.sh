#!/bin/bash

# Jewish Coaching RAG Pipeline - Complete Execution Script
# This script runs the entire pipeline from PDFs to Azure AI Search

set -e  # Exit on error

echo "================================================================================"
echo "Jewish Coaching RAG Pipeline - Complete Execution"
echo "================================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo "Please run: ./setup_venv.sh first"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}[1/4] Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create .env from env_template.txt and add your credentials"
    exit 1
fi

# Check if data directory has files
if [ -z "$(ls -A data/*.pdf data/*.txt 2>/dev/null)" ]; then
    echo -e "${RED}Error: No PDF or TXT files found in data/ directory!${NC}"
    echo "Please add your source files to the data/ directory"
    exit 1
fi

echo -e "${YELLOW}[2/4] Running ETL Pipeline (ingest.py)...${NC}"
echo "This will extract coaching insights from your PDFs"
echo "Expected time: 30-60 minutes"
echo ""

python ingest.py

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: ETL pipeline failed!${NC}"
    echo "Check logs in logs/ directory for details"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ ETL pipeline completed successfully${NC}"
echo ""

# Check if knowledge base was created
if [ ! -f "output/knowledge_base_master.json" ]; then
    echo -e "${RED}Error: Knowledge base file not created!${NC}"
    exit 1
fi

# Count insights
INSIGHT_COUNT=$(python -c "import json; data=json.load(open('output/knowledge_base_master.json')); print(data['total_insights'])")
echo -e "${GREEN}✓ Extracted ${INSIGHT_COUNT} insights${NC}"
echo ""

# Ask user if they want to upload to Azure
echo -e "${YELLOW}[3/4] Upload to Azure AI Search?${NC}"
echo "This will:"
echo "  - Generate embeddings for all insights"
echo "  - Create Azure AI Search index"
echo "  - Upload documents with vectors"
echo "  - Expected time: 5-10 minutes"
echo ""
read -p "Continue with upload? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Skipping Azure upload${NC}"
    echo "You can run it later with: python upload_to_azure.py"
    exit 0
fi

echo ""
echo -e "${YELLOW}[4/4] Running Upload Pipeline (upload_to_azure.py)...${NC}"
echo ""

python upload_to_azure.py

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Upload pipeline failed!${NC}"
    echo "Check logs in logs/ directory for details"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Upload pipeline completed successfully${NC}"
echo ""

# Final summary
echo "================================================================================"
echo -e "${GREEN}🎉 PIPELINE COMPLETED SUCCESSFULLY!${NC}"
echo "================================================================================"
echo ""
echo "Summary:"
echo "  ✓ Insights extracted: ${INSIGHT_COUNT}"
echo "  ✓ Knowledge base: output/knowledge_base_master.json"
echo "  ✓ Azure AI Search: Index created and populated"
echo ""
echo "Next steps:"
echo "  1. Test search in Azure Portal"
echo "  2. Build RAG query API"
echo "  3. Create chat interface"
echo ""
echo "Documentation:"
echo "  - README.md - Complete documentation"
echo "  - AZURE_SEARCH_SETUP.md - Azure setup guide"
echo "  - PIPELINE_COMPLETE.md - Pipeline overview"
echo ""
echo "================================================================================"
echo ""
echo -e "${GREEN}Ready to build your AI Coach! 🚀${NC}"
echo ""
echo "בס״ד"
echo ""






