Solução completa que permite criar servidores MCP para operações CRUD em banco de dados (SQLite/MySQL) e integração com Agno Agents e Teams. A solução padroniza a comunicação via MCP e permite que diferentes agentes tenham diferentes capacidades.

---

## 📋 Arquitetura da Solução

### **1. Servidor MCP de Banco de Dados**

O arquivo `mcp_database_server.py` implementa um servidor MCP completo que permite:

- ✅ **Create (Criar)**: Criar novos registros em tabelas
- ✅ **Read (Ler)**: Ler registros com filtros opcionais
- ✅ **Update (Atualizar)**: Atualizar registros existentes
- ❌ **Delete (Deletar)**: NÃO disponível por segurança (como solicitado)

**Ferramentas disponíveis:**
- `create_record`: Cria novos registros
- `read_records`: Lê registros com filtros
- `update_record`: Atualiza registros existentes
- `execute_query`: Executa queries SELECT customizadas (apenas SELECT por segurança)
- `list_tables`: Lista todas as tabelas disponíveis
- `describe_table`: Descreve a estrutura de uma tabela

**Suporte a múltiplos bancos:**
- SQLite (local, fácil de usar)
- MySQL (produção, escalável)

---

### **2. Servidor MCP de RAG (LanceDB)**

O arquivo `mcp_rag_server.py` implementa um servidor MCP para busca semântica em documentos:

- ✅ **Busca semântica**: Busca documentos usando embeddings
- ✅ **Listagem**: Lista todos os documentos disponíveis
- ✅ **Obtenção**: Obtém documentos específicos por ID

**Ferramentas disponíveis:**
- `search_documents`: Busca semântica em documentos
- `get_document`: Obtém documento específico
- `list_documents`: Lista todos os documentos

---

### **3. Integração com Agno Agents**

O arquivo `exemplo_agno_mcp_database.py` mostra como integrar os servidores MCP com Agno:

#### **Agente 1: Database Agent**
- Especializado em operações CRUD
- Conectado ao servidor MCP de banco de dados
- Pode criar, ler e atualizar registros
- NÃO pode deletar (por segurança)

#### **Agente 2: RAG Agent**
- Especializado em busca em documentos
- Conectado ao servidor MCP de RAG (LanceDB)
- Pode buscar informações em documentos internos
- Fornece respostas baseadas em documentos

---

### **4. Integração com Teams**

O Team coordena os agentes e delega tarefas:

- **Database Agent**: Para tarefas de banco de dados
- **RAG Agent**: Para tarefas de busca em documentos
- **Coordenação**: Decide qual agente usar baseado na tarefa

---

### **5. AgentOS com MCP Server**

O AgentOS pode ser configurado como servidor MCP:

- Expõe endpoint `/mcp` para comunicação externa
- Permite que outros sistemas se conectem via MCP
- Padroniza a comunicação entre sistemas

---

## 🛠️ Como Usar

### **Passo 1: Configurar Servidor MCP de Banco de Dados**

```python
# SQLite (local)
server = DatabaseMCPServer(
    db_type="sqlite",
    db_config={"path": "database.db"}
)

# MySQL (produção)
server = DatabaseMCPServer(
    db_type="mysql",
    db_config={
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "senha",
        "database": "meu_banco"
    }
)
```

### **Passo 2: Criar Agente com MCP**

```python
from agno.agent import Agent
from agno.tools.mcp import MCPTools

# Criar MCP Tools
mcp_tools = MCPTools(
    command="python mcp_database_server.py",
    args=[],
    env=os.environ
)

# Criar agente
agent = Agent(
    name="Database Agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[mcp_tools],
    instructions="Você é um assistente especializado em banco de dados..."
)
```

### **Passo 3: Criar Team com Múltiplos Agentes**

```python
from agno.team import Team

# Criar agentes
database_agent = await criar_database_agent()
rag_agent = await criar_rag_agent()

# Criar team
team = Team(
    name="MCP Team",
    agents=[database_agent, rag_agent],
    instructions="Você coordena tarefas entre agentes..."
)
```

### **Passo 4: Usar AgentOS com MCP Server**

```python
from agno.os import AgentOS

agent_os = AgentOS(
    description="Sistema com agentes MCP",
    agents=[database_agent, rag_agent],
    enable_mcp_server=True  # Habilita servidor MCP
)

# O servidor MCP estará disponível em /mcp
```

---

## 🎨 Arquitetura Completa

```
┌─────────────────────────────────────────────────────────────┐
│                     Teams (Coordenador)                      │
│  Delega tarefas para agentes especializados                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ├─────────────────┐
                            │                 │
                            ▼                 ▼
        ┌──────────────────────────┐  ┌──────────────────────────┐
        │   Database Agent          │  │   RAG Agent              │
        │   (CRUD em MySQL/SQLite)  │  │   (Busca em LanceDB)     │
        └──────────────────────────┘  └──────────────────────────┘
                    │                           │
                    │                           │
                    ▼                           ▼
        ┌──────────────────────────┐  ┌──────────────────────────┐
        │   MCP Database Server    │  │   MCP RAG Server          │
        │   (mcp_database_server)  │  │   (mcp_rag_server)        │
        └──────────────────────────┘  └──────────────────────────┘
                    │                           │
                    │                           │
                    ▼                           ▼
        ┌──────────────────────────┐  ┌──────────────────────────┐
        │   MySQL / SQLite         │  │   LanceDB                │
        │   (Banco de dados)       │  │   (Vector Store)         │
        └──────────────────────────┘  └──────────────────────────┘
```

---

## 🔐 Segurança

### **Proteções Implementadas:**

1. **DELETE desabilitado**: Não há ferramenta de DELETE por segurança
2. **Queries limitadas**: Apenas SELECT permitido em queries customizadas
3. **Validação de dados**: Validação antes de criar/atualizar
4. **Filtros obrigatórios**: Filtros necessários para UPDATE

---

## 📝 Exemplos de Uso

### **Exemplo 1: Criar Registro**

```python
# O agente pode criar registros naturalmente
await agent.aprint_response(
    "Crie um novo usuário chamado 'João Silva' com email 'joao@example.com'",
    stream=True
)
```

### **Exemplo 2: Buscar Registros**

```python
# O agente pode buscar registros
await agent.aprint_response(
    "Mostre todos os usuários cadastrados",
    stream=True
)
```

### **Exemplo 3: Atualizar Registro**

```python
# O agente pode atualizar registros
await agent.aprint_response(
    "Atualize a idade do usuário João Silva para 31 anos",
    stream=True
)
```

### **Exemplo 4: Busca em Documentos**

```python
# O RAG agent pode buscar em documentos
await rag_agent.aprint_response(
    "Qual é a política de férias da empresa?",
    stream=True
)
```

### **Exemplo 5: Coordenação via Team**

```python
# O team coordena entre agentes
await team.aprint_response(
    "Busque informações sobre políticas de RH nos documentos e crie um registro no banco com um resumo",
    stream=True
)
```
