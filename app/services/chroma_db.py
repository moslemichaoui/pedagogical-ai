"""ChromaDB vector store service."""
import os
from typing import List, Dict, Any, Optional


COLLECTION_NAME = "pedagogical_documents"


def sanitize_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Keep only Chroma-compatible, non-None metadata values."""
    cleaned = {}
    for key, value in (metadata or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            cleaned[key] = value
        elif isinstance(value, int):
            cleaned[key] = value
        elif isinstance(value, float):
            cleaned[key] = value
        elif isinstance(value, str):
            if value != '':
                cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


def build_where_clause(filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build a Chroma where clause from optional filters, ignoring empty values."""
    conditions = []
    for key, value in filters.items():
        if value is None or value == '':
            continue
        conditions.append({key: value})
    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


class ChromaService:
    """ChromaDB vector store service."""

    def __init__(self, persist_dir: Optional[str] = None):
        if persist_dir is None:
            persist_dir = os.environ.get('CHROMA_PERSIST_DIR')
            if not persist_dir:
                try:
                    from flask import current_app
                    persist_dir = current_app.config.get('CHROMA_PERSIST_DIR')
                except RuntimeError:
                    persist_dir = None
            if not persist_dir:
                persist_dir = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), '..', '..', 'chromadb_data')
                )
        self.persist_dir = persist_dir
        self._client = None
        self._collection = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            import chromadb
        except ImportError as e:
            raise RuntimeError(
                "chromadb package not installed. "
                "Please install it with: pip install chromadb"
            ) from e

        os.makedirs(self.persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self.persist_dir)
        return self._client

    def _get_collection(self):
        if self._collection is not None:
            return self._collection

        client = self._get_client()
        kwargs = {
            "name": COLLECTION_NAME,
            "metadata": {"hnsw:space": "cosine"},
        }
        try:
            self._collection = client.get_or_create_collection(
                embedding_function=None,
                **kwargs,
            )
        except TypeError:
            self._collection = client.get_or_create_collection(**kwargs)
        return self._collection

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """Add document chunks with explicit embedding vectors."""
        if not chunks:
            return True

        ids = []
        documents = []
        metadatas = []
        embeddings = []

        for chunk in chunks:
            chunk_id = chunk.get('chunk_id')
            text = chunk.get('text', '')
            embedding = chunk.get('embedding') or chunk.get('embeddings')
            if not chunk_id:
                raise ValueError("Each chunk must include chunk_id")
            if embedding is None:
                raise ValueError("add_chunks requires embedding vectors for every chunk")
            metadata = sanitize_metadata(chunk.get('metadata', {}))
            if 'chunk_id' not in metadata:
                metadata['chunk_id'] = chunk_id
            ids.append(str(chunk_id))
            documents.append(text)
            metadatas.append(metadata)
            embeddings.append(list(embedding))

        collection = self._get_collection()
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return True

    def delete_document(self, doc_id: int) -> bool:
        collection = self._get_collection()
        where = build_where_clause({"document_id": doc_id})
        if where:
            try:
                collection.delete(where=where)
            except Exception:
                collection.delete(where={"document_id": str(doc_id)})
        return True

    def search(self, query_vector: List[float], n_results: int = 5, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        collection = self._get_collection()
        count = collection.count()
        if count == 0:
            return []

        query_kwargs = {
            "query_embeddings": [query_vector],
            "n_results": min(n_results, count),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where

        results = collection.query(**query_kwargs)

        formatted = []
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                distance = results['distances'][0][i] if results.get('distances') else 1.0
                formatted.append({
                    'text': doc,
                    'metadata': metadata or {},
                    'distance': distance,
                    'similarity': 1.0 - distance,
                })
        return formatted

    def get_by_metadata(self, where: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        collection = self._get_collection()
        get_kwargs = {"include": ["documents", "metadatas"]}
        if where:
            get_kwargs["where"] = where
        if limit:
            get_kwargs["limit"] = limit
        results = collection.get(**get_kwargs)

        formatted = []
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents']):
                metadata = results['metadatas'][i] if results.get('metadatas') else {}
                formatted.append({
                    'text': doc,
                    'metadata': metadata or {},
                })
        return formatted

    def count(self) -> int:
        collection = self._get_collection()
        return collection.count()

    def health(self) -> Dict[str, Any]:
        try:
            count = self.count()
            return {
                'status': 'healthy',
                'chunks': count,
                'persist_dir': self.persist_dir,
                'collection': COLLECTION_NAME,
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
            }
