import os
from typing import List, Dict
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

class RAGService:
    def __init__(self, persist_directory: str = None):
        # Base directory of the project
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if persist_directory is None:
            self.persist_directory = os.path.join(base_dir, "chroma_db")
        else:
            self.persist_directory = persist_directory
            
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
        self.vectorstore = None
        self._initialize_vectorstore()

    def _initialize_vectorstore(self):
        """Initialize or load the ChromaDB vector store."""
        if os.path.exists(self.persist_directory):
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
        else:
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
            self._load_initial_knowledge()

    def _load_initial_knowledge(self):
        """Load PlantUML templates from the knowledge folder."""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        knowledge_path = os.path.join(base_dir, "knowledge", "class_templates.puml")
        if not os.path.exists(knowledge_path):
            print(f"[RAG_SERVICE] Warning: Knowledge file {knowledge_path} not found.")
            return

        with open(knowledge_path, "r") as f:
            content = f.read()

        # Split by sections (marked by ### in our template)
        sections = content.split("###")
        documents = []
        
        for section in sections:
            if not section.strip():
                continue
            
            lines = section.split("\n")
            title = lines[0].strip()
            puml_content = "\n".join(lines[1:]).strip()
            
            if puml_content:
                doc = Document(
                    page_content=f"Diagram Title: {title}\nContent: {puml_content}",
                    metadata={"title": title, "type": "class"}
                )
                documents.append(doc)

        if documents:
            self.vectorstore.add_documents(documents)
            print(f"[RAG_SERVICE] Indexed {len(documents)} class diagram templates.")

    def get_relevant_context(self, query: str, diagram_type: str = "class", k: int = 1) -> str:
        """Retrieve the most relevant PlantUML context for a given query."""
        if not self.vectorstore:
            return ""

        try:
            # Filter by diagram type if needed (currently only class)
            results = self.vectorstore.similarity_search(query, k=k)
            
            context_blocks = []
            for doc in results:
                context_blocks.append(doc.page_content)
            
            return "\n\n---\n\n".join(context_blocks)
        except Exception as e:
            print(f"[RAG_SERVICE] Retrieval error: {str(e)}")
            return ""

# Singleton instance
rag_instance = RAGService()
