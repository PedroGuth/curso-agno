# 📚 **Servidor MCP para RAG com LanceDB**
# 
# Este servidor MCP permite que agentes façam busca semântica em documentos
# armazenados no LanceDB

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from pathlib import Path

# MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# RAG e Vector Store
import lancedb
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document


class RAGMCPServer:
    """Servidor MCP para busca RAG em LanceDB"""
    
    def __init__(self, db_path: str = "./lancedb", table_name: str = "documents"):
        """
        Inicializa o servidor MCP de RAG
        
        Args:
            db_path: Caminho do banco LanceDB
            table_name: Nome da tabela no LanceDB
        """
        self.db_path = db_path
        self.table_name = table_name
        self.server = Server("rag-mcp-server")
        self.db = None
        self.table = None
        self.embeddings = None
        
        # Inicializar
        self._initialize_rag()
        
        # Registrar ferramentas
        self._register_tools()
    
    def _initialize_rag(self):
        """Inicializa o sistema RAG"""
        try:
            # Conectar ao LanceDB
            self.db = lancedb.connect(self.db_path)
            
            # Carregar embeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            
            # Verificar se a tabela existe
            if self.table_name in self.db.table_names():
                self.table = self.db.open_table(self.table_name)
                print(f"✅ Tabela '{self.table_name}' carregada do LanceDB")
            else:
                print(f"⚠️ Tabela '{self.table_name}' não encontrada. Crie documentos primeiro.")
                
        except Exception as e:
            print(f"❌ Erro ao inicializar RAG: {e}")
    
    def _register_tools(self):
        """Registra as ferramentas MCP"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """Lista todas as ferramentas disponíveis"""
            return [
                Tool(
                    name="search_documents",
                    description="Busca documentos usando busca semântica. Retorna documentos mais relevantes para a query.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Pergunta ou query para buscar nos documentos"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Número máximo de documentos a retornar (padrão: 5)"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_document",
                    description="Obtém um documento específico por ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "ID do documento"
                            }
                        },
                        "required": ["document_id"]
                    }
                ),
                Tool(
                    name="list_documents",
                    description="Lista todos os documentos disponíveis com metadados",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Número máximo de documentos a retornar (padrão: 20)"
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Executa uma ferramenta"""
            
            if not self.table:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "Tabela não encontrada. Certifique-se de que os documentos foram indexados."
                    }, indent=2)
                )]
            
            try:
                if name == "search_documents":
                    query = arguments["query"]
                    limit = arguments.get("limit", 5)
                    result = self._search_documents(query, limit)
                    
                elif name == "get_document":
                    document_id = arguments["document_id"]
                    result = self._get_document(document_id)
                    
                elif name == "list_documents":
                    limit = arguments.get("limit", 20)
                    result = self._list_documents(limit)
                    
                else:
                    result = {"error": f"Ferramenta '{name}' não encontrada"}
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False, default=str)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]
    
    def _search_documents(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Busca documentos usando busca semântica"""
        try:
            # Gerar embedding da query
            query_embedding = self.embeddings.embed_query(query)
            
            # Buscar no LanceDB
            results = self.table.search(query_embedding).limit(limit).to_pandas()
            
            # Formatar resultados
            documents = []
            for _, row in results.iterrows():
                documents.append({
                    "id": str(row.get("id", "")),
                    "content": row.get("text", ""),
                    "source": row.get("source", ""),
                    "metadata": row.get("metadata", {}),
                    "score": float(row.get("_distance", 0.0)) if "_distance" in row else None
                })
            
            return {
                "success": True,
                "query": query,
                "count": len(documents),
                "documents": documents
            }
            
        except Exception as e:
            return {"error": f"Erro ao buscar documentos: {str(e)}"}
    
    def _get_document(self, document_id: str) -> Dict[str, Any]:
        """Obtém um documento específico"""
        try:
            # Buscar documento por ID
            results = self.table.search([0.0] * 384).limit(1000).to_pandas()
            
            # Filtrar por ID
            document = None
            for _, row in results.iterrows():
                if str(row.get("id", "")) == document_id:
                    document = {
                        "id": str(row.get("id", "")),
                        "content": row.get("text", ""),
                        "source": row.get("source", ""),
                        "metadata": row.get("metadata", {})
                    }
                    break
            
            if document:
                return {
                    "success": True,
                    "document": document
                }
            else:
                return {
                    "error": f"Documento com ID '{document_id}' não encontrado"
                }
                
        except Exception as e:
            return {"error": f"Erro ao obter documento: {str(e)}"}
    
    def _list_documents(self, limit: int = 20) -> Dict[str, Any]:
        """Lista todos os documentos"""
        try:
            # Buscar todos os documentos
            results = self.table.search([0.0] * 384).limit(limit).to_pandas()
            
            # Formatar resultados
            documents = []
            for _, row in results.iterrows():
                documents.append({
                    "id": str(row.get("id", "")),
                    "source": row.get("source", ""),
                    "metadata": row.get("metadata", {}),
                    "content_preview": str(row.get("text", ""))[:200] + "..." if len(str(row.get("text", ""))) > 200 else str(row.get("text", ""))
                })
            
            return {
                "success": True,
                "count": len(documents),
                "documents": documents
            }
            
        except Exception as e:
            return {"error": f"Erro ao listar documentos: {str(e)}"}
    
    async def run(self):
        """Executa o servidor MCP"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


# Exemplo de uso
if __name__ == "__main__":
    # Criar servidor
    server = RAGMCPServer(
        db_path="./lancedb",
        table_name="documents"
    )
    
    # Executar servidor
    print("🚀 Servidor MCP de RAG iniciado!")
    print("📚 Ferramentas disponíveis:")
    print("   - search_documents: Busca semântica em documentos")
    print("   - get_document: Obtém documento específico")
    print("   - list_documents: Lista todos os documentos")
    print("\n💡 Certifique-se de que os documentos foram indexados no LanceDB primeiro!")
    
    asyncio.run(server.run())

