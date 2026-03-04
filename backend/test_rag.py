import asyncio
import sys
import os

# Add parent directory to path to import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.rag_service import rag_instance

async def test_rag():
    print("=== RAG Prototype Verification ===")
    
    # Test queries
    queries = [
        "A system for managing books and library loans",
        "A bank with customers and accounts",
        "E-commerce store with orders and products"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        print("-" * 20)
        context = rag_instance.get_relevant_context(query)
        if context:
            print("Retrieved Context Found!")
            print(f"Snippet: {context[:200]}...")
        else:
            print("No context retrieved. Check if ChromaDB is initialized.")

if __name__ == "__main__":
    asyncio.run(test_rag())
