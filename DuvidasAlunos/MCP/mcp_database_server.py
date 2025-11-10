# 🗄️ **Servidor MCP para CRUD em Banco de Dados**
# 
# Este servidor MCP permite que agentes façam operações CRUD (Create, Read, Update)
# em bancos de dados SQLite ou MySQL, sem DELETE por segurança

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

# MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Banco de dados
import sqlite3
import mysql.connector
from mysql.connector import Error as MySQLError


class DatabaseMCPServer:
    """Servidor MCP para operações CRUD em banco de dados"""
    
    def __init__(self, db_type: str = "sqlite", db_config: Optional[Dict] = None):
        """
        Inicializa o servidor MCP de banco de dados
        
        Args:
            db_type: Tipo de banco ("sqlite" ou "mysql")
            db_config: Configuração do banco de dados
        """
        self.db_type = db_type
        self.db_config = db_config or {}
        self.server = Server("database-mcp-server")
        self.connection = None
        
        # Registrar ferramentas
        self._register_tools()
        
        # Conectar ao banco
        self._connect_database()
    
    def _connect_database(self):
        """Conecta ao banco de dados"""
        try:
            if self.db_type == "sqlite":
                db_path = self.db_config.get("path", "database.db")
                self.connection = sqlite3.connect(db_path, check_same_thread=False)
                self.connection.row_factory = sqlite3.Row
                print(f"✅ Conectado ao SQLite: {db_path}")
                
            elif self.db_type == "mysql":
                self.connection = mysql.connector.connect(
                    host=self.db_config.get("host", "localhost"),
                    port=self.db_config.get("port", 3306),
                    user=self.db_config.get("user", "root"),
                    password=self.db_config.get("password", ""),
                    database=self.db_config.get("database", "test")
                )
                print(f"✅ Conectado ao MySQL: {self.db_config.get('database')}")
                
        except Exception as e:
            print(f"❌ Erro ao conectar ao banco: {e}")
            self.connection = None
    
    def _register_tools(self):
        """Registra as ferramentas MCP"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """Lista todas as ferramentas disponíveis"""
            return [
                Tool(
                    name="create_record",
                    description="Cria um novo registro em uma tabela. Retorna o ID do registro criado.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table": {
                                "type": "string",
                                "description": "Nome da tabela"
                            },
                            "data": {
                                "type": "object",
                                "description": "Dados a serem inseridos (chave-valor)"
                            }
                        },
                        "required": ["table", "data"]
                    }
                ),
                Tool(
                    name="read_records",
                    description="Lê registros de uma tabela com filtros opcionais. Retorna lista de registros.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table": {
                                "type": "string",
                                "description": "Nome da tabela"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Filtros opcionais (ex: {'id': 1, 'name': 'João'})"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Limite de registros (padrão: 100)"
                            }
                        },
                        "required": ["table"]
                    }
                ),
                Tool(
                    name="update_record",
                    description="Atualiza um registro existente. Retorna número de linhas afetadas.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table": {
                                "type": "string",
                                "description": "Nome da tabela"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Filtros para identificar o registro (ex: {'id': 1})"
                            },
                            "data": {
                                "type": "object",
                                "description": "Dados a serem atualizados"
                            }
                        },
                        "required": ["table", "filters", "data"]
                    }
                ),
                Tool(
                    name="execute_query",
                    description="Executa uma query SQL SELECT customizada. Apenas SELECT permitido por segurança.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Query SQL SELECT"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="list_tables",
                    description="Lista todas as tabelas disponíveis no banco de dados",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="describe_table",
                    description="Descreve a estrutura de uma tabela (colunas, tipos, etc.)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table": {
                                "type": "string",
                                "description": "Nome da tabela"
                            }
                        },
                        "required": ["table"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Executa uma ferramenta"""
            
            if not self.connection:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "Não conectado ao banco de dados"}, indent=2)
                )]
            
            try:
                if name == "create_record":
                    result = self._create_record(arguments["table"], arguments["data"])
                    
                elif name == "read_records":
                    filters = arguments.get("filters", {})
                    limit = arguments.get("limit", 100)
                    result = self._read_records(arguments["table"], filters, limit)
                    
                elif name == "update_record":
                    result = self._update_record(
                        arguments["table"],
                        arguments["filters"],
                        arguments["data"]
                    )
                    
                elif name == "execute_query":
                    result = self._execute_query(arguments["query"])
                    
                elif name == "list_tables":
                    result = self._list_tables()
                    
                elif name == "describe_table":
                    result = self._describe_table(arguments["table"])
                    
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
    
    def _create_record(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria um novo registro"""
        try:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?" if self.db_type == "sqlite" else "%s"] * len(data))
            values = list(data.values())
            
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            cursor = self.connection.cursor()
            cursor.execute(query, values)
            self.connection.commit()
            
            # Obter ID do registro criado
            record_id = cursor.lastrowid if self.db_type == "sqlite" else cursor.lastrowid
            
            cursor.close()
            
            return {
                "success": True,
                "message": f"Registro criado com sucesso",
                "id": record_id,
                "table": table
            }
            
        except Exception as e:
            return {"error": f"Erro ao criar registro: {str(e)}"}
    
    def _read_records(self, table: str, filters: Dict[str, Any], limit: int) -> Dict[str, Any]:
        """Lê registros com filtros"""
        try:
            query = f"SELECT * FROM {table}"
            values = []
            
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(f"{key} = ?" if self.db_type == "sqlite" else f"{key} = %s")
                    values.append(value)
                query += " WHERE " + " AND ".join(conditions)
            
            query += f" LIMIT {limit}"
            
            cursor = self.connection.cursor()
            cursor.execute(query, values)
            
            # Converter resultados para dicionário
            if self.db_type == "sqlite":
                rows = [dict(row) for row in cursor.fetchall()]
            else:
                columns = [desc[0] for desc in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            cursor.close()
            
            return {
                "success": True,
                "count": len(rows),
                "records": rows,
                "table": table
            }
            
        except Exception as e:
            return {"error": f"Erro ao ler registros: {str(e)}"}
    
    def _update_record(self, table: str, filters: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza um registro"""
        try:
            # Construir SET clause
            set_clause = []
            values = []
            for key, value in data.items():
                set_clause.append(f"{key} = ?" if self.db_type == "sqlite" else f"{key} = %s")
                values.append(value)
            
            # Construir WHERE clause
            where_clause = []
            for key, value in filters.items():
                where_clause.append(f"{key} = ?" if self.db_type == "sqlite" else f"{key} = %s")
                values.append(value)
            
            query = f"UPDATE {table} SET {', '.join(set_clause)} WHERE {' AND '.join(where_clause)}"
            
            cursor = self.connection.cursor()
            cursor.execute(query, values)
            rows_affected = cursor.rowcount
            self.connection.commit()
            
            cursor.close()
            
            return {
                "success": True,
                "message": f"Registro atualizado com sucesso",
                "rows_affected": rows_affected,
                "table": table
            }
            
        except Exception as e:
            return {"error": f"Erro ao atualizar registro: {str(e)}"}
    
    def _execute_query(self, query: str) -> Dict[str, Any]:
        """Executa uma query SELECT customizada"""
        try:
            # Validar que é apenas SELECT (segurança)
            query_upper = query.strip().upper()
            if not query_upper.startswith("SELECT"):
                return {"error": "Apenas queries SELECT são permitidas por segurança"}
            
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            # Converter resultados
            if self.db_type == "sqlite":
                rows = [dict(row) for row in cursor.fetchall()]
            else:
                columns = [desc[0] for desc in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            cursor.close()
            
            return {
                "success": True,
                "count": len(rows),
                "records": rows
            }
            
        except Exception as e:
            return {"error": f"Erro ao executar query: {str(e)}"}
    
    def _list_tables(self) -> Dict[str, Any]:
        """Lista todas as tabelas"""
        try:
            if self.db_type == "sqlite":
                query = "SELECT name FROM sqlite_master WHERE type='table'"
            else:
                query = "SHOW TABLES"
            
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            if self.db_type == "sqlite":
                tables = [row[0] for row in cursor.fetchall()]
            else:
                tables = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            
            return {
                "success": True,
                "tables": tables,
                "count": len(tables)
            }
            
        except Exception as e:
            return {"error": f"Erro ao listar tabelas: {str(e)}"}
    
    def _describe_table(self, table: str) -> Dict[str, Any]:
        """Descreve a estrutura de uma tabela"""
        try:
            if self.db_type == "sqlite":
                query = f"PRAGMA table_info({table})"
                cursor = self.connection.cursor()
                cursor.execute(query)
                columns = [dict(row) for row in cursor.fetchall()]
            else:
                query = f"DESCRIBE {table}"
                cursor = self.connection.cursor()
                cursor.execute(query)
                columns = []
                for row in cursor.fetchall():
                    columns.append({
                        "name": row[0],
                        "type": row[1],
                        "null": row[2],
                        "key": row[3],
                        "default": row[4],
                        "extra": row[5]
                    })
            
            cursor.close()
            
            return {
                "success": True,
                "table": table,
                "columns": columns
            }
            
        except Exception as e:
            return {"error": f"Erro ao descrever tabela: {str(e)}"}
    
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
    # Configuração SQLite
    sqlite_config = {
        "path": "database.db"
    }
    
    # Configuração MySQL (descomente para usar)
    # mysql_config = {
    #     "host": "localhost",
    #     "port": 3306,
    #     "user": "root",
    #     "password": "senha",
    #     "database": "meu_banco"
    # }
    
    # Criar servidor
    server = DatabaseMCPServer(
        db_type="sqlite",  # ou "mysql"
        db_config=sqlite_config  # ou mysql_config
    )
    
    # Executar servidor
    print("🚀 Servidor MCP de banco de dados iniciado!")
    print("📊 Ferramentas disponíveis:")
    print("   - create_record: Criar registros")
    print("   - read_records: Ler registros")
    print("   - update_record: Atualizar registros")
    print("   - execute_query: Executar queries SELECT")
    print("   - list_tables: Listar tabelas")
    print("   - describe_table: Descrever estrutura de tabela")
    print("\n⚠️ DELETE não está disponível por segurança")
    
    asyncio.run(server.run())

