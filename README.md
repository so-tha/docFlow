# 🐍 Loglife - Sistema Python de Relatórios

Sistema web simples em Python (Flask) para:
- ✅ Upload de relatórios (Excel, CSV, PDF)
- 🔍 Comparação automática com versão SharePoint
- ✅❌ Botões para Aceitar/Rejeitar mudanças
- 📝 Auditoria completa: quem fez o quê, quando e de onde
- 👥 Múltiplos usuários simultâneos
- 🔒 Autenticação e controle de acesso

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.9+
- pip

### Instalação

```bash
# 1. Clonar e entrar na pasta
cd loglife-python-app

# 2. Criar ambiente virtual
python -m venv venv

# 3. Ativar ambiente virtual
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate

# 4. Instalar dependências
pip install -r requirements.txt

# 5. Copiar e configurar arquivo .env
cp .env.example .env
# Editar .env com suas configurações

# 6. Inicializar banco de dados
python init_db.py

# 7. Rodar aplicação
python main.py
```

A aplicação estará em: **http://localhost:5000**

### Usuarios de Teste

**Padrão (criar novo usuário no registro):**
- Email: você@email.com
- Senha: sua-senha

## 📋 Funcionalidades

### 1. **Autenticação**
- Registro de novo usuário
- Login com email/senha
- Logout
- Perfil do usuário

### 2. **Upload de Relatório**
- Escolher arquivo (Excel, CSV, PDF)
- Validação de tipo e tamanho
- Armazenamento seguro com hash

### 3. **Comparação com SharePoint**
- Detecta diferenças célula por célula
- Mostra antes/depois
- Agrupa por planilha
- Marca linhas com alterações

### 4. **Aprovação/Rejeição**
- Botões Aceitar e Rejeitar
- Comentários obrigatórios/opcionais
- Registro automático de quem decidiu e quando

### 5. **Auditoria Completa**
- Cada ação é registrada:
  - Login/Logout
  - Upload de relatório
  - Comparação
  - Aprovação/Rejeição
  - Acesso a relatórios
- Mostra: Usuário, Ação, Data, Hora, IP
- Histórico por usuário
- Histórico por relatório

## 📁 Estrutura do Projeto

```
loglife-python-app/
├── main.py                 # Ponto de entrada
├── requirements.txt        # Dependências Python
├── .env                    # Variáveis de ambiente
├── init_db.py             # Script para criar banco de dados
├── app/
│   ├── __init__.py        # Factory Flask
│   ├── config.py          # Configurações
│   ├── models.py          # Modelos SQLAlchemy
│   ├── templates/         # Templates HTML
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   ├── upload.html
│   │   ├── report_view.html
│   │   ├── report_list.html
│   │   ├── audit_logs.html
│   │   ├── profile.html
│   │   └── error.html
│   ├── static/            # CSS, JS, imagens
│   ├── services/          # Lógica de negócio
│   │   ├── audit_service.py
│   │   ├── report_service.py
│   │   ├── comparator_service.py
│   │   └── sharepoint_service.py
│   └── routes/            # Rotas HTTP
│       ├── auth_routes.py
│       ├── report_routes.py
│       ├── audit_routes.py
│       └── main.py
├── uploads/               # Arquivos enviados (gitignore)
└── loglife.db            # Banco SQLite (gitignore)
```

## 🗄️ Banco de Dados

### Tabelas

**users**
- id, email, name, password_hash, is_active, created_at, updated_at

**reports**
- id, filename, original_filename, file_path, file_size, file_hash
- uploaded_by_id (FK users), status (pending/approved/rejected)
- approved_at, rejected_at, decision_by_id (FK users), decision_comment
- created_at, updated_at

**comparisons**
- id, report_id (FK reports), differences_count, differences_data (JSON)
- sharepoint_file_path, sharepoint_version, created_at

**audit_logs**
- id, user_id (FK users), action, entity_type, entity_id
- details (JSON), ip_address, user_agent, created_at

## 🔧 Configuração

Editar `.env`:

```env
# Flask
FLASK_ENV=development
SECRET_KEY=seu-secret-key-aqui

# Banco de dados
DATABASE_URL=sqlite:///loglife.db

# SharePoint (para integração futura)
SHAREPOINT_SITE_URL=https://seu-sharepoint.sharepoint.com
SHAREPOINT_LIBRARY=Documentos Compartilhados

# Azure AD (para integração futura)
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=

# Upload
MAX_CONTENT_LENGTH=52428800
UPLOAD_FOLDER=uploads
```

## 📊 Fluxo Típico

```
1. Usuário faz LOGIN
   └→ Auditoria: "login" gravada

2. Usuário ENVIA RELATÓRIO
   ├→ Arquivo armazenado
   └→ Auditoria: "upload" gravada

3. Sistema COMPARA com SharePoint
   ├→ Detecta diferenças
   └→ Auditoria: "view_comparison" gravada

4. Usuário ACEITA ou REJEITA
   ├→ Status do relatório atualizado
   ├→ Nome de quem decidiu registrado
   └→ Auditoria: "approve" ou "reject" gravada

5. Usuário consulta AUDITORIA
   └→ Vê histórico completo
```

## 🔒 Segurança

- ✅ Senhas com hashing (werkzeug)
- ✅ Session segura (cookies HTTP-only)
- ✅ CSRF protection (implementar)
- ✅ Auditoria de todas as ações
- ✅ Rastreamento de IP
- 📋 TODO: HTTPS em produção
- 📋 TODO: Rate limiting
- 📋 TODO: 2FA

## 🚀 Próximos Passos

### Para Produção
- [ ] Integração real com Azure AD
- [ ] Integração real com SharePoint (Graph API)
- [ ] HTTPS/SSL
- [ ] Backup automático do banco
- [ ] Rate limiting
- [ ] 2FA
- [ ] Logs em arquivo
- [ ] Deploy (Docker, Heroku, AWS)

### Features
- [ ] Notificações por email
- [ ] Exportar auditoria em PDF
- [ ] Busca avançada de relatórios
- [ ] Alertas automáticos
- [ ] Workflow de aprovação
- [ ] Versionamento de comparações
- [ ] API REST pública

## 📧 Suporte

Para dúvidas ou sugestões, entre em contato com a equipe de desenvolvimento.

## 📄 Licença

Propriedade da Loglife. Todos os direitos reservados.

---

