# 🤖 **Exemplo: Agno Agent com MCP Database Server**
# 
# Este exemplo mostra como integrar um servidor MCP de banco de dados
# com Agno Agents e Teams

import asyncio
import os
from typing import List, Optional
from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools
from agno.os import AgentOS
from agno.team import Team


# ============================================================================
# AGENTE 1: Database Agent (CRUD no MySQL/SQLite)
# ============================================================================

async def criar_database_agent() -> Agent:
    """
    Cria um agente que pode fazer CRUD em banco de dados via MCP
    """
    
    # Configuração do servidor MCP de banco de dados
    # Opção 1: SQLite (local)
    mcp_command = "python mcp_database_server.py"
    
    # Opção 2: MySQL (descomente e configure)
    # mcp_command = "python mcp_database_server.py --db-type mysql --host localhost --user root --password senha --database meu_banco"
    
    # Criar MCP Tools
    mcp_tools = MCPTools(
        command=mcp_command,
        args=[],
        env=os.environ
    )
    
    # Criar agente
    agent = Agent(
        name="Database Agent",
        model=OpenAIChat(id="gpt-4o-mini"),  # ou Claude(id="claude-sonnet-4-0")
        tools=[mcp_tools],
        instructions=dedent("""
            Você é um assistente especializado em operações de banco de dados.
            
            Você tem acesso às seguintes ferramentas:
            - create_record: Criar novos registros em tabelas
            - read_records: Ler registros com filtros
            - update_record: Atualizar registros existentes
            - execute_query: Executar queries SELECT customizadas
            - list_tables: Listar todas as tabelas disponíveis
            - describe_table: Descrever estrutura de tabelas
            
            IMPORTANTE:
            - NUNCA execute DELETE (não está disponível por segurança)
            - Sempre valide dados antes de criar ou atualizar
            - Use filtros apropriados ao buscar registros
            - Explique o que você está fazendo antes de executar operações
            
            Quando o usuário pedir para:
            - Criar algo: Use create_record
            - Buscar algo: Use read_records ou execute_query
            - Atualizar algo: Use update_record
            - Ver estrutura: Use list_tables ou describe_table
        """),
        markdown=True,
    )
    
    return agent


# ============================================================================
# AGENTE 2: RAG Agent (Busca em documentos LanceDB)
# ============================================================================

async def criar_rag_agent() -> Agent:
    """
    Cria um agente que faz RAG em documentos via MCP LanceDB
    """
    
    # Configuração do servidor MCP de RAG (LanceDB)
    # Você precisaria criar um servidor MCP similar para LanceDB
    mcp_command = "python mcp_rag_server.py"
    
    mcp_tools = MCPTools(
        command=mcp_command,
        args=[],
        env=os.environ
    )
    
    agent = Agent(
        name="RAG Agent",
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[mcp_tools],
        instructions=dedent("""
            Você é um assistente especializado em buscar informações em documentos.
            
            Você tem acesso a documentos internos através de busca semântica (RAG).
            
            Quando o usuário fizer perguntas:
            - Busque nos documentos usando busca semântica
            - Forneça respostas baseadas nos documentos encontrados
            - Cite as fontes dos documentos
            - Se não encontrar informação, seja honesto sobre isso
        """),
        markdown=True,
    )
    
    return agent


# ============================================================================
# TEAM: Coordenador que delega tarefas
# ============================================================================

async def criar_team_com_mcp() -> Team:
    """
    Cria um Team que coordena agentes com MCP
    """
    
    # Criar agentes
    database_agent = await criar_database_agent()
    rag_agent = await criar_rag_agent()
    
    # Criar team
    team = Team(
        name="MCP Team",
        agents=[database_agent, rag_agent],
        instructions=dedent("""
            Você é um coordenador que delega tarefas para agentes especializados.
            
            Você tem dois agentes disponíveis:
            1. Database Agent: Para operações CRUD em banco de dados
            2. RAG Agent: Para buscar informações em documentos
            
            Quando receber uma tarefa:
            - Se envolver banco de dados (criar, ler, atualizar dados): Delegue para Database Agent
            - Se envolver busca em documentos: Delegue para RAG Agent
            - Se envolver ambos: Coordene entre os dois agentes
            
            Sempre explique qual agente você está usando e por quê.
        """),
    )
    
    return team


# ============================================================================
# AGENTOS: Sistema completo com MCP habilitado
# ============================================================================

async def criar_agentos_com_mcp():
    """
    Cria um AgentOS completo com MCP habilitado
    """
    
    # Criar agentes
    database_agent = await criar_database_agent()
    rag_agent = await criar_rag_agent()
    
    # Criar AgentOS com MCP server habilitado
    agent_os = AgentOS(
        description="Sistema com agentes MCP para banco de dados e RAG",
        agents=[database_agent, rag_agent],
        enable_mcp_server=True,  # Habilita servidor MCP no AgentOS
    )
    
    return agent_os


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

async def exemplo_uso_database_agent():
    """Exemplo de uso do Database Agent"""
    
    agent = await criar_database_agent()
    
    # Conectar ao MCP
    await agent.tools[0].connect()
    
    try:
        # Exemplo 1: Listar tabelas
        print("📊 Listando tabelas disponíveis...")
        await agent.aprint_response(
            "Quais tabelas existem no banco de dados?",
            stream=True
        )
        
        # Exemplo 2: Criar registro
        print("\n📝 Criando um novo usuário...")
        await agent.aprint_response(
            "Crie um novo usuário chamado 'João Silva' com email 'joao@example.com' e idade 30",
            stream=True
        )
        
        # Exemplo 3: Buscar registros
        print("\n🔍 Buscando usuários...")
        await agent.aprint_response(
            "Mostre todos os usuários cadastrados",
            stream=True
        )
        
        # Exemplo 4: Atualizar registro
        print("\n✏️ Atualizando usuário...")
        await agent.aprint_response(
            "Atualize a idade do usuário João Silva para 31 anos",
            stream=True
        )
        
    finally:
        # Desconectar
        await agent.tools[0].close()


async def exemplo_uso_team():
    """Exemplo de uso do Team"""
    
    team = await criar_team_com_mcp()
    
    # Conectar MCP tools
    for agent in team.agents:
        for tool in agent.tools:
            if isinstance(tool, MCPTools):
                await tool.connect()
    
    try:
        # Tarefa que requer banco de dados
        print("🗄️ Tarefa de banco de dados...")
        await team.aprint_response(
            "Crie um novo evento na agenda: 'Reunião de equipe' para amanhã às 14h",
            stream=True
        )
        
        # Tarefa que requer RAG
        print("\n📚 Tarefa de busca em documentos...")
        await team.aprint_response(
            "Qual é a política de férias da empresa?",
            stream=True
        )
        
        # Tarefa que requer ambos
        print("\n🔄 Tarefa combinada...")
        await team.aprint_response(
            "Busque informações sobre políticas de RH nos documentos e crie um registro no banco com um resumo",
            stream=True
        )
        
    finally:
        # Desconectar
        for agent in team.agents:
            for tool in agent.tools:
                if isinstance(tool, MCPTools):
                    await tool.close()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("🚀 Exemplo de Agno Agents com MCP Database Server")
    print("=" * 60)
    print("\nEscolha uma opção:")
    print("1. Testar Database Agent individual")
    print("2. Testar Team com múltiplos agentes")
    print("3. Criar AgentOS completo")
    
    # Descomente para testar:
    # asyncio.run(exemplo_uso_database_agent())
    # asyncio.run(exemplo_uso_team())
    
    print("\n💡 Configure suas variáveis de ambiente:")
    print("   - OPENAI_API_KEY ou ANTHROPIC_API_KEY")
    print("   - Configure o banco de dados no mcp_database_server.py")

