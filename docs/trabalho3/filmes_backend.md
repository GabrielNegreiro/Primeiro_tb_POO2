# Módulo de filmes do backend

## Visão geral

O módulo implementa `FastAPI -> Service -> Repository -> SQLAlchemy -> PostgreSQL`. A interface PySide6 ainda não consome a API.

## Model SQLAlchemy

`backend/app/models/base.py` declara a única `Base` compartilhada.

`Filme` representa `filmes`:

- `id`: chave primária gerada pelo banco;
- `titulo`: obrigatório, até 200 caracteres e indexado;
- `genero`: obrigatório, até 100 caracteres;
- `ano`: inteiro a partir de 1888;
- `duracao`: inteiro positivo;
- `disponivel`: booleano, verdadeiro por padrão e indexado.

A migração Alembic `20261120_01` cria a tabela sem alterar outras tabelas. A futura `locacoes.filme_id` deve referenciar `filmes.id` com `ON DELETE RESTRICT`.

## Schemas Pydantic

- `FilmeCreate`: valida cadastro e rejeita ID ou campos extras.
- `FilmeUpdate`: valida a atualização completa.
- `FilmeResponse`: serializa SQLAlchemy com `from_attributes=True`.

Título e gênero são limpos e não podem ficar vazios. Ano fica entre 1888 e o ano seguinte ao atual. Duração deve ser positiva.

## FilmeRepository

- `criar(dados)`: insere e obtém o ID com `flush`.
- `listar(titulo, disponivel)`: filtra e ordena por ID.
- `listar_disponiveis()`: retorna filmes livres.
- `buscar_por_id(filme_id)`: consulta a chave primária.
- `atualizar(filme, dados)`: aplica campos na transação.
- `excluir(filme)`: remove e converte violação de FK em conflito.
- `confirmar()`: efetiva a unidade de trabalho das rotas HTTP de filmes.

O repository somente executa commit quando o serviço controlador solicita. `get_session()` mantém rollback seguro para qualquer exceção e também confirma unidades de trabalho compartilhadas que terminem normalmente.

## FilmeService

- `criar(dados)`: cadastra dados validados.
- `listar(titulo, disponivel)`: delega filtros.
- `buscar_por_id(filme_id)`: sinaliza recurso inexistente.
- `atualizar(filme_id, dados)`: atualiza filme existente.
- `definir_disponibilidade(filme_id, disponivel)`: ponto compartilhado com locações.
- `excluir(filme_id)`: bloqueia filme indisponível ou referenciado.

Nas rotas próprias, `auto_commit=True` garante persistência antes da resposta HTTP. O padrão `auto_commit=False` permite que o módulo de locações use `definir_disponibilidade()` dentro da mesma transação da locação ou devolução.

As rotas convertem ausência em 404 e conflito em 409. Erros SQLAlchemy inesperados recebem 503 sem exposição de credenciais.

## Endpoints

| Método | Caminho | Sucesso |
|---|---|---|
| GET | `/filmes` | 200 |
| GET | `/filmes/{id}` | 200 |
| POST | `/filmes` | 201 |
| PUT | `/filmes/{id}` | 200 |
| DELETE | `/filmes/{id}` | 204 |

Os filtros `titulo` e `disponivel` podem ser combinados em `GET /filmes`.

## Testes

Testes unitários usam SQLite em memória e overrides do FastAPI. A integração usa `api_test` e `db_test`, porta 8001 e banco efêmero `locadora_test`.

Nenhum teste altera dados do desktop ou arquivos legados.
