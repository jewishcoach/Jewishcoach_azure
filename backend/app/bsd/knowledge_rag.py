"""
BSD Knowledge RAG Service

Retrieval-Augmented Generation (RAG) service for answering questions about
BSD methodology using Azure AI Search + Azure OpenAI.

This service:
1. Takes a user's methodology question
2. Performs hybrid search (keyword + vector) in Azure AI Search
3. Retrieves relevant context from the BSD knowledge base
4. Uses LLM to generate a natural answer based on the context

Author: Jewish Coaching System
"""

import os
import logging
from typing import List, Dict, Optional, Any
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from langchain_core.messages import SystemMessage, HumanMessage

from .llm import get_azure_chat_llm
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


class BSDKnowledgeRAG:
    """
    RAG service for answering questions about BSD methodology.
    
    Uses Azure AI Search for retrieval and Azure OpenAI for generation.
    """
    
    def __init__(self):
        """Initialize RAG service with Azure clients"""
        self.search_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
        self.index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
        self.search_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
        
        # Initialize only if all credentials are present
        self._search_client = None
        self._openai_client = None
        
        if self.search_endpoint and self.index_name and self.search_key:
            try:
                self._search_client = SearchClient(
                    endpoint=self.search_endpoint,
                    index_name=self.index_name,
                    credential=AzureKeyCredential(self.search_key)
                )
                # Initialize Azure OpenAI client for embeddings
                self._openai_client = AzureOpenAI(
                    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
                )
                logger.info("✅ [RAG] Initialized successfully")
            except Exception as e:
                logger.error(f"❌ [RAG] Initialization failed: {e}")
                self._search_client = None
                self._openai_client = None
        else:
            logger.warning("⚠️  [RAG] Azure Search credentials not configured - RAG disabled")
    
    @property
    def is_available(self) -> bool:
        """Check if RAG service is available"""
        return self._search_client is not None and self._openai_client is not None
    
    async def answer_question(
        self, 
        question: str, 
        language: str = "he"
    ) -> Optional[str]:
        """
        Answer a question about BSD methodology using RAG.
        
        Args:
            question: User's question about BSD methodology
            language: Language for response ("he" or "en")
        
        Returns:
            Natural answer if relevant context found, None otherwise
        """
        if not self.is_available:
            logger.warning("[RAG] Service not available - skipping")
            return None
        
        try:
            logger.info(f"🔍 [RAG] Answering question: '{question[:50]}...'")
            
            # 2. Keyword search (fallback to simple text search)
            results = await self._keyword_search(question)
            
            # 3. Build context from top results
            context = self._build_context(results, language)
            
            if not context:
                logger.info("[RAG] No relevant context found")
                return None
            
            # 4. Generate answer using LLM + context
            answer = await self._generate_answer(question, context, language)
            
            if answer:
                logger.info(f"✅ [RAG] Answer generated: '{answer[:50]}...'")
                return answer
            else:
                logger.info("[RAG] No quality answer generated")
                return None
            
        except Exception as e:
            logger.error(f"❌ [RAG] Error answering question: {e}")
            return None
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Azure OpenAI"""
        try:
            response = self._openai_client.embeddings.create(
                model="text-embedding-3-small",  # Make sure this matches your deployment
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ [RAG] Embedding generation failed: {e}")
            raise
    
    async def _keyword_search(
        self, 
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Perform simple keyword search in Azure AI Search.
        
        Returns top 10 most relevant documents.
        """
        try:
            # Simple text search with more results
            results = self._search_client.search(
                search_text=query,
                select=["content_he", "summary_en", "phase", "original_term"],
                top=10
            )
            
            # Convert to list
            docs = []
            for result in results:
                docs.append({
                    "content_he": result.get("content_he", ""),
                    "summary_en": result.get("summary_en", ""),
                    "phase": result.get("phase", ""),
                    "original_term": result.get("original_term", ""),
                    "score": result.get("@search.score", 0)
                })
            
            logger.info(f"🔍 [RAG] Found {len(docs)} results")
            return docs
            
        except Exception as e:
            logger.error(f"❌ [RAG] Search failed: {e}")
            return []
    
    def _build_context(
        self, 
        results: List[Dict[str, Any]], 
        language: str
    ) -> str:
        """
        Build context string from search results.
        
        Prioritizes content based on language and combines top results.
        """
        if not results:
            return ""
        
        contexts = []
        for result in results:
            if language == "he":
                content = result.get("content_he", "")
            else:
                content = result.get("summary_en", "") or result.get("content_he", "")
            
            if content and len(content.strip()) > 20:  # Filter out too short snippets
                contexts.append(content)
        
        # Combine top results (limit to avoid token overflow)
        combined = "\n\n---\n\n".join(contexts[:5])
        
        logger.debug(f"📄 [RAG] Context built: {len(combined)} chars")
        return combined
    
    async def _generate_answer(
        self, 
        question: str, 
        context: str, 
        language: str
    ) -> str:
        """
        Generate natural answer using LLM + RAG context.
        
        Uses BSD coaching principles to ensure appropriate tone and style.
        """
        if language == "he":
            system_prompt = (
                "אתה מאמן BSD מומחה. תפקידך לענות על שאלות המשתמש על שיטת BSD.\n"
                "\n"
                "עקרונות:\n"
                "1. השתמש במידע מההקשר שניתן לך כבסיס לתשובה\n"
                "2. השב בצורה טבעית וחמה, לא רובוטית\n"
                "3. אם ההקשר מזכיר את הנושא, תן תשובה רלוונטית גם אם לא מפורטת\n"
                "4. רק אם ההקשר לא רלוונטי בכלל לשאלה, אמור 'אין לי מידע מספיק על כך'\n"
                "5. שמור על קצרה - עד 4-5 משפטים\n"
                "6. השב בעברית בלבד\n"
                "\n"
                f"הקשר מהספר:\n{context}"
            )
        else:
            system_prompt = (
                "You are a BSD coaching expert. Your role is to answer user questions about BSD methodology.\n"
                "\n"
                "Principles:\n"
                "1. Use only information from the provided context\n"
                "2. Respond naturally and warmly, not robotically\n"
                "3. Don't interpret or guess - only what's in the context\n"
                "4. If no relevant info, say 'I don't have enough information about that'\n"
                "5. Keep it brief - 3-4 sentences max\n"
                "6. Respond in English only\n"
                "\n"
                f"Context from the book:\n{context}"
            )
        
        llm = get_azure_chat_llm(purpose="talker")
        
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=question)
        ])
        
        answer = response.content.strip() if response and response.content else ""
        
        logger.debug(f"📝 [RAG] LLM response: '{answer[:200]}'...")
        
        # Validate answer quality
        if self._is_low_quality_answer(answer):
            logger.warning(f"[RAG] Generated answer appears low quality: '{answer[:100]}'")
            return None
        
        return answer
    
    def _is_low_quality_answer(self, answer: str) -> bool:
        """
        Check if generated answer is low quality.
        
        Low quality indicators:
        - Too short (< 10 chars)
        - Contains EXACT "I don't know" / "אין לי מידע מספיק"
        - Empty or whitespace only
        """
        if not answer or len(answer.strip()) < 15:
            return True
        
        # Only reject if it's EXACTLY the "no info" response
        low_quality_phrases = [
            "אין לי מידע מספיק על כך",
            "i don't have enough information"
        ]
        
        answer_lower = answer.lower().strip()
        return any(phrase in answer_lower and len(answer_lower) < 50 for phrase in low_quality_phrases)


# Singleton instance
_rag_service: Optional[BSDKnowledgeRAG] = None


def get_rag_service() -> BSDKnowledgeRAG:
    """
    Get singleton RAG service instance.
    
    Returns:
        Initialized BSDKnowledgeRAG instance
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = BSDKnowledgeRAG()
    return _rag_service

