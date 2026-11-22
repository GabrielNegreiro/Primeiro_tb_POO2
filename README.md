# Locadora de Filmes - Trabalho 3 de POO II

O projeto combina a aplicação desktop existente em PySide6 com a arquitetura:

```text
PySide6 -> HTTP/JSON -> FastAPI -> SQLAlchemy -> PostgreSQL em Docker
```

O módulo de filmes do desktop utiliza a API HTTP e o PostgreSQL. Os repositories JSON/CSV foram preservados apenas como legado e para os testes dos trabalhos anteriores; eles não são fallback silencioso no modo conectado.

## Estrutura

```text
.
|-- backend/
|   |-- app/
|   |   |-- models/filme.py
|   |   |-- schemas/filmes.py
|   |   |-- repositories/filmes.py
|   |   |-- services/filmes.py
|   |   |-- routers/filmes.py
|   |   |-- config.py
|   |   |-- database.py
|   |   `-- main.py
|   |-- alembic/versions/
|   |-- tests/
|   |   |-- unit/
|   |   `-- integration/
|   |-- Dockerfile
|   |-- requirements.txt
|   `-- requirements-dev.txt
|-- docs/trabalho3/filmes_backend.md
|-- locadora_filmes/
|-- docker-compose.yml
`-- .env.example
```

## Tecnologias

- FastAPI e Uvicorn para HTTP.
- SQLAlchemy 2 e Psycopg 3 para PostgreSQL.
- Alembic para migrações versionadas.
- PostgreSQL 16 em Docker.
- `unittest`, TestClient, SQLite e PyYAML nos testes unitários.
- `httpx` no cliente HTTP do desktop.

Foi mantido `unittest` por ser o framework já utilizado no projeto. Testes que exigem PostgreSQL ficam separados e desabilitados por padrão.

## Configuração local

Requisitos: Python 3.12 e Docker com Docker Compose.

```powershell
Copy-Item .env.example .env
notepad .env
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Troque `POSTGRES_PASSWORD` antes da primeira inicialização. `.env` é ignorado pelo Git.

## Endpoints de saúde

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/health/db
```

- `/health` verifica somente o processo da API.
- `/health/db` executa `SELECT 1` e retorna 503 com mensagem segura quando o banco falha.
- Swagger: `http://127.0.0.1:8000/docs`.

## API de filmes

| Método | Endpoint | Resultado |
|---|---|---|
| `GET` | `/filmes` | Lista filmes |
| `GET` | `/filmes/{id}` | Consulta por ID |
| `GET` | `/filmes?titulo=matrix` | Pesquisa parcial por título |
| `GET` | `/filmes?disponivel=true` | Filtra disponibilidade |
| `POST` | `/filmes` | Cadastra, HTTP 201 |
| `PUT` | `/filmes/{id}` | Atualiza, HTTP 200 |
| `DELETE` | `/filmes/{id}` | Exclui, HTTP 204 |

Recursos ausentes retornam 404. Filme alugado ou referenciado por locações retorna 409 na exclusão. Dados inválidos retornam 422. Falhas inesperadas de banco retornam 503 sem detalhes sensíveis.

Fluxo: `router -> FilmeService -> FilmeRepository -> Session SQLAlchemy -> PostgreSQL`. As rotas de filmes confirmam a transação antes de responder; qualquer exceção provoca rollback no encerramento da sessão.

## Migrações

O contêiner executa `alembic upgrade head` antes do Uvicorn. A revisão `20261120_01` cria `filmes`, checks e índices sem remover tabelas existentes.

```powershell
docker compose exec api alembic current
```

## Testes

```powershell
python -m pip install -r backend/requirements-dev.txt
python -m unittest discover -s backend/tests/unit -v
```

Integração PostgreSQL isolada:

```powershell
docker compose --profile test up -d --build db_test api_test
$env:RUN_POSTGRES_INTEGRATION = "1"
$env:API_BASE_URL = "http://127.0.0.1:8001"
$env:FILMES_TEST_API_BASE_URL = "http://127.0.0.1:8001"
python -m unittest discover -s backend/tests/integration -v
Remove-Item Env:RUN_POSTGRES_INTEGRATION
Remove-Item Env:API_BASE_URL
Remove-Item Env:FILMES_TEST_API_BASE_URL
```

O perfil `test` usa `locadora_test` em armazenamento efêmero. Os testes não acessam JSON, CSV ou dados reais da locadora.

## Persistência e rede

O banco principal usa o volume `postgres_data`. `db` não publica a porta 5432 no host. A API acessa o PostgreSQL pelo hostname `db` na rede interna. Somente a API publica porta, vinculada por padrão a `127.0.0.1:8000`.

```powershell
docker compose logs --tail 100 api db
docker compose down
```

Não use `docker compose down -v` se desejar preservar o banco.

## Integração com locações

`backend.app.models.Base` é a Base SQLAlchemy compartilhada. O model de locações deve referenciar `filmes.id` com `ON DELETE RESTRICT`. `FilmeService.definir_disponibilidade()` permite que locação e devolução atualizem o filme na mesma sessão e transação. Para isso, o módulo de locações deve instanciar o serviço com o padrão `auto_commit=False`; somente as rotas próprias de filmes usam `auto_commit=True`.

A branch de locações ainda não está integrada nesta árvore. Nenhum schema ou arquivo de Nilson foi alterado.

## Servidor remoto

Em Linux, instale Docker, configure `.env`, mantenha 5432 bloqueada e publique a API por proxy reverso HTTPS. IP, domínio, firewall, certificado e persistência após reinicialização real ainda precisam ser validados no servidor escolhido; Docker local não comprova implantação remota.

## Etapa 3

O desktop cria `ApiClient` e `FilmeApiService` na `MainWindow`. O carregamento, cadastro, edição e exclusão são executados por QThreads; pesquisa por título, gênero e ano e filtro de disponibilidade usam o cache confirmado pela API.

```powershell
python -m pip install -r locadora_filmes/requirements.txt
$env:LOCADORA_API_BASE_URL = "http://127.0.0.1:8000"
python locadora_filmes/main.py
Remove-Item Env:LOCADORA_API_BASE_URL
```

Se a variável não for definida, o endereço padrão é `http://127.0.0.1:8000`. Detalhes de classes, workers, erros e limitações estão em `docs/trabalho3/integracao_desktop_filmes.md`.

Enquanto a API de locações não estiver integrada nesta branch, a tela correspondente permanece visível, mas suas operações ficam desabilitadas no modo HTTP. Assim, o CSV legado não altera silenciosamente a disponibilidade mantida pelo PostgreSQL.

Testes do desktop:

```powershell
Push-Location locadora_filmes
python -m unittest discover -s tests -p "test_*.py" -v

$env:RUN_DESKTOP_API_INTEGRATION = "1"
$env:LOCADORA_TEST_API_BASE_URL = "http://127.0.0.1:8001"
python -m unittest discover -s tests/integration -p "test_*.py" -v
Remove-Item Env:RUN_DESKTOP_API_INTEGRATION
Remove-Item Env:LOCADORA_TEST_API_BASE_URL
Pop-Location
```
