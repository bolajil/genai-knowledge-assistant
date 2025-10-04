"""
PGVector Vector Store Adapter
Implements vector search using PostgreSQL with pgvector extension (Supabase/RDS compatible)
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import numpy as np
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    # Create mock classes for type hints when psycopg2 is not available
    class psycopg2:
        pass
    
    class RealDictCursor:
        pass
    
    import numpy as np

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    # Create mock class for type hints when asyncpg is not available
    class asyncpg:
        pass

from ..multi_vector_storage_interface import (
    BaseVectorStore, VectorStoreConfig, VectorSearchResult, VectorStoreType
)

logger = logging.getLogger(__name__)

class PGVectorAdapter(BaseVectorStore):
    """PostgreSQL with pgvector extension vector store implementation"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        
        if not PSYCOPG2_AVAILABLE and not ASYNCPG_AVAILABLE:
            raise ImportError("psycopg2 or asyncpg package is required for PGVector adapter")
        
        # Extract connection parameters
        params = config.connection_params
        self.host = params.get('host', 'localhost')
        self.port = params.get('port', 5432)
        self.database = params.get('database', 'postgres')
        self.username = params.get('username', 'postgres')
        self.password = params.get('password', '')
        self.ssl_mode = params.get('ssl_mode', 'prefer')
        
        # Vector configuration
        self.vector_dimension = params.get('vector_dimension', 384)
        self.distance_metric = params.get('distance_metric', 'cosine')  # cosine, l2, inner_product
        
        # Connection configuration
        self.use_async = params.get('use_async', True)
        self.connection_pool_size = params.get('connection_pool_size', 10)
        
        self._connection = None
        self._pool = None
    
    def _get_connection_string(self) -> str:
        """Build PostgreSQL connection string"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?sslmode={self.ssl_mode}"
    
    def _get_distance_operator(self) -> str:
        """Get the appropriate distance operator for pgvector"""
        operators = {
            'cosine': '<=>',
            'l2': '<->',
            'inner_product': '<#>'
        }
        return operators.get(self.distance_metric, '<=>')
    
    async def connect(self) -> bool:
        """Establish connection to PostgreSQL with pgvector"""
        try:
            if self.use_async and ASYNCPG_AVAILABLE:
                # Use asyncpg for async operations
                self._pool = await asyncpg.create_pool(
                    self._get_connection_string(),
                    min_size=1,
                    max_size=self.connection_pool_size
                )
                
                # Test connection and ensure pgvector extension
                async with self._pool.acquire() as conn:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    
            else:
                # Use psycopg2 for sync operations
                self._connection = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.username,
                    password=self.password,
                    sslmode=self.ssl_mode
                )
                
                # Test connection and ensure pgvector extension
                with self._connection.cursor() as cursor:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    self._connection.commit()
            
            logger.info(f"Connected to PostgreSQL with pgvector at {self.host}:{self.port}")
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close connection to PostgreSQL"""
        try:
            if self._pool:
                await self._pool.close()
            elif self._connection:
                self._connection.close()
        except Exception as e:
            logger.error(f"Error disconnecting from PostgreSQL: {e}")
        self._connected = False
    
    def _get_table_name(self, collection_name: str) -> str:
        """Generate table name for collection"""
        # Sanitize collection name for SQL
        sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in collection_name)
        return f"vaultmind_{sanitized}"
    
    async def create_collection(self, collection_name: str, **kwargs) -> bool:
        """Create a new table for vector storage"""
        try:
            if not self._connected:
                await self.connect()
            
            table_name = self._get_table_name(collection_name)
            
            # SQL to create table with vector column
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id TEXT PRIMARY KEY,
                content TEXT,
                vector vector({self.vector_dimension}),
                metadata JSONB,
                source TEXT,
                source_type TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            
            # Create indexes for better performance
            create_indexes_sql = [
                f"CREATE INDEX IF NOT EXISTS {table_name}_vector_idx ON {table_name} USING ivfflat (vector {self._get_distance_operator()}) WITH (lists = 100);",
                f"CREATE INDEX IF NOT EXISTS {table_name}_source_idx ON {table_name} (source);",
                f"CREATE INDEX IF NOT EXISTS {table_name}_source_type_idx ON {table_name} (source_type);",
                f"CREATE INDEX IF NOT EXISTS {table_name}_metadata_idx ON {table_name} USING GIN (metadata);"
            ]
            
            if self.use_async and self._pool:
                async with self._pool.acquire() as conn:
                    await conn.execute(create_table_sql)
                    for index_sql in create_indexes_sql:
                        try:
                            await conn.execute(index_sql)
                        except Exception as e:
                            logger.warning(f"Failed to create index: {e}")
            else:
                with self._connection.cursor() as cursor:
                    cursor.execute(create_table_sql)
                    for index_sql in create_indexes_sql:
                        try:
                            cursor.execute(index_sql)
                        except Exception as e:
                            logger.warning(f"Failed to create index: {e}")
                    self._connection.commit()
            
            logger.info(f"Created PGVector table: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create PGVector table {collection_name}: {e}")
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a table"""
        try:
            if not self._connected:
                await self.connect()
            
            table_name = self._get_table_name(collection_name)
            drop_sql = f"DROP TABLE IF EXISTS {table_name};"
            
            if self.use_async and self._pool:
                async with self._pool.acquire() as conn:
                    await conn.execute(drop_sql)
            else:
                with self._connection.cursor() as cursor:
                    cursor.execute(drop_sql)
                    self._connection.commit()
            
            logger.info(f"Deleted PGVector table: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete PGVector table {collection_name}: {e}")
            return False
    
    async def list_collections(self) -> List[str]:
        """List all available tables (collections)"""
        try:
            if not self._connected:
                await self.connect()
            
            # Query for tables with vaultmind prefix
            list_sql = """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name LIKE 'vaultmind_%';
            """
            
            collections = []
            if self.use_async and self._pool:
                async with self._pool.acquire() as conn:
                    rows = await conn.fetch(list_sql)
                    for row in rows:
                        table_name = row['table_name']
                        # Extract collection name
                        if table_name.startswith('vaultmind_'):
                            collection_name = table_name[10:]  # Remove 'vaultmind_' prefix
                            collections.append(collection_name)
            else:
                with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(list_sql)
                    rows = cursor.fetchall()
                    for row in rows:
                        table_name = row['table_name']
                        if table_name.startswith('vaultmind_'):
                            collection_name = table_name[10:]
                            collections.append(collection_name)
            
            return collections
            
        except Exception as e:
            logger.error(f"Failed to list PGVector collections: {e}")
            return []
    
    async def upsert_documents(self, 
                             collection_name: str,
                             documents: List[Dict[str, Any]],
                             embeddings: Optional[List[List[float]]] = None) -> bool:
        """Insert or update documents with vectors"""
        try:
            if not self._connected:
                await self.connect()
            
            table_name = self._get_table_name(collection_name)
            
            # Prepare upsert SQL
            upsert_sql = f"""
            INSERT INTO {table_name} (id, content, vector, metadata, source, source_type, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                vector = EXCLUDED.vector,
                metadata = EXCLUDED.metadata,
                source = EXCLUDED.source,
                source_type = EXCLUDED.source_type,
                created_at = EXCLUDED.created_at;
            """
            
            # Prepare data for batch insert
            batch_data = []
            for i, doc in enumerate(documents):
                doc_id = doc.get('id', f"doc_{i}_{datetime.now().timestamp()}")
                
                # Get vector
                vector = None
                if embeddings and i < len(embeddings):
                    vector = embeddings[i]
                elif 'vector' in doc:
                    vector = doc['vector']
                else:
                    logger.warning(f"No vector provided for document {doc_id}")
                    continue
                
                # Prepare data
                batch_data.append((
                    str(doc_id),
                    doc.get('content', ''),
                    vector,
                    json.dumps(doc.get('metadata', {})),
                    doc.get('source', ''),
                    doc.get('source_type', 'unknown'),
                    doc.get('created_at', datetime.now())
                ))
            
            # Execute batch upsert
            if self.use_async and self._pool:
                async with self._pool.acquire() as conn:
                    await conn.executemany(upsert_sql, batch_data)
            else:
                with self._connection.cursor() as cursor:
                    cursor.executemany(upsert_sql, batch_data)
                    self._connection.commit()
            
            logger.info(f"Upserted {len(batch_data)} documents to PGVector table {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert documents to PGVector table {collection_name}: {e}")
            return False
    
    async def search(self, 
                    collection_name: str,
                    query: Optional[str] = None,
                    query_embedding: Optional[List[float]] = None,
                    filters: Optional[Dict[str, Any]] = None,
                    limit: int = 10,
                    **kwargs) -> List[VectorSearchResult]:
        """Search using pgvector similarity with filtering"""
        try:
            if not query_embedding:
                logger.error("Query embedding is required for PGVector search")
                return []
            
            if not self._connected:
                await self.connect()
            
            table_name = self._get_table_name(collection_name)
            distance_op = self._get_distance_operator()
            
            # Build base query
            base_query = f"""
            SELECT id, content, metadata, source, source_type, created_at,
                   vector {distance_op} $1 as distance
            FROM {table_name}
            """
            
            # Add filters
            where_conditions = []
            params = [query_embedding]
            param_count = 2
            
            if filters:
                for field, value in filters.items():
                    if field == 'metadata':
                        # JSON filtering
                        if isinstance(value, dict):
                            for key, val in value.items():
                                where_conditions.append(f"metadata->>${param_count} = ${param_count + 1}")
                                params.extend([key, json.dumps(val)])
                                param_count += 2
                    else:
                        if isinstance(value, list):
                            placeholders = ','.join([f'${param_count + i}' for i in range(len(value))])
                            where_conditions.append(f"{field} IN ({placeholders})")
                            params.extend(value)
                            param_count += len(value)
                        else:
                            where_conditions.append(f"{field} = ${param_count}")
                            params.append(value)
                            param_count += 1
            
            # Combine query parts
            if where_conditions:
                search_sql = f"{base_query} WHERE {' AND '.join(where_conditions)} ORDER BY distance LIMIT ${param_count}"
            else:
                search_sql = f"{base_query} ORDER BY distance LIMIT ${param_count}"
            
            params.append(limit)
            
            # Execute search
            results = []
            if self.use_async and self._pool:
                async with self._pool.acquire() as conn:
                    rows = await conn.fetch(search_sql, *params)
                    for row in rows:
                        metadata = json.loads(row['metadata']) if row['metadata'] else {}
                        
                        result = VectorSearchResult(
                            content=row['content'],
                            metadata=metadata,
                            score=1.0 - row['distance'],  # Convert distance to similarity
                            source=row['source'],
                            id=row['id']
                        )
                        results.append(result)
            else:
                with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(search_sql, params)
                    rows = cursor.fetchall()
                    for row in rows:
                        metadata = json.loads(row['metadata']) if row['metadata'] else {}
                        
                        result = VectorSearchResult(
                            content=row['content'],
                            metadata=metadata,
                            score=1.0 - row['distance'],
                            source=row['source'],
                            id=row['id']
                        )
                        results.append(result)
            
            logger.info(f"PGVector returned {len(results)} results for query in {collection_name}")
            return results
            
        except Exception as e:
            logger.error(f"Search failed in PGVector table {collection_name}: {e}")
            return []
    
    async def delete_documents(self, 
                             collection_name: str,
                             document_ids: List[str]) -> bool:
        """Delete specific documents from table"""
        try:
            if not self._connected:
                await self.connect()
            
            table_name = self._get_table_name(collection_name)
            
            # Prepare delete SQL with placeholders
            placeholders = ','.join(['$' + str(i + 1) for i in range(len(document_ids))])
            delete_sql = f"DELETE FROM {table_name} WHERE id IN ({placeholders});"
            
            if self.use_async and self._pool:
                async with self._pool.acquire() as conn:
                    await conn.execute(delete_sql, *document_ids)
            else:
                with self._connection.cursor() as cursor:
                    cursor.execute(delete_sql, document_ids)
                    self._connection.commit()
            
            logger.info(f"Deleted {len(document_ids)} documents from PGVector table {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from PGVector table {collection_name}: {e}")
            return False
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a table"""
        try:
            if not self._connected:
                await self.connect()
            
            table_name = self._get_table_name(collection_name)
            
            # Get table statistics
            stats_sql = f"""
            SELECT 
                COUNT(*) as document_count,
                pg_total_relation_size('{table_name}') as size_bytes,
                pg_size_pretty(pg_total_relation_size('{table_name}')) as size_pretty
            FROM {table_name};
            """
            
            if self.use_async and self._pool:
                async with self._pool.acquire() as conn:
                    row = await conn.fetchrow(stats_sql)
                    return {
                        "document_count": row['document_count'],
                        "size_bytes": row['size_bytes'],
                        "size_pretty": row['size_pretty'],
                        "vector_dimension": self.vector_dimension,
                        "distance_metric": self.distance_metric,
                        "health": "green"
                    }
            else:
                with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(stats_sql)
                    row = cursor.fetchone()
                    return {
                        "document_count": row['document_count'],
                        "size_bytes": row['size_bytes'],
                        "size_pretty": row['size_pretty'],
                        "vector_dimension": self.vector_dimension,
                        "distance_metric": self.distance_metric,
                        "health": "green"
                    }
            
        except Exception as e:
            logger.error(f"Failed to get stats for PGVector table {collection_name}: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Tuple[bool, str]:
        """Check if PostgreSQL with pgvector is healthy"""
        try:
            if not self._connected:
                await self.connect()
            
            # Test pgvector extension
            test_sql = "SELECT extname FROM pg_extension WHERE extname = 'vector';"
            
            if self.use_async and self._pool:
                async with self._pool.acquire() as conn:
                    row = await conn.fetchrow(test_sql)
                    if row:
                        collections = await self.list_collections()
                        return True, f"PGVector healthy: {len(collections)} collections available"
                    else:
                        return False, "pgvector extension not installed"
            else:
                with self._connection.cursor() as cursor:
                    cursor.execute(test_sql)
                    row = cursor.fetchone()
                    if row:
                        collections = await self.list_collections()
                        return True, f"PGVector healthy: {len(collections)} collections available"
                    else:
                        return False, "pgvector extension not installed"
                
        except Exception as e:
            return False, f"Health check failed: {e}"

# Register the adapter
from ..multi_vector_storage_interface import VectorStoreFactory
if PSYCOPG2_AVAILABLE or ASYNCPG_AVAILABLE:
    VectorStoreFactory.register(VectorStoreType.PGVECTOR, PGVectorAdapter)
