# ✈️ AirFlow Lite

Versão simplificada do Apache Airflow para **execução e agendamento de scripts Python** via interface web, com controle de acesso por nível de usuário.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0+-green?logo=flask&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple?logo=bootstrap&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 Funcionalidades

### Dashboard
- Visão geral de todos os scripts cadastrados com status em tempo real
- Contadores de scripts ativos, em execução, execuções com sucesso e falhas
- Lista das últimas 10 execuções com link para detalhes
- **Atualização automática** a cada 3 segundos via polling AJAX

### Gestão de Scripts
- Cadastro de scripts Python referenciando o **caminho absoluto** do arquivo no servidor
- Validação do caminho: verifica se o arquivo existe, se tem extensão `.py` e se está em um diretório permitido (whitelist)
- Configuração de **agendamento cron** (ex: `0 8 * * *` para rodar todo dia às 08:00)
- **Timeout configurável** por script (padrão: 1 hora)
- Ativação/desativação de scripts sem excluí-los
- Histórico completo de execuções por script com estatísticas

### Execução de Scripts
- **Execução manual** via botão na interface (disponível para todos os usuários)
- **Execução agendada** via expressão cron (configurada pelo admin)
- **Bloqueio de execução simultânea**: se um script já está rodando, novas tentativas são registradas como `skipped`
- Captura completa de `stdout` e `stderr` com log armazenado no banco
- **Timeout automático**: processo é encerrado se exceder o tempo limite
- Recovery automático após crash: scripts presos como "running" são resetados ao reiniciar

### Controle de Acesso (2 níveis)

| Permissão | User | Admin |
|-----------|:----:|:-----:|
| Visualizar dashboard e scripts | ✅ | ✅ |
| Executar scripts manualmente | ✅ | ✅ |
| Ver logs e histórico de execuções | ✅ | ✅ |
| Cadastrar/editar/excluir scripts | ❌ | ✅ |
| Configurar agendamento cron | ❌ | ✅ |
| Ativar/desativar scripts | ❌ | ✅ |
| Gerenciar usuários | ❌ | ✅ |

### Logs e Monitoramento
- Log de saída em tempo real durante a execução (polling a cada 2s)
- Histórico de execuções com filtros por script e status
- Paginação no histórico (25 por página)
- Indicadores visuais de status: `running`, `success`, `failed`, `skipped`, `timeout`
- Duração calculada automaticamente
- Botão para copiar log para a área de transferência

---

## 🚀 Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/cristianprz/air-flow.git
cd air-flow
```

### 2. Criar ambiente virtual

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

Defina as variáveis diretamente no sistema operacional antes de executar.

> ⚠️ **Em produção, é obrigatório configurar pelo menos `SECRET_KEY` e `ALLOWED_SCRIPT_DIRS`.**

#### Windows (PowerShell)
```powershell
$env:SECRET_KEY = "sua-chave-secreta-aqui-mude-em-producao"
$env:DATABASE_URL = "sqlite:///C:/caminho/para/airflow_lite.db"
$env:ALLOWED_SCRIPT_DIRS = "C:\scripts\producao;D:\automacao\python"
$env:DEFAULT_TIMEOUT = "3600"
$env:MAX_LOG_SIZE = "51200"
```

#### Windows (CMD)
```cmd
set SECRET_KEY=sua-chave-secreta-aqui-mude-em-producao
set DATABASE_URL=sqlite:///C:/caminho/para/airflow_lite.db
set ALLOWED_SCRIPT_DIRS=C:\scripts\producao;D:\automacao\python
set DEFAULT_TIMEOUT=3600
set MAX_LOG_SIZE=51200
```

#### Linux / Mac
```bash
export SECRET_KEY="sua-chave-secreta-aqui-mude-em-producao"
export DATABASE_URL="sqlite:////home/user/airflow_lite.db"
export ALLOWED_SCRIPT_DIRS="/home/user/scripts;/opt/automacao/python"
export DEFAULT_TIMEOUT="3600"
export MAX_LOG_SIZE="51200"
```

### 5. Criar o usuário administrador

```bash
flask create-admin
```

O comando pedirá o username e senha interativamente.

### 6. Iniciar o servidor (desenvolvimento)

```bash
python run.py
```

> `run.py` é o servidor de **desenvolvimento** do Flask. O debugger só liga com `FLASK_DEBUG=1`.
> Para **produção** (Windows Server), use o Waitress via `serve.py` ou os scripts em `deploy/` (veja abaixo).

Acesse: **http://localhost:5000**

---

## 🖥️ Deploy em Windows Server (produção)

Em produção a aplicação roda com **Waitress** (servidor WSGI puro-Python, estável no Windows) e inicia
automaticamente no boot via **Agendador de Tarefas (Task Scheduler)**. Todos os scripts estão em `deploy/`.

> ⚠️ Rode **apenas uma instância** do servidor apontando para o mesmo banco. O scheduler de cron roda
> dentro do processo; múltiplos processos duplicariam as execuções agendadas. O Waitress usa *threads*
> (um único processo), então isso é respeitado por padrão.

### 1. Instalar

```cmd
deploy\setup.bat
```

O `setup.bat` cria a venv, instala as dependências, gera o `deploy\.env.bat` (com uma `SECRET_KEY`
aleatória) a partir de `deploy\.env.bat.example` e cria o usuário administrador interativamente.

### 2. Configurar variáveis

Edite **`deploy\.env.bat`** — em especial:

- `ALLOWED_SCRIPT_DIRS` — diretórios permitidos para scripts (whitelist de segurança).
- `DATABASE_URL` — caminho do banco (use um local fixo, ex.: `sqlite:///C:/airflow-lite/airflow_lite.db`).
- `HOST` / `PORT` — interface e porta do servidor.

> `deploy\.env.bat` contém segredos e **não** é versionado (está no `.gitignore`).

### 3. Testar

```cmd
deploy\start.bat
```

Abre o servidor em `http://HOST:PORT`. `Ctrl+C` para parar.

### 4. Inicialização automática no boot

Clique com o botão direito em **`deploy\install-task.bat`** → **Executar como administrador**.
Isso registra a tarefa `AirFlowLite` para iniciar no boot, sob a conta `SYSTEM` (não exige login).

Comandos úteis:

```cmd
schtasks /Run    /TN "AirFlowLite"     REM inicia agora
schtasks /Query  /TN "AirFlowLite"     REM ver status
schtasks /End    /TN "AirFlowLite"     REM parar
deploy\uninstall-task.bat              REM remover (como admin)
```

> Para reinício automático em caso de falha, abra o Agendador de Tarefas, edite `AirFlowLite` →
> aba **Configurações** → **Reiniciar a cada**.

---

## ⚙️ Variáveis de Ambiente

| Variável | Descrição | Padrão | Obrigatório em Produção |
|----------|-----------|--------|:-----------------------:|
| `SECRET_KEY` | Chave secreta para sessões e CSRF. Use uma string longa e aleatória. | `dev-secret-key-change-in-production` | ✅ |
| `DATABASE_URL` | URI de conexão com o banco de dados ([SQLAlchemy format](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls)). | `sqlite:///airflow_lite.db` (na raiz do projeto) | Recomendado |
| `ALLOWED_SCRIPT_DIRS` | Diretórios permitidos para scripts Python. Separe múltiplos com `;`. | `./scripts` (pasta scripts do projeto) | ✅ |
| `DEFAULT_TIMEOUT` | Timeout padrão de execução em segundos. Pode ser sobrescrito por script. | `3600` (1 hora) | Não |
| `MAX_LOG_SIZE` | Tamanho máximo do log armazenado por execução (em bytes). Logs maiores são truncados. | `51200` (50 KB) | Não |

### Gerando uma SECRET_KEY segura

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Exemplos de DATABASE_URL

```bash
# SQLite (padrão, arquivo local)
DATABASE_URL=sqlite:///airflow_lite.db

# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/airflow_lite

# MySQL
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/airflow_lite
```

### Configurando ALLOWED_SCRIPT_DIRS

Esta é a **whitelist de segurança** que restringe quais diretórios do servidor podem conter scripts executáveis. Ao cadastrar um script, o sistema verifica se o caminho informado está dentro de um dos diretórios permitidos.

```bash
# Um diretório
ALLOWED_SCRIPT_DIRS=C:\meus-scripts

# Múltiplos diretórios (separados por ;)
ALLOWED_SCRIPT_DIRS=C:\scripts\etl;C:\scripts\relatorios;D:\automacao
```

---

## 🕐 Agendamento Cron

Os scripts podem ser agendados usando **expressões cron** no formato de 5 campos:

```
┌───────────── minuto (0-59)
│ ┌───────────── hora (0-23)
│ │ ┌───────────── dia do mês (1-31)
│ │ │ ┌───────────── mês (1-12)
│ │ │ │ ┌───────────── dia da semana (0-6, 0=segunda)
│ │ │ │ │
* * * * *
```

### Exemplos

| Expressão | Descrição |
|-----------|-----------|
| `0 8 * * *` | Todo dia às 08:00 |
| `30 18 * * 0-4` | Segunda a sexta às 18:30 |
| `0 */2 * * *` | A cada 2 horas |
| `*/15 * * * *` | A cada 15 minutos |
| `0 9 1 * *` | Dia 1 de cada mês às 09:00 |
| `0 0 * * 6` | Todo domingo à meia-noite |

> ⚠️ **Atenção ao dia da semana:** o agendador (APScheduler) usa **0 = segunda-feira … 6 = domingo**
> (diferente do cron padrão do Unix, onde 0 = domingo). Ou seja, *Segunda a sexta* é `0-4` e *domingo* é `6`.
>
> O fuso horário utilizado é **America/Sao_Paulo (UTC-3)**.

---

## 🛠️ Comandos CLI

| Comando | Descrição |
|---------|-----------|
| `flask create-admin` | Cria um usuário administrador (interativo) |
| `flask reset-running` | Reseta scripts presos como "running" após crash do servidor |

---

## 📁 Estrutura do Projeto

```
air-flow/
├── app/
│   ├── __init__.py            # Flask app factory
│   ├── models.py              # Modelos: User, Script, Execution
│   ├── cli.py                 # Comandos CLI (create-admin, reset-running)
│   ├── utils.py               # Utilitários (fuso horário BRT)
│   ├── routes/
│   │   ├── auth.py            # Login, logout, gestão de usuários
│   │   ├── dashboard.py       # Dashboard e API de status
│   │   ├── scripts.py         # CRUD de scripts e execução manual
│   │   └── executions.py      # Histórico e detalhes de execuções
│   ├── scheduler/
│   │   └── engine.py          # APScheduler + subprocess executor
│   ├── templates/             # Templates Jinja2 + Bootstrap 5
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── scripts/
│   │   ├── executions/
│   │   └── users/
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── scripts/
│   └── exemplo.py             # Script de exemplo para testes
├── config.py                  # Configurações e variáveis de ambiente
├── run.py                     # Entry point da aplicação
├── requirements.txt           # Dependências Python
└── .gitignore
```

---

## 🔒 Segurança

- Senhas armazenadas com hash (`werkzeug.security`)
- Proteção CSRF em todos os formulários (`Flask-WTF`)
- Whitelist de diretórios para scripts (`ALLOWED_SCRIPT_DIRS`)
- Validação de caminhos: existência do arquivo e extensão `.py`
- Sessões gerenciadas por `Flask-Login`
- Em produção, **altere a `SECRET_KEY`** e use HTTPS

---

## 📦 Tecnologias

| Componente | Tecnologia |
|------------|-----------|
| Backend | Flask 3.x |
| Banco de Dados | SQLAlchemy + SQLite (dev) / PostgreSQL (prod) |
| Agendamento | APScheduler |
| Autenticação | Flask-Login |
| Frontend | Bootstrap 5 + Jinja2 |
| Fuso Horário | America/Sao_Paulo (UTC-3) |
