import chromadb
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import hashlib
import os
import json
from datetime import datetime
from pathlib import Path

class VectorDBManager:
    def __init__(self, data_dir: str = ".github_vector_cli"):
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize stats file
        self.stats_file = Path(data_dir) / "repo_stats.json"
        self._load_stats()
        
        # Use new ChromaDB client configuration
        self.client = chromadb.PersistentClient(path=data_dir)
        self.collection = self.client.get_or_create_collection(
            name="github_repos",
            metadata={"hnsw:space": "cosine"}
        )
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def _load_stats(self):
        """Load repository statistics from file"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    self.repo_stats = json.load(f)
            except json.JSONDecodeError:
                self.repo_stats = {}
        else:
            self.repo_stats = {}

    def store_repository(self, repo_name: str, documents: Dict[str, str]) -> None:
        """Store repository documents in ChromaDB"""
        ids = []
        embeddings = []
        metadatas = []
        documents_list = []
        total_size = 0
        
        for path, content in documents.items():
            doc_id = self._generate_doc_id(repo_name, path)
            content_size = len(content.encode())
            total_size += content_size
            
            ids.append(doc_id)
            embeddings.append(self.embedding_model.encode(content))
            metadatas.append({
                "repo": repo_name,
                "path": path,
                "size": content_size,
                "indexed_at": datetime.now().isoformat()
            })
            documents_list.append(content)
        
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents_list
        )
        
        # Update repository statistics
        self.repo_stats[repo_name] = {
            "indexed_files": len(documents),
            "size_bytes": total_size,
            "last_indexed": datetime.now().isoformat()
        }
        
        with open(self.stats_file, 'w') as f:
            json.dump(self.repo_stats, f, indent=2)

    def search_repository(self, query: str, repo_name: Optional[str] = None, n_results: int = 5) -> List[Dict]:
        """Search across repositories with optional filtering"""
        query_embedding = self.embedding_model.encode(query).tolist()
        
        if repo_name:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where={"repo": repo_name}
            )
        else:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
        
        return self._format_results(results)

    def _format_results(self, results) -> List[Dict]:
        formatted = []
        for i in range(len(results['ids'][0])):
            formatted.append({
                "id": results['ids'][0][i],
                "repo": results['metadatas'][0][i]['repo'],
                "path": results['metadatas'][0][i]['path'],
                "content": results['documents'][0][i],
                "distance": results['distances'][0][i]
            })
        return formatted

    def _generate_doc_id(self, repo_name: str, path: str) -> str:
        """Generate a unique ID for a document"""
        unique_str = f"{repo_name}_{path}"
        return hashlib.md5(unique_str.encode()).hexdigest()

    def clear_repository(self, repo_name: str) -> None:
        """Remove all documents for a specific repository"""
        self.collection.delete(where={"repo": repo_name})
        if repo_name in self.repo_stats:
            del self.repo_stats[repo_name]
            with open(self.stats_file, 'w') as f:
                json.dump(self.repo_stats, f, indent=2)

    def get_repository_stats(self) -> Dict:
        """Get statistics about indexed repositories"""
        total_stats = {
            "total_repos": len(self.repo_stats),
            "total_files": sum(repo["indexed_files"] for repo in self.repo_stats.values()),
            "total_size_bytes": sum(repo["size_bytes"] for repo in self.repo_stats.values()),
            "repos": self.repo_stats
        }
        return total_stats

    def get_repository_files(self, repo_name: str) -> List[Dict[str, any]]:
        """Get list of all files in a repository with their metadata"""
        try:
            results = self.collection.get(
                where={"repo": repo_name},
                include=['metadatas']
            )
            
            if not results or not results['metadatas']:
                return []
            
            files = []
            for metadata in results['metadatas']:
                files.append({
                    "path": metadata["path"],
                    "size": metadata.get("size", 0),
                    "indexed_at": metadata.get("indexed_at", "Unknown")
                })
            
            # Sort files by path for better readability
            return sorted(files, key=lambda x: x["path"])
        except Exception:
            return []

    def get_file_content(self, repo_name: str, file_path: str) -> Optional[str]:
        """Retrieve the content of a specific file from the indexed repositories"""
        doc_id = self._generate_doc_id(repo_name, file_path)
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=['documents']
            )
            if results and results['documents']:
                return results['documents'][0]
        except Exception:
            pass
        return None