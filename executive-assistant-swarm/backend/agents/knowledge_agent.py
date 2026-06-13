import asyncio
from typing import Dict, Any, List
from .base_agent import BaseAgent
from utils.knowledge_db import KnowledgeDB

class KnowledgeAgent(BaseAgent):
    """Agent responsible for querying the personal Knowledge Base (RAG)."""
    
    def __init__(self):
        super().__init__(name="KnowledgeAgent", role="Knowledge Retriever")
        self.db = KnowledgeDB()

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Task format:
        {
            "action": "query" | "add_document",
            "query": str (optional),
            "doc_id": str (optional),
            "text": str (optional),
            "metadata": dict (optional)
        }
        """
        action = task.get("action", "query")
        self.log_action(f"Executing Knowledge action: {action}")

        try:
            if action == "query":
                query_text = task.get("query", "")
                if not query_text:
                    return {"status": "error", "message": "No query provided"}
                    
                self.log_action(f"Querying knowledge base for: '{query_text}'")
                
                # Perform the retrieval asynchronously to avoid blocking
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(None, self.db.query, query_text)
                
                synthesis = "No relevant context found in the knowledge base."
                if results:
                    context = "\n\n".join([f"Snippet {i+1}: {text}" for i, text in enumerate(results)])
                    synthesis = f"Found relevant context:\n\n{context}"
                    
                self.log_action(f"Retrieval complete. Found {len(results)} snippets.")
                
                return {
                    "status": "success",
                    "action": "query",
                    "data": synthesis
                }
                
            elif action == "add_document":
                doc_id = task.get("doc_id", "unknown")
                text = task.get("text", "")
                metadata = task.get("metadata", {})
                
                self.log_action(f"Adding document '{doc_id}' to knowledge base...")
                
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(None, self.db.add_document, doc_id, text, metadata)
                
                if success:
                    return {"status": "success", "message": f"Document {doc_id} added."}
                else:
                    return {"status": "error", "message": f"Failed to add {doc_id}."}
                    
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
                
        except Exception as e:
            self.log_action(f"Knowledge Base Error: {str(e)}", level="ERROR")
            return {"status": "error", "message": str(e)}
