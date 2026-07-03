# 📁 DocFlow - Controle & Versionamento de Documentos

DocFlow é um sistema web desenvolvido em Python (Flask) para gerenciamento, comparação e aprovação de documentos tabulares (Excel/CSV). O DocFlow rastreia e compara novas versões diretamente contra a versão aprovada anterior armazenada no próprio banco de dados do sistema.

## 🚀 Fluxo de Trabalho
1. **Upload Inicial (v1):** O usuário faz o upload de uma planilha que se torna a versão base (v1), aprovada automaticamente.
2. **Nova Revisão (v2+):** O usuário envia uma nova planilha para o mesmo documento. O status entra como `PENDENTE`.
3. **Análise de Diferenças:** O sistema compara o conteúdo célula por célula com a última versão aprovada e exibe as alterações.
4. **Decisão:** O revisor aprova ou rejeita a nova versão com comentários.
5. **Histórico e Auditoria:** Todas as ações, mudanças e decisões são gravadas em uma trilha de auditoria imutável.

---

## 💻 Recursos do Sistema
- **Aparência Dark Premium:** Interface moderna baseada em glassmorphism com fontes Inter e visualização limpa.
- **Diferenças em Células:** Detecção de modificações nas coordenadas exatas (Ex: Célula B2 alterada de `100` para `120`).
- **Pré-visualização em Grid:** Veja as primeiras 15 linhas das planilhas diretamente no navegador sem precisar baixá-las.
- **Prevenção de Duplicidade:** O upload calcula o hash SHA-256 do arquivo e bloqueia uploads de conteúdos idênticos.
- **Histórico Completo:** Cada documento exibe sua linha do tempo de versões e comentários de aprovação.

---

## 🛠️ Início Rápido

### Pré-requisitos
- Python 3.12 ou superior
- Pip

### Configuração do Ambiente

```bash
# 1. Clonar ou navegar até a pasta
cd receipt-automation

# 2. Criar ambiente virtual
python3.13 -m venv venv

# 3. Ativar o ambiente virtual
source venv/bin/activate

# 4. Instalar as dependências do projeto
pip install -r requirements.txt
# Certifique-se de que sqlalchemy e werkzeug estejam em versões compatíveis (ex: SQLAlchemy>=2.0.25 para Python 3.13)
```

### Inicialização e Execução

```bash
# 1. Configurar variáveis de ambiente (.env)
# O banco de dados SQLite será criado automaticamente
cp .env.example .env

# 2. Iniciar o servidor Flask
python run_web.py
```

A aplicação estará acessível em: **http://localhost:5000**

---

## 📁 Estrutura de Diretórios
```
receipt-automation/
├── run_web.py             # Ponto de entrada da aplicação
├── requirements.txt       # Dependências do Python
├── .env                   # Variáveis de ambiente
├── test_doc_v1.csv        # Massa de teste versão 1
├── test_doc_v2.csv        # Massa de teste versão 2
├── app/
│   ├── __init__.py        # Inicialização do App Flask e DB
│   ├── config.py          # Configurações do app e SQLite
│   ├── models.py          # Modelos de dados (User, Document, Version, Comparison, AuditLog)
│   ├── templates/         # Interface e layouts de páginas
│   │   ├── base.html      # Tema e estilos CSS base (Dark Glassmorphism)
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   ├── upload.html
│   │   ├── report_view.html    # Tela de revisão e comparação detalhada
│   │   ├── document_list.html  # Lista de documentos
│   │   ├── document_history.html # Linha do tempo de versões do documento
│   │   ├── audit_logs.html     # Trilha de auditoria geral
│   │   └── profile.html        # Perfil e histórico do usuário
│   ├── services/          # Serviços de negócio
│   │   ├── document_service.py # Uploads, hashing, persistência
│   │   ├── comparator_service.py # Algoritmo de diff de planilhas
│   │   └── audit_service.py    # Geração de logs imutáveis
│   └── routes/            # Controladores de rota
│       ├── auth_routes.py
│       ├── document_routes.py
│       ├── audit_routes.py
│       └── main.py
```

---

## 🗄️ Modelo do Banco de Dados (SQLite)

- **User**: Informações de acesso, e-mail e hash da senha.
- **Document**: Container do documento criado, rastreando o autor e a data de criação.
- **DocumentVersion**: Contém os metadados do arquivo (tamanho, hash SHA-256), o status (`pending`/`approved`/`rejected`), comentários de decisão e os dados em formato JSON serializado na coluna `extracted_data`.
- **Comparison**: Armazena a contagem de diferenças e o dicionário de alterações entre a versão nova e a versão aprovada anterior.
- **AuditLog**: Tabela imutável que armazena a ação (ex: `login`, `upload`, `approve`), o IP do cliente e detalhes de auditoria.

---

## 🔒 Segurança e Conformidade
- **Hashing de Senhas:** Senhas criptografadas usando o algoritmo PBKDF2 via `werkzeug.security`.
- **Prevenção de Colisão:** Arquivos duplicados são detectados na origem via hash SHA-256 e impedidos de gerar novas versões redundantes.
- **Trilha de Auditoria:** Rastreabilidade completa de ações administrativas por endereço de IP e ID de usuário.
