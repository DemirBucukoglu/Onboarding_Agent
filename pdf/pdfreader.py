"""
PDF Processing Module - Handles PDF document ingestion for semantic memory.

This module provides functionality to extract text from PDF documents
and store them in semantic memory for AI-powered Q&A functionality.
"""

import os
from pathlib import Path
import PyPDF2
from semantic_kernel.memory import VolatileMemoryStore
from semantic_kernel.connectors.ai.open_ai import OpenAITextEmbedding
from semantic_kernel.memory.semantic_text_memory import SemanticTextMemory


def build_memory() -> SemanticTextMemory:
    """Build and configure semantic text memory with OpenAI embeddings."""
    store = VolatileMemoryStore()
    embed = OpenAITextEmbedding(
        service_id="embed",
        ai_model_id=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    )
    return SemanticTextMemory(storage=store, embeddings_generator=embed)


async def ingest_pdf(path: str | Path, memory: SemanticTextMemory, collection: str = "policy-book") -> None:
    """
    Extract text from PDF and store in semantic memory.
    
    Args:
        path: Path to the PDF file
        memory: Semantic text memory instance
        collection: Name of the memory collection to store the text
    """
    try:
        reader = PyPDF2.PdfReader(str(path))
        
        for page_no, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                await memory.save_information(
                    collection=collection,
                    id=f"page-{page_no}",
                    text=text,
                    description=f"Page {page_no} from {Path(path).name}"
                )
            
    except Exception as e:
        print(f"Error processing PDF {path}: {e}")
        raise
