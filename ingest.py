"""
Jewish Coaching (BSD) - ETL Pipeline for RAG Application
Senior Data Engineer Implementation

This script ingests PDF and text files, extracts structured coaching insights
using Azure OpenAI GPT-4o, and builds a comprehensive knowledge base.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Third-party imports
from dotenv import load_dotenv
from openai import AzureOpenAI
from pypdf import PdfReader
from tqdm import tqdm
import tiktoken

# Local imports
from schemas import (
    CoachingInsight,
    ExtractionBatch,
    KnowledgeBase,
    CoachingPhase,
    PHASE_DESCRIPTIONS
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load environment variables
load_dotenv()

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Processing Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 3000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 500))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))

# Directories
DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
LOGS_DIR = Path("logs")

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / f"etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# SYSTEM PROMPT FOR GPT-4o
# ============================================================================

EXTRACTION_SYSTEM_PROMPT = """
You are an expert Data Extractor for the "Jewish Coaching" (BSD) methodology.
Your task is to read the provided text and extract structural coaching components.

**Methodology Mapping (For Classification):**
1. **Situation (המצוי):** Reality vs. Desired Reality descriptions.
2. **Gap (הפער):** The gap between reality and desire. Recognition of the "Opportunity".
3. **Pattern (דפוס):** Recurring automatic behaviors or reactions.
4. **Paradigm (פרדיגמה):** The hidden "Action Thought" (מחשבת המעשה) driving the pattern.
5. **Stance (עמדה):** The root worldview. Includes "Profit & Loss" analysis.
6. **KMZ (כמ"ז):**
   - Distinction between **Source (Mekor)** (Godly soul, values, faith) and **Nature (Teva)** (Ego, survival).
7. **New Choice (התחדשות/בחירה):** Choosing a NEW Stance, Paradigm, and Pattern.
8. **Vision (חזון):** Future orientation, Mission (Shlichut), Destiny (Yiud).
9. **PPD (פפ"ד):** "Project Breakthrough" - specific measurable goals.
10. **Coaching Request (בקשה לאימון):** The formula: "I ask to train on X... to achieve Y...".
11. **General Concept:** Any other relevant coaching insights or explanations.

**Instructions:**
- Extract every relevant insight from the text.
- Map each insight to the correct `phase`.
- Keep the `content_he` in the original Hebrew exactly as it appears.
- GENERATE a clear English summary for `summary_en` so the bot can understand it in any language.
- If you find a coaching question, include it in `key_question`.
- If any specific tool or exercise is mentioned (e.g., "טבלת רווח והפסד", "תרגיל הקופסה"), note it in `tool_used`.
- If the text doesn't contain clear coaching insights, return an empty list.
- Be thorough - extract ALL relevant insights, even if they seem similar.

**Output Format:**
Return a JSON object with an "insights" array containing CoachingInsight objects.
Each insight must have: phase, original_term, content_he, summary_en, and optionally key_question and tool_used.

**IMPORTANT - Phase Values:**
Use ONLY these exact English values for the "phase" field (no Hebrew, no parentheses):
- Situation
- Gap
- Pattern
- Paradigm
- Stance
- KMZ_Source_Nature
- New_Choice
- Vision
- PPD_Project
- Coaching_Request
- General_Concept
"""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_config():
    """Validate that all required configuration is present."""
    missing = []
    
    if not AZURE_OPENAI_API_KEY:
        missing.append("AZURE_OPENAI_API_KEY")
    if not AZURE_OPENAI_ENDPOINT:
        missing.append("AZURE_OPENAI_ENDPOINT")
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please create a .env file with your Azure OpenAI credentials.")
        logger.error("See env_template.txt for an example.")
        sys.exit(1)
    
    if not DATA_DIR.exists():
        logger.error(f"Data directory not found: {DATA_DIR}")
        logger.error("Please create a 'data' folder and add your PDF/TXT files.")
        sys.exit(1)
    
    logger.info("✓ Configuration validated successfully")


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count the number of tokens in a text string."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))


def load_pdf(file_path: Path) -> str:
    """Extract text from a PDF file."""
    logger.info(f"Loading PDF: {file_path.name}")
    
    try:
        reader = PdfReader(str(file_path))
        text = ""
        
        for page_num, page in enumerate(reader.pages, 1):
            page_text = page.extract_text()
            if page_text:
                text += f"\n\n--- Page {page_num} ---\n\n{page_text}"
        
        logger.info(f"✓ Extracted {len(text)} characters from {len(reader.pages)} pages")
        return text
    
    except Exception as e:
        logger.error(f"Error loading PDF {file_path.name}: {e}")
        return ""


def load_text_file(file_path: Path) -> str:
    """Load text from a TXT file."""
    logger.info(f"Loading text file: {file_path.name}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        logger.info(f"✓ Loaded {len(text)} characters")
        return text
    
    except Exception as e:
        logger.error(f"Error loading text file {file_path.name}: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[Tuple[str, Dict]]:
    """
    Split text into overlapping chunks based on token count.
    
    Returns:
        List of tuples: (chunk_text, metadata)
    """
    logger.info(f"Chunking text (size={chunk_size}, overlap={overlap})")
    
    # Split by paragraphs first
    paragraphs = text.split('\n\n')
    
    chunks = []
    current_chunk = ""
    current_tokens = 0
    chunk_num = 0
    
    for para in paragraphs:
        para_tokens = count_tokens(para)
        
        # If adding this paragraph exceeds chunk size, save current chunk
        if current_tokens + para_tokens > chunk_size and current_chunk:
            chunks.append((
                current_chunk.strip(),
                {
                    "chunk_number": chunk_num,
                    "token_count": current_tokens,
                    "char_count": len(current_chunk)
                }
            ))
            
            # Start new chunk with overlap
            overlap_text = ' '.join(current_chunk.split()[-overlap:])
            current_chunk = overlap_text + "\n\n" + para
            current_tokens = count_tokens(current_chunk)
            chunk_num += 1
        else:
            current_chunk += "\n\n" + para if current_chunk else para
            current_tokens += para_tokens
    
    # Add the last chunk
    if current_chunk.strip():
        chunks.append((
            current_chunk.strip(),
            {
                "chunk_number": chunk_num,
                "token_count": current_tokens,
                "char_count": len(current_chunk)
            }
        ))
    
    logger.info(f"✓ Created {len(chunks)} chunks")
    return chunks


def extract_insights_from_chunk(
    client: AzureOpenAI,
    chunk_text: str,
    chunk_metadata: Dict,
    source_file: str,
    retry_count: int = 0
) -> List[CoachingInsight]:
    """
    Extract coaching insights from a text chunk using Azure OpenAI.
    Includes retry logic for API errors.
    """
    
    if retry_count > MAX_RETRIES:
        logger.error(f"Max retries exceeded for chunk {chunk_metadata.get('chunk_number')}")
        return []
    
    try:
        # Prepare the user message
        user_message = f"""
Please analyze the following text and extract all coaching insights according to the Jewish Coaching (BSD) methodology.

Text to analyze:
{chunk_text}

Remember to:
1. Extract ALL relevant insights
2. Keep content_he in original Hebrew
3. Provide English summary in summary_en
4. Classify each insight into the correct phase
"""
        
        # Call Azure OpenAI with JSON mode
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=4000
        )
        
        # Parse the response
        response_text = response.choices[0].message.content
        response_data = json.loads(response_text)
        
        # Validate and convert to Pydantic models
        insights = []
        
        if "insights" in response_data and isinstance(response_data["insights"], list):
            for insight_data in response_data["insights"]:
                try:
                    # Add source file metadata
                    insight_data["source_file"] = source_file
                    
                    # Clean and map the phase field
                    if "phase" in insight_data:
                        phase_value = insight_data["phase"]
                        # Remove anything after "(" if exists
                        if "(" in phase_value:
                            phase_value = phase_value.split("(")[0].strip()
                        
                        # Map variations to correct enum values
                        phase_mapping = {
                            "KMZ": "KMZ_Source_Nature",
                            "PPD": "PPD_Project",
                            "New Choice": "New_Choice",
                            "Coaching Request": "Coaching_Request",
                            "General Concept": "General_Concept"
                        }
                        
                        phase_value = phase_mapping.get(phase_value, phase_value)
                        insight_data["phase"] = phase_value
                    
                    # Create CoachingInsight object
                    insight = CoachingInsight(**insight_data)
                    insights.append(insight)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse insight: {e}")
                    logger.debug(f"Insight data: {insight_data}")
                    continue
        
        logger.info(f"✓ Extracted {len(insights)} insights from chunk {chunk_metadata.get('chunk_number')}")
        return insights
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        logger.debug(f"Response text: {response_text}")
        return []
    
    except Exception as e:
        logger.warning(f"API error (attempt {retry_count + 1}/{MAX_RETRIES}): {e}")
        
        # Exponential backoff
        wait_time = 2 ** retry_count
        logger.info(f"Retrying in {wait_time} seconds...")
        time.sleep(wait_time)
        
        return extract_insights_from_chunk(
            client,
            chunk_text,
            chunk_metadata,
            source_file,
            retry_count + 1
        )


def process_file(client: AzureOpenAI, file_path: Path) -> List[CoachingInsight]:
    """Process a single file (PDF or TXT) and extract all insights."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Processing: {file_path.name}")
    logger.info(f"{'='*80}")
    
    # Load the file
    if file_path.suffix.lower() == '.pdf':
        text = load_pdf(file_path)
    elif file_path.suffix.lower() == '.txt':
        text = load_text_file(file_path)
    else:
        logger.warning(f"Unsupported file type: {file_path.suffix}")
        return []
    
    if not text:
        logger.warning(f"No text extracted from {file_path.name}")
        return []
    
    # Chunk the text
    chunks = chunk_text(text)
    
    # Extract insights from each chunk
    all_insights = []
    
    for chunk_content, chunk_metadata in tqdm(chunks, desc=f"Processing {file_path.name}"):
        insights = extract_insights_from_chunk(
            client,
            chunk_content,
            chunk_metadata,
            file_path.name
        )
        all_insights.extend(insights)
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    logger.info(f"\n✓ Total insights extracted from {file_path.name}: {len(all_insights)}")
    return all_insights


# ============================================================================
# MAIN ETL PIPELINE
# ============================================================================

def main():
    """Main ETL pipeline execution."""
    
    logger.info("\n" + "="*80)
    logger.info("Jewish Coaching ETL Pipeline - Starting")
    logger.info("="*80 + "\n")
    
    # Step 1: Validate configuration
    validate_config()
    
    # Step 2: Initialize Azure OpenAI client
    logger.info("Initializing Azure OpenAI client...")
    
    try:
        client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        logger.info("✓ Azure OpenAI client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Azure OpenAI client: {e}")
        sys.exit(1)
    
    # Step 3: Discover files in data directory
    logger.info(f"\nScanning data directory: {DATA_DIR}")
    
    files_to_process = []
    for ext in ['*.pdf', '*.txt']:
        files_to_process.extend(DATA_DIR.glob(ext))
    
    # Filter out Zone.Identifier files (Windows metadata)
    files_to_process = [f for f in files_to_process if 'Zone.Identifier' not in f.name]
    
    if not files_to_process:
        logger.error("No PDF or TXT files found in data directory!")
        sys.exit(1)
    
    logger.info(f"Found {len(files_to_process)} file(s) to process:")
    for file in files_to_process:
        logger.info(f"  - {file.name}")
    
    # Step 4: Process each file
    knowledge_base = KnowledgeBase()
    knowledge_base.metadata = {
        "created_at": datetime.now().isoformat(),
        "model_used": AZURE_OPENAI_DEPLOYMENT_NAME,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP
    }
    
    for file_path in files_to_process:
        try:
            insights = process_file(client, file_path)
            knowledge_base.add_insights(insights)
            knowledge_base.sources_processed.append(file_path.name)
            
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            logger.exception("Full traceback:")
            continue
    
    # Step 5: Save the knowledge base
    output_file = OUTPUT_DIR / "knowledge_base_master.json"
    logger.info(f"\n{'='*80}")
    logger.info(f"Saving knowledge base to: {output_file}")
    logger.info(f"{'='*80}")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(
                knowledge_base.model_dump(),
                f,
                ensure_ascii=False,
                indent=2
            )
        
        logger.info(f"✓ Knowledge base saved successfully")
        
    except Exception as e:
        logger.error(f"Failed to save knowledge base: {e}")
        sys.exit(1)
    
    # Step 6: Print summary
    logger.info("\n" + "="*80)
    logger.info("ETL PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("="*80)
    logger.info(f"Total insights extracted: {knowledge_base.total_insights}")
    logger.info(f"Files processed: {len(knowledge_base.sources_processed)}")
    logger.info(f"Output file: {output_file}")
    
    # Print breakdown by phase
    logger.info("\nInsights by phase:")
    for phase in CoachingPhase:
        count = len(knowledge_base.get_insights_by_phase(phase))
        if count > 0:
            logger.info(f"  {phase.value}: {count}")
    
    logger.info("\n" + "="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nPipeline interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\nUnexpected error: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)

