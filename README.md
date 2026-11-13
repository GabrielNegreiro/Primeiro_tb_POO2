# Locadora de Filmes - Trabalho 3 de POO II

O projeto combina a aplicação desktop existente em PySide6 com a infraestrutura inicial do Trabalho 3:

```text
PySide6 -> HTTP/JSON -> FastAPI -> SQLAlchemy -> PostgreSQL em Docker
```

Nesta etapa, o desktop ainda utiliza os repositórios dos trabalhos anteriores. O backend contém somente a infraestrutura e os endpoints de saúde; nenhum CRUD foi migrado.

## Estrutura

```text
.
|-- backend/
|   |-- app/
|   |   |-- config.py
|   |   |-- database.py
|   |   `-- main.py
|   |-- tests/
|   |   |-- unit/
|   |   `-- integration/
|   |-- Dockerfile
|   |-- requirements.txt
|   `-- requirements-dev.txt
|-- locadora_filmes/
|-- entregas/changelog_parcial_1.txt
|-- docker-compose.yml
`-- .env.example
```

## Tecnologias

- FastAPI e Uvicorn para a API HTTP.
- SQLAlchemy 2 para acesso ao banco.
- Psycopg 3 como driver PostgreSQL.
- PostgreSQL 16 em contêiner Docker.
- Docker Compose para orquestração.
- `unittest`, `TestClient` e PyYAML nos testes.

Foi mantido `unittest` por ser o framework já utilizado pelo projeto. Os testes que exigem PostgreSQL estão separados e desabilitados por padrão.

## Configuração local

Requisitos:

- Python 3.12 ou compatível.
- Docker Engine ou Docker Desktop com Docker Compose.

No PowerShell, a partir da raiz do repositório:

```powershell
Copy-Item .env.example .env
notepad .env
```

Troque obrigatoriamente `POSTGRES_PASSWORD`. O arquivo `.env` é ignorado pelo Git.

Valide e inicie os serviços:

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Consulte os endpoints:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/health/db
```

- `GET /health` verifica somente o processo da API.
- `GET /health/db` executa `SELECT 1` no PostgreSQL e retorna HTTP 503 com mensagem segura quando a conexão falha.
- A documentação interativa fica em `http://127.0.0.1:8000/docs`.

Para acompanhar os logs:

```powershell
docker compose logs --tail 100 api db
```

Para parar sem apagar o volume:

```powershell
docker compose down
```

Não use `docker compose down -v` se desejar preservar o banco.

## Testes

Instale as dependências de desenvolvimento:

```powershell
python -m pip install -r backend/requirements-dev.txt
python -m unittest discover -s backend/tests/unit -v
```

Com o Compose em execução, rode a integração real:

```powershell
$env:RUN_POSTGRES_INTEGRATION = "1"
$env:API_BASE_URL = "http://127.0.0.1:8000"
python -m unittest discover -s backend/tests/integration -v
Remove-Item Env:RUN_POSTGRES_INTEGRATION
Remove-Item Env:API_BASE_URL
```

Os testes não utilizam dados reais da locadora.

## Persistência e rede

O PostgreSQL grava seus dados no volume nomeado `postgres_data`. O serviço `db` não possui mapeamento de `ports`, portanto a porta 5432 não é publicada no host nem na internet. A API acessa o banco pelo hostname `db` na rede Docker interna `backend`.

Apenas a API publica uma porta. Por padrão, ela é vinculada a `127.0.0.1:8000` para evitar exposição acidental.

## Preparação para servidor remoto

Em um servidor Linux:

1. Instale Docker Engine e o plugin Docker Compose pelos repositórios oficiais da distribuição.
2. Transfira ou clone o projeto no servidor.
3. Copie `.env.example` para `.env` e defina uma senha forte e exclusiva.
4. Mantenha a porta 5432 bloqueada no firewall; ela não precisa ser liberada pelo Compose.
5. Execute `docker compose config --quiet` e `docker compose up -d --build`.
6. Verifique `docker compose ps`, os logs e os dois endpoints de saúde.
7. Confira o volume com `docker volume ls` e não use `down -v` em atualizações.
8. Para acesso por outro computador, configure `API_BIND_ADDRESS=0.0.0.0` somente quando houver firewall e proxy reverso.
9. Publique a API por HTTPS usando um proxy reverso, como Caddy, Nginx ou Traefik, com certificado válido.
10. Restrinja a API às redes e clientes necessários; não exponha diretamente o Uvicorn à internet pública.

O endereço IP, domínio, firewall, proxy HTTPS e persistência após uma reinicialização real do servidor precisam ser validados no ambiente remoto escolhido. A execução local em Docker não substitui essa validação.

## Integração futura do desktop

Nas próximas etapas, os repositórios de filmes e locações serão substituídos gradualmente por clientes HTTP. A interface PySide6 e os arquivos dos trabalhos anteriores permanecem inalterados nesta etapa.
