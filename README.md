# Locadora de Filmes — Trabalho 3 de POO II

Projeto acadêmico da disciplina **Programação Orientada a Objetos II**, do Bacharelado em Sistemas de Informação da **Universidade Federal do Piauí (UFPI), Campus Senador Helvídio Nunes de Barros (Picos–PI)**.

**Autores:** Gabriel Santana Paz Landim Negreiros e Nilson Bruno dos Santos Lima.

A aplicação é uma locadora de filmes com **interface desktop PySide6**, **API REST FastAPI** e persistência em **PostgreSQL 16**, executado em contêineres Docker. O Trabalho 3 continua os trabalhos anteriores, mantendo funcionalidades de filmes, locações, dashboard e exportação de relatório TXT.

## Arquitetura

```text
Aplicação desktop (Python + PySide6)
   ├── Telas: Início/Dashboard, Filmes e Locações
   ├── Serviços: FilmeApiService e LocacaoApiService
   ├── QThread: carregamentos, operações e exportação TXT
   └── ApiClient (httpx)
           │ HTTP/JSON
           ▼
API REST (FastAPI + Pydantic)
   ├── Rotas /filmes e /locacoes
   ├── Regras de negócio (services)
   ├── Acesso a dados (repositories + SQLAlchemy)
   └── Migrações Alembic
           │ rede interna do Docker
           ▼
PostgreSQL 16 (volume persistente)
```

O **desktop não acessa o PostgreSQL diretamente**: solicita operações à API HTTP, que valida os dados, executa as regras de negócio e utiliza SQLAlchemy para acessar o banco. As operações de rede executadas pela interface utilizam workers para evitar bloquear a janela principal.

## Funcionalidades

### Filmes

- Cadastrar, consultar, pesquisar, editar e excluir filmes.
- Filtrar filmes por disponibilidade.
- Impedir exclusão quando houver impedimento de negócio, incluindo vínculo com locações.
- Manter a disponibilidade sincronizada com as locações.

### Locações

- Cadastrar, consultar e editar locações em aberto.
- Registrar devoluções e liberar filmes quando cabível.
- Excluir somente locações já devolvidas.
- Consultar locações **todas**, **ativas** ou **atrasadas**.
- Impedir mais de uma locação em aberto para o mesmo filme, inclusive por restrição de unicidade parcial no PostgreSQL.
- Exibir indicadores e movimentações recentes no dashboard.
- Exportar relatório de locações em **TXT**.

### Persistência e evolução dos trabalhos

Nos trabalhos anteriores, filmes eram gravados em **JSON** e locações em **CSV**. Esses componentes permanecem no repositório para compatibilidade e testes históricos, mas **não são a fonte de dados do modo HTTP conectado**. No Trabalho 3, filmes e locações são persistidos no PostgreSQL. O arquivo TXT continua útil como formato de exportação, não como banco operacional.

## Tecnologias

| Camada | Tecnologias |
|---|---|
| Interface | Python 3, PySide6 (Qt) |
| Comunicação desktop–API | HTTP/JSON, httpx |
| Backend | FastAPI, Uvicorn, Pydantic |
| Persistência | PostgreSQL 16, SQLAlchemy 2, Psycopg 3 |
| Migrações | Alembic |
| Contêineres | Docker e Docker Compose |
| Testes | unittest, mocks, TestClient, SQLite e PostgreSQL isolado |

## Estrutura do repositório

```text
.
├── backend/
│   ├── app/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models/          # Filme, Locacao e Base
│   │   ├── schemas/         # Validação e contratos Pydantic
│   │   ├── repositories/    # Persistência SQLAlchemy
│   │   ├── services/        # Regras de negócio e transações
│   │   └── routers/         # Endpoints de filmes e locações
│   ├── alembic/versions/    # Migrações de filmes e locações
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── requirements-dev.txt
├── locadora_filmes/
│   ├── app/
│   │   ├── data/            # Persistência legada em arquivos
│   │   ├── models/
│   │   ├── network/         # ApiClient
│   │   ├── services/        # Adaptadores HTTP e exportação TXT
│   │   ├── views/           # Janela e páginas PySide6
│   │   ├── widgets/
│   │   └── workers/         # QThreads de carga e operações
│   ├── tests/
│   │   └── integration/
│   ├── main.py
│   └── requirements.txt
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

As antigas pastas `docs/` e `entregas/` foram removidas do repositório. Isso não afeta o código executável. O relatório acadêmico em PDF e o código-fonte devem ser organizados separadamente para a entrega da disciplina.

## Executar no Windows (PowerShell)

**Pré-requisitos:** Python 3.12 (recomendado), Docker Desktop com Docker Compose e Git.

### 1. Clonar e configurar

```powershell
git clone https://github.com/GabrielNegreiro/Primeiro_tb_POO2.git
cd Primeiro_tb_POO2
Copy-Item .env.example .env
notepad .env
```

Preencha `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD` no `.env`; **substitua a senha de exemplo por uma senha forte**. O `.env` não deve ser versionado.

### 2. Iniciar a API e o PostgreSQL

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Espere os serviços `db` e `api` ficarem com status **healthy**. A API aplica as migrações Alembic antes de iniciar o servidor Uvicorn.

Verifique:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/health/db
```

**Swagger / documentação interativa da API:** http://127.0.0.1:8000/docs

### 3. Instalar dependências e abrir o desktop

```powershell
python -m pip install -r locadora_filmes/requirements.txt
$env:LOCADORA_API_BASE_URL = "http://127.0.0.1:8000"
python locadora_filmes/main.py
```

A URL é opcional quando a API está em `http://127.0.0.1:8000`, que já é o endereço padrão. Para conectar a outra API, configure `LOCADORA_API_BASE_URL` com o endereço apropriado.

### 4. Encerrar os contêineres

```powershell
docker compose down
```

**Não use `docker compose down -v`**, pois a opção `-v` remove volumes e pode apagar os dados do PostgreSQL.

## Endpoints da API

### Filmes

| Método | Rota | Descrição |
|---|---|---|
| GET | `/filmes` | Lista filmes; filtros opcionais `titulo` e `disponivel` |
| GET | `/filmes/{filme_id}` | Consulta um filme |
| POST | `/filmes` | Cadastra um filme |
| PUT | `/filmes/{filme_id}` | Atualiza um filme |
| DELETE | `/filmes/{filme_id}` | Exclui um filme, se permitido |

### Locações

| Método | Rota | Descrição |
|---|---|---|
| GET | `/locacoes` | Lista locações; filtro `situacao=todas|ativas|atrasadas` |
| GET | `/locacoes/{locacao_id}` | Consulta uma locação |
| POST | `/locacoes` | Registra uma locação |
| PUT | `/locacoes/{locacao_id}` | Edita uma locação em aberto |
| POST | `/locacoes/{locacao_id}/devolucao` | Registra devolução |
| DELETE | `/locacoes/{locacao_id}` | Exclui uma locação devolvida |

As rotas utilizam, conforme o caso, respostas HTTP **200, 201 e 204**; erros como **404** (não encontrado), **409** (conflito), **422** (entrada inválida) e **503** (indisponibilidade do banco).

## Banco de dados e integridade

- A migração `20261120_01` cria a tabela `filmes`.
- A migração `20261120_02` cria a tabela `locacoes`, com chave estrangeira `filme_id` referenciando `filmes.id`.
- `ON DELETE RESTRICT` protege a referência entre locação e filme.
- Restrições de datas e índice único parcial impedem inconsistências, como duas locações abertas para um mesmo filme.
- Registro, edição e devolução de locações atualizam o estado do filme na **mesma transação**; em caso de erro, ocorre rollback.
- Operações concorrentes utilizam bloqueio de registros (`SELECT ... FOR UPDATE`) nas regras de locação.

Para conferir a versão das migrações e o acesso ao banco:

```powershell
docker compose exec api alembic current
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"'
```

O banco principal usa um volume persistente chamado `postgres_data`. O serviço `db` não publica a porta `5432` para a máquina hospedeira: a API o acessa pelo hostname `db` na rede interna do Compose.

## Testes

Os testes automatizados do backend e do desktop são mantidos em diretórios separados. A suíte padrão não precisa de uma instância real de PostgreSQL; os testes E2E exigem o ambiente de testes isolado.

### Backend — testes unitários

```powershell
python -m pip install -r backend/requirements-dev.txt
python -m unittest discover -s backend/tests/unit -v
```

### Desktop — testes unitários e de interface

```powershell
Push-Location locadora_filmes
python -m unittest discover -s tests -p "test_*.py" -v
Pop-Location
```

### Integração real com PostgreSQL e API de testes

```powershell
docker compose --profile test up -d --build db_test api_test
Invoke-RestMethod http://127.0.0.1:8001/health/db

$env:RUN_POSTGRES_INTEGRATION = "1"
$env:API_BASE_URL = "http://127.0.0.1:8001"
$env:FILMES_TEST_API_BASE_URL = "http://127.0.0.1:8001"
python -m unittest discover -s backend/tests/integration -v

$env:RUN_DESKTOP_API_INTEGRATION = "1"
$env:LOCADORA_TEST_API_BASE_URL = "http://127.0.0.1:8001"
Push-Location locadora_filmes
python -m unittest discover -s tests/integration -p "test_*.py" -v
Pop-Location

Remove-Item Env:RUN_POSTGRES_INTEGRATION -ErrorAction SilentlyContinue
Remove-Item Env:RUN_DESKTOP_API_INTEGRATION -ErrorAction SilentlyContinue
Remove-Item Env:API_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:FILMES_TEST_API_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:LOCADORA_TEST_API_BASE_URL -ErrorAction SilentlyContinue
```

O perfil `test` executa `db_test` com banco `locadora_test` efêmero e `api_test` na porta `8001`. **Não utilize o banco principal para testes destrutivos.**

Na execução local previamente registrada durante a integração, a suíte padrão apresentou **119 testes de backend aprovados** e **127 casos de desktop (121 aprovados e 6 ignorados por dependerem do ambiente E2E)**. Esses números descrevem aquela execução, não uma garantia automática para commits futuros.

## Desenvolvimento em dupla

- **Gabriel Santana Paz Landim Negreiros:** infraestrutura Docker/PostgreSQL, backend e integração de filmes, além de contribuições na janela principal e integração geral.
- **Nilson Bruno dos Santos Lima:** modelagem, API e integração de locações, além de dashboard, telas de locação e funcionalidades relacionadas.
- **Integração final:** união dos módulos de filmes e locações no fluxo HTTP, sincronização do dashboard e testes.

## Implantação remota

O `docker-compose.yml` permite executar PostgreSQL e API em contêineres. **A validação da execução local em Docker não comprova que o banco já foi implantado em um servidor remoto**, exigência específica do Trabalho 3.

Para uma implantação remota, é necessário configurar um host apropriado, persistência e acesso seguro à API, idealmente com proxy reverso HTTPS. A porta do PostgreSQL não deve ser exposta publicamente; valide também firewall, domínio/certificado e reinicialização dos serviços antes de declarar a implantação concluída.

## Resolução de problemas

- **`POSTGRES_DB is missing a value`:** crie `.env` a partir de `.env.example` e preencha as variáveis obrigatórias.
- **API indisponível:** confira `docker compose ps` e `docker compose logs --tail 100 api db`.
- **Desktop não carrega os dados:** verifique `/health/db` e a variável `LOCADORA_API_BASE_URL`.
- **Banco não aparece no navegador:** PostgreSQL é um servidor de banco, não uma interface web; utilize um cliente como Adminer ou pgAdmin conectado de forma segura.
- **Mudou a senha no `.env` após inicializar o volume:** a senha armazenada no PostgreSQL não muda automaticamente; altere também a credencial no próprio banco, sem excluir o volume.
