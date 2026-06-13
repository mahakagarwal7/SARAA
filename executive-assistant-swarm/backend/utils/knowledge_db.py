import os
import chromadb
from chromadb.config import Settings
import logging

logger = logging.getLogger(__name__)

class KnowledgeDB:
    """Wrapper for ChromaDB to provide local RAG capabilities."""
    
    def __init__(self, db_path: str = ".cache/chroma"):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path)
        os.makedirs(self.db_path, exist_ok=True)
        
        try:
            # Initialize ChromaDB Persistent Client
            self.client = chromadb.PersistentClient(path=self.db_path, settings=Settings(anonymized_telemetry=False))
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="personal_knowledge_base",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.client = None
            self.collection = None

    def add_document(self, doc_id: str, text: str, metadata: dict = None):
        """Add a document to the knowledge base."""
        if not self.collection:
            logger.warning("Knowledge Base is not initialized.")
            return False
            
        try:
            # We break large text into smaller chunks for better retrieval
            # For a basic implementation, we just insert the whole text if it's small,
            # or split by paragraphs.
            chunks = [t.strip() for t in text.split('\n\n') if len(t.strip()) > 20]
            
            if not chunks:
                chunks = [text]
                
            ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
            metadatas = [metadata or {"source": doc_id}] * len(chunks)
            
            self.collection.upsert(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Successfully added document {doc_id} with {len(chunks)} chunks.")
            return True
        except Exception as e:
            logger.error(f"Failed to add document to Knowledge Base: {e}")
            return False

    def query(self, query_text: str, n_results: int = 3):
        """Query the knowledge base."""
        if not self.collection:
            logger.warning("Knowledge Base is not initialized.")
            return []
            
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            if not results or not results['documents'] or not results['documents'][0]:
                return []
                
            return results['documents'][0]
            
        except Exception as e:
            logger.error(f"Failed to query Knowledge Base: {e}")
            return []
