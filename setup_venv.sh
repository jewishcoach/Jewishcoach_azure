#!/bin/bash

# Jewish Coach ETL Pipeline - Virtual Environment Setup Script
# Created by: Senior Data Engineer

echo "=================================="
echo "Jewish Coach ETL - Environment Setup"
echo "=================================="

# Check if Python 3.11+ is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Detected Python version: $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "Error: Failed to create virtual environment"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo ""
echo "Installing requirements..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Error: Failed to install requirements"
    exit 1
fi

# Create necessary directories
echo ""
echo "Creating project structure..."
mkdir -p data
mkdir -p output
mkdir -p logs

# Copy .env.example to .env if .env doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Please edit .env file with your Azure OpenAI credentials!"
fi

echo ""
echo "=================================="
echo "✅ Setup completed successfully!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Edit .env file with your Azure OpenAI credentials"
echo "3. Place your PDF/TXT files in the 'data' folder"
echo "4. Run the ingestion: python ingest.py"
echo ""






