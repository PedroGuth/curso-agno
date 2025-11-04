# 🚀 **RAG Multimodal com PDFs - Processamento de Imagens e Tabelas**
# 
# Este exemplo demonstra como processar PDFs contendo imagens e tabelas,
# armazenar no LanceDB e apresentar no AgentUI do Agno

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import base64
import json

# Processamento de PDFs
import fitz  # PyMuPDF - melhor para extrair imagens e tabelas
import pdfplumber  # Excelente para extração de tabelas
from PIL import Image
import pandas as pd

# RAG e Vector Store
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
import lancedb
import pyarrow as pa

# Para processamento de imagens (descrições)
from transformers import pipeline

# Para processamento de tabelas
import tabula  # Alternativa para extração de tabelas


class PDFMultimodalProcessor:
    """Processa PDFs extraindo texto, imagens e tabelas"""
    
    def __init__(self, pdfs_folder: str = "pdfs"):
        self.pdfs_folder = Path(pdfs_folder)
        self.output_images = Path("pdf_images")
        self.output_tables = Path("pdf_tables")
        
        # Criar pastas de saída
        self.output_images.mkdir(exist_ok=True)
        self.output_tables.mkdir(exist_ok=True)
        
        # Pipeline para descrição de imagens
        try:
            self.image_captioner = pipeline(
                "image-to-text", 
                model="nlpconnect/vit-gpt2-image-captioning"
            )
        except:
            self.image_captioner = None
            print("⚠️ Modelo de caption não disponível, usando descrições básicas")
    
    def extract_images_from_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extrai imagens de um PDF"""
        images_data = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Salvar imagem
                    image_filename = f"{pdf_path.stem}_page{page_num+1}_img{img_index+1}.{image_ext}"
                    image_path = self.output_images / image_filename
                    
                    with open(image_path, "wb") as img_file:
                        img_file.write(image_bytes)
                    
                    # Gerar descrição da imagem
                    description = self._describe_image(image_path)
                    
                    # Converter para base64 para armazenamento
                    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                    
                    images_data.append({
                        "page": page_num + 1,
                        "image_index": img_index + 1,
                        "image_path": str(image_path),
                        "image_b64": image_b64,
                        "description": description,
                        "source_pdf": pdf_path.name
                    })
            
            doc.close()
            print(f"✅ Extraídas {len(images_data)} imagens de {pdf_path.name}")
            
        except Exception as e:
            print(f"❌ Erro ao extrair imagens de {pdf_path.name}: {e}")
        
        return images_data
    
    def _describe_image(self, image_path: Path) -> str:
        """Gera descrição de uma imagem"""
        if self.image_captioner:
            try:
                image = Image.open(image_path)
                result = self.image_captioner(image)
                return result[0]['generated_text']
            except:
                pass
        
        # Fallback: descrição básica
        return f"Imagem extraída do PDF: {image_path.name}"
    
    def extract_tables_from_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extrai tabelas de um PDF usando pdfplumber"""
        tables_data = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    
                    for table_index, table in enumerate(tables):
                        if table and len(table) > 0:
                            # Converter para DataFrame
                            df = pd.DataFrame(table[1:], columns=table[0])
                            
                            # Salvar tabela como CSV
                            table_filename = f"{pdf_path.stem}_page{page_num}_table{table_index+1}.csv"
                            table_path = self.output_tables / table_filename
                            df.to_csv(table_path, index=False)
                            
                            # Converter para JSON para armazenamento
                            table_json = df.to_dict(orient='records')
                            
                            # Criar descrição textual da tabela
                            description = self._describe_table(df, table[0])
                            
                            tables_data.append({
                                "page": page_num,
                                "table_index": table_index + 1,
                                "table_path": str(table_path),
                                "table_json": table_json,
                                "table_csv": df.to_csv(index=False),
                                "description": description,
                                "source_pdf": pdf_path.name,
                                "rows": len(df),
                                "columns": len(df.columns)
                            })
            
            print(f"✅ Extraídas {len(tables_data)} tabelas de {pdf_path.name}")
            
        except Exception as e:
            print(f"❌ Erro ao extrair tabelas de {pdf_path.name}: {e}")
        
        return tables_data
    
    def _describe_table(self, df: pd.DataFrame, headers: List[str]) -> str:
        """Gera descrição textual de uma tabela"""
        description = f"Tabela com {len(df)} linhas e {len(df.columns)} colunas. "
        description += f"Colunas: {', '.join(headers[:5])}"
        if len(headers) > 5:
            description += "..."
        return description
    
    def extract_text_from_pdf(self, pdf_path: Path) -> List[Document]:
        """Extrai texto de um PDF usando LangChain"""
        try:
            loader = PyPDFLoader(str(pdf_path))
            documents = loader.load()
            
            # Adicionar metadados
            for doc in documents:
                doc.metadata['source_pdf'] = pdf_path.name
                doc.metadata['content_type'] = 'text'
            
            return documents
            
        except Exception as e:
            print(f"❌ Erro ao extrair texto de {pdf_path.name}: {e}")
            return []
    
    def process_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Processa um PDF completo extraindo tudo"""
        print(f"\n📄 Processando: {pdf_path.name}")
        
        # Extrair texto
        text_docs = self.extract_text_from_pdf(pdf_path)
        
        # Extrair imagens
        images = self.extract_images_from_pdf(pdf_path)
        
        # Extrair tabelas
        tables = self.extract_tables_from_pdf(pdf_path)
        
        return {
            "pdf_name": pdf_path.name,
            "text_documents": text_docs,
            "images": images,
            "tables": tables
        }
    
    def process_all_pdfs(self) -> List[Dict[str, Any]]:
        """Processa todos os PDFs da pasta"""
        pdf_files = list(self.pdfs_folder.glob("*.pdf"))
        
        if not pdf_files:
            print(f"⚠️ Nenhum PDF encontrado em {self.pdfs_folder}")
            return []
        
        all_results = []
        
        for pdf_path in pdf_files:
            result = self.process_pdf(pdf_path)
            all_results.append(result)
        
        print(f"\n✅ Processados {len(all_results)} PDFs")
        return all_results


class LanceDBMultimodalStore:
    """Armazena documentos multimodais no LanceDB"""
    
    def __init__(self, db_path: str = "./lancedb_multimodal"):
        self.db_path = db_path
        self.db = None
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
    def initialize_db(self):
        """Inicializa o banco de dados LanceDB"""
        try:
            self.db = lancedb.connect(self.db_path)
            print(f"✅ LanceDB conectado em {self.db_path}")
        except:
            self.db = lancedb.connect(self.db_path)
            print(f"✅ LanceDB criado em {self.db_path}")
    
    def create_documents_with_metadata(self, processed_pdfs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Cria documentos com metadados para armazenamento"""
        all_documents = []
        
        for pdf_data in processed_pdfs:
            # Adicionar documentos de texto
            for doc in pdf_data['text_documents']:
                embedding = self.embeddings.embed_query(doc.page_content)
                
                all_documents.append({
                    "content": doc.page_content,
                    "content_type": "text",
                    "source_pdf": pdf_data['pdf_name'],
                    "page": doc.metadata.get('page', 0),
                    "embedding": embedding,
                    "metadata": json.dumps({
                        "type": "text",
                        "source": pdf_data['pdf_name'],
                        "page": doc.metadata.get('page', 0)
                    })
                })
            
            # Adicionar imagens com descrições
            for img in pdf_data['images']:
                # Criar embedding da descrição
                embedding = self.embeddings.embed_query(img['description'])
                
                all_documents.append({
                    "content": img['description'],
                    "content_type": "image",
                    "source_pdf": pdf_data['pdf_name'],
                    "page": img['page'],
                    "embedding": embedding,
                    "image_b64": img['image_b64'],
                    "image_path": img['image_path'],
                    "metadata": json.dumps({
                        "type": "image",
                        "source": pdf_data['pdf_name'],
                        "page": img['page'],
                        "image_path": img['image_path'],
                        "image_b64": img['image_b64']
                    })
                })
            
            # Adicionar tabelas com descrições
            for table in pdf_data['tables']:
                # Criar embedding da descrição
                embedding = self.embeddings.embed_query(table['description'])
                
                all_documents.append({
                    "content": table['description'] + "\n" + table['table_csv'],
                    "content_type": "table",
                    "source_pdf": pdf_data['pdf_name'],
                    "page": table['page'],
                    "embedding": embedding,
                    "table_json": json.dumps(table['table_json']),
                    "table_csv": table['table_csv'],
                    "table_path": table['table_path'],
                    "metadata": json.dumps({
                        "type": "table",
                        "source": pdf_data['pdf_name'],
                        "page": table['page'],
                        "table_path": table['table_path'],
                        "rows": table['rows'],
                        "columns": table['columns']
                    })
                })
        
        print(f"✅ Criados {len(all_documents)} documentos para armazenamento")
        return all_documents
    
    def store_documents(self, documents: List[Dict[str, Any]], table_name: str = "multimodal_rag"):
        """Armazena documentos no LanceDB"""
        try:
            # Definir schema
            schema = pa.schema([
                pa.field("content", pa.string()),
                pa.field("content_type", pa.string()),
                pa.field("source_pdf", pa.string()),
                pa.field("page", pa.int32()),
                pa.field("embedding", pa.list_(pa.float32())),
                pa.field("metadata", pa.string()),
                pa.field("image_b64", pa.string(), nullable=True),
                pa.field("image_path", pa.string(), nullable=True),
                pa.field("table_json", pa.string(), nullable=True),
                pa.field("table_csv", pa.string(), nullable=True),
                pa.field("table_path", pa.string(), nullable=True),
            ])
            
            # Criar tabela
            if table_name in self.db.table_names():
                table = self.db.open_table(table_name)
                table.add(documents)
            else:
                table = self.db.create_table(table_name, documents)
            
            print(f"✅ {len(documents)} documentos armazenados em '{table_name}'")
            return table
            
        except Exception as e:
            print(f"❌ Erro ao armazenar documentos: {e}")
            return None
    
    def search(self, query: str, k: int = 5, content_type: Optional[str] = None):
        """Busca documentos similares"""
        try:
            # Criar embedding da query
            query_embedding = self.embeddings.embed_query(query)
            
            # Buscar na tabela
            table = self.db.open_table("multimodal_rag")
            
            # Buscar similares
            results = table.search(query_embedding).limit(k).to_pandas()
            
            # Filtrar por tipo se especificado
            if content_type:
                results = results[results['content_type'] == content_type]
            
            return results
            
        except Exception as e:
            print(f"❌ Erro na busca: {e}")
            return None


# Exemplo de uso com Agno
def criar_rag_multimodal_agno(pdfs_folder: str = "pdfs"):
    """
    Cria um sistema RAG multimodal completo para uso com Agno
    
    Passos:
    1. Processa PDFs extraindo texto, imagens e tabelas
    2. Armazena no LanceDB com metadados
    3. Retorna função de busca que pode ser usada no Agno
    """
    
    # 1. Processar PDFs
    processor = PDFMultimodalProcessor(pdfs_folder=pdfs_folder)
    processed_pdfs = processor.process_all_pdfs()
    
    if not processed_pdfs:
        return None
    
    # 2. Inicializar LanceDB
    store = LanceDBMultimodalStore()
    store.initialize_db()
    
    # 3. Criar documentos com metadados
    documents = store.create_documents_with_metadata(processed_pdfs)
    
    # 4. Armazenar no LanceDB
    store.store_documents(documents)
    
    # 5. Retornar função de busca para usar no Agno
    def search_function(query: str, k: int = 5):
        """Função de busca para usar no Agno Agent"""
        results = store.search(query, k=k)
        
        if results is None or len(results) == 0:
            return {"text": "Nenhum resultado encontrado", "images": [], "tables": []}
        
        # Organizar resultados por tipo
        response = {
            "text": "",
            "images": [],
            "tables": []
        }
        
        for _, row in results.iterrows():
            if row['content_type'] == 'text':
                response['text'] += f"\n\n{row['content']}"
            
            elif row['content_type'] == 'image':
                response['images'].append({
                    "description": row['content'],
                    "image_b64": row.get('image_b64', ''),
                    "image_path": row.get('image_path', ''),
                    "source": row['source_pdf'],
                    "page": row['page']
                })
            
            elif row['content_type'] == 'table':
                response['tables'].append({
                    "description": row['content'],
                    "table_csv": row.get('table_csv', ''),
                    "table_path": row.get('table_path', ''),
                    "source": row['source_pdf'],
                    "page": row['page']
                })
        
        return response
    
    return search_function, store


# Exemplo de integração com Agno AgentUI
def exemplo_uso_agno():
    """
    Exemplo de como usar o RAG multimodal no Agno AgentUI
    
    O AgentUI do Agno já tem suporte nativo para renderização de:
    - Imagens (base64 ou URLs)
    - Tabelas (HTML/Markdown)
    - Texto formatado
    """
    
    # Criar o sistema RAG
    search_function, store = criar_rag_multimodal_agno("pdfs")
    
    # Exemplo de resposta que o Agno pode processar
    def processar_consulta_agno(query: str):
        """Processa consulta e retorna formato compatível com AgentUI"""
        results = search_function(query, k=5)
        
        # Formato que o AgentUI pode renderizar
        response_parts = []
        
        # Adicionar texto
        if results['text']:
            response_parts.append({
                "type": "text",
                "content": results['text']
            })
        
        # Adicionar imagens (AgentUI renderiza automaticamente)
        for img in results['images']:
            response_parts.append({
                "type": "image",
                "src": f"data:image/png;base64,{img['image_b64']}",  # AgentUI aceita base64
                "alt": img['description'],
                "caption": f"Página {img['page']} de {img['source']}"
            })
        
        # Adicionar tabelas (AgentUI renderiza Markdown/HTML)
        for table in results['tables']:
            response_parts.append({
                "type": "table",
                "content": table['table_csv'],  # CSV que pode ser convertido para Markdown
                "caption": f"Página {table['page']} de {table['source']}"
            })
        
        return response_parts
    
    return processar_consulta_agno


if __name__ == "__main__":
    print("🚀 Sistema RAG Multimodal para PDFs")
    print("=" * 50)
    print("\n📋 Este exemplo demonstra:")
    print("  1. Extração de texto, imagens e tabelas de PDFs")
    print("  2. Armazenamento no LanceDB com metadados")
    print("  3. Integração com Agno AgentUI")
    print("\n💡 Para usar:")
    print("  1. Coloque seus PDFs na pasta 'pdfs'")
    print("  2. Execute: criar_rag_multimodal_agno()")
    print("  3. Use a função de busca no seu Agno Agent")
    print("\n✅ O AgentUI do Agno renderiza automaticamente:")
    print("  - Imagens (base64 ou URLs)")
    print("  - Tabelas (HTML/Markdown)")
    print("  - Texto formatado")

