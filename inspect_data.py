#!/usr/bin/env python3
"""
Data Quality Audit Script for Azure AI Search

This script inspects the actual chunks stored in Azure AI Search
to verify text quality, formatting, and coherence.
"""

import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from datetime import datetime
from pathlib import Path
import sys

# Ensure UTF-8 encoding for Hebrew text
sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

def print_separator(char="=", length=80):
    """Print a separator line."""
    print(char * length)

def print_document(doc, index):
    """Print a single document in a readable format."""
    print_separator()
    print(f"\n📄 DOCUMENT #{index}")
    print_separator("-")
    
    # Basic Info
    print(f"🆔 ID: {doc.get('id', 'N/A')}")
    print(f"📚 Source: {doc.get('source_file', 'N/A')}")
    print(f"📊 Phase: {doc.get('phase', 'N/A')}")
    
    # Content Analysis
    content = doc.get('content_he', '')
    original_term = doc.get('original_term', 'N/A')
    key_question = doc.get('key_question', 'N/A')
    content_length = len(content)
    print(f"🏷️  Original Term: {original_term}")
    print(f"❓ Key Question: {key_question}")
    print(f"📏 Content Length: {content_length} characters")
    
    # Summary (if available)
    summary = doc.get('summary_en', '')
    if summary:
        print(f"📝 Summary (EN): {summary[:200]}{'...' if len(summary) > 200 else ''}")
    
    print_separator("-")
    print("📖 CONTENT PREVIEW (First 500 characters):")
    print_separator("-")
    
    # Print content preview
    preview = content[:500]
    print(preview)
    
    if content_length > 500:
        print(f"\n... (+ {content_length - 500} more characters)")
    
    print("\n")

def main():
    """Main function to inspect Azure Search data."""
    print_separator("=")
    print("🔍 AZURE AI SEARCH - DATA QUALITY AUDIT")
    print_separator("=")
    print()
    
    # Get Azure credentials from environment
    search_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
    search_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "jewish-coaching-index")
    
    if not search_endpoint or not search_key:
        print("❌ ERROR: Missing Azure Search credentials!")
        print("Please ensure .env file contains:")
        print("  - AZURE_SEARCH_SERVICE_ENDPOINT")
        print("  - AZURE_SEARCH_ADMIN_KEY")
        return
    
    print(f"🔗 Endpoint: {search_endpoint}")
    print(f"📇 Index: {index_name}")
    print()
    
    try:
        # Initialize Search Client
        print("⏳ Connecting to Azure Search...")
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(search_key)
        )
        print("✅ Connected successfully!")
        print()
        
        # Perform wildcard search to get all documents
        print("🔎 Fetching sample documents...")
        results = search_client.search(
            search_text="*",
            select=["id", "content_he", "summary_en", "phase", "source_file", "original_term", "key_question"],
            top=10
        )
        
        # Process and display results
        documents = list(results)
        
        if not documents:
            print("⚠️  No documents found in the index!")
            print("💡 Tip: Run 'python upload_to_azure.py' to populate the index.")
            return
        
        print(f"✅ Found {len(documents)} documents. Displaying samples...\n")
        
        # Display each document
        for i, doc in enumerate(documents, 1):
            print_document(doc, i)
        
        # Summary Statistics
        print_separator("=")
        print("📊 SUMMARY STATISTICS")
        print_separator("=")
        print(f"✓ Total documents retrieved: {len(documents)}")
        
        # Calculate average content length
        content_lengths = []
        for doc in documents:
            content = doc.get('content_he', '')
            content_lengths.append(len(content))
        
        if content_lengths:
            avg_length = sum(content_lengths) / len(content_lengths)
            min_length = min(content_lengths)
            max_length = max(content_lengths)
            
            print(f"✓ Average content length: {avg_length:.0f} characters")
            print(f"✓ Min content length: {min_length} characters")
            print(f"✓ Max content length: {max_length} characters")
        
        # Phase distribution
        phases = [doc.get('phase', 'Unknown') for doc in documents]
        unique_phases = set(phases)
        print(f"✓ Unique phases in sample: {', '.join(sorted(unique_phases))}")
        
        print_separator("=")
        print()
        print("🎯 QUALITY CHECK QUESTIONS:")
        print("  1. Is the Hebrew text readable and properly formatted?")
        print("  2. Are sentences complete or cut off in the middle?")
        print("  3. Is there noise (page numbers, headers, etc.)?")
        print("  4. Does the content make sense in context?")
        print("  5. Are the phase classifications correct?")
        print()
        print("💡 To fetch more documents, modify 'top=10' in the script.")
        print_separator("=")
        
        # Save to file
        print("\n💾 Saving results to file...")
        output_file = Path("logs") / f"data_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("🔍 AZURE AI SEARCH - DATA QUALITY AUDIT\n")
            f.write("="*80 + "\n\n")
            f.write(f"🔗 Endpoint: {search_endpoint}\n")
            f.write(f"📇 Index: {index_name}\n")
            f.write(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for i, doc in enumerate(documents, 1):
                f.write("="*80 + "\n\n")
                f.write(f"📄 DOCUMENT #{i}\n")
                f.write("-"*80 + "\n")
                f.write(f"🆔 ID: {doc.get('id', 'N/A')}\n")
                f.write(f"📚 Source: {doc.get('source_file', 'N/A')}\n")
                f.write(f"📊 Phase: {doc.get('phase', 'N/A')}\n")
                f.write(f"🏷️  Original Term: {doc.get('original_term', 'N/A')}\n")
                f.write(f"❓ Key Question: {doc.get('key_question', 'N/A')}\n")
                
                content = doc.get('content_he', '')
                f.write(f"📏 Content Length: {len(content)} characters\n")
                
                summary = doc.get('summary_en', '')
                if summary:
                    f.write(f"📝 Summary (EN): {summary[:200]}{'...' if len(summary) > 200 else ''}\n")
                
                f.write("-"*80 + "\n")
                f.write("📖 CONTENT PREVIEW (First 500 characters):\n")
                f.write("-"*80 + "\n")
                f.write(content[:500] + "\n")
                
                if len(content) > 500:
                    f.write(f"\n... (+ {len(content) - 500} more characters)\n")
                f.write("\n\n")
            
            # Summary
            f.write("="*80 + "\n")
            f.write("📊 SUMMARY STATISTICS\n")
            f.write("="*80 + "\n")
            f.write(f"✓ Total documents retrieved: {len(documents)}\n")
            
            if content_lengths:
                avg_length = sum(content_lengths) / len(content_lengths)
                f.write(f"✓ Average content length: {avg_length:.0f} characters\n")
                f.write(f"✓ Min content length: {min(content_lengths)} characters\n")
                f.write(f"✓ Max content length: {max(content_lengths)} characters\n")
            
            phases = [doc.get('phase', 'Unknown') for doc in documents]
            unique_phases = set(phases)
            f.write(f"✓ Unique phases in sample: {', '.join(sorted(unique_phases))}\n")
            f.write("="*80 + "\n")
        
        print(f"✅ Results saved to: {output_file}")
        print_separator("=")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    main()

