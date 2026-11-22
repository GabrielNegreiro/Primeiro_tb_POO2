# Integracao do desktop com a API de filmes

## Arquitetura

O fluxo conectado e:

```text
FilmesPage -> QThread -> FilmeApiService -> ApiClient/httpx
            -> FastAPI -> SQLAlchemy -> PostgreSQL
```

Nenhum handler de botao executa HTTP diretamente. A tela pesquisa titulo, genero e ano sobre o ultimo cache confirmado, evitando uma requisicao por tecla.

## Componentes

### ApiClient

`app/network/api_client.py` centraliza `GET`, `POST`, `PUT` e `DELETE`, URL-base, timeout de conexao/leitura, JSON e traducao de erros. Ele nao importa Qt, SQLAlchemy ou codigo do backend.

A URL segue esta prioridade:

1. argumento `base_url`;
2. variavel `LOCADORA_API_BASE_URL`;
3. `http://127.0.0.1:8000`.

### FilmeApiService

`app/services/filme_api_service.py` converte JSON em `app.models.filme.Filme` e mantem um cache em memoria. Seus metodos sao:

- `carregar_filmes`: consulta a colecao com filtros opcionais;
- `listar_filmes`: devolve uma copia do cache;
- `buscar_filmes`: filtra titulo, genero e ano localmente;
- `buscar_por_id`: consulta `/filmes/{id}`;
- `obter_filme`: busca apenas no cache;
- `adicionar_filme`: envia `POST /filmes`;
- `atualizar_filme`: rele o recurso e envia `PUT /filmes/{id}`;
- `remover_filme`: envia `DELETE /filmes/{id}`;
- `listar_disponiveis`: filtra o cache;
- `definir_disponibilidade`: bloqueia alteracoes originadas nas locacoes locais;
- `fechar`: libera o pool HTTP.

Uma lista vazia do PostgreSQL continua vazia. Os quatro filmes de exemplo nao sao recriados e falhas de conexao nao sao convertidas em lista vazia.

### Workers

`FilmeLoaderThread` chama `carregar_filmes()` fora da GUI e preserva os sinais `carregado` e `erro`.

`FilmeOperationThread` recebe uma funcao e seus argumentos para executar cadastro, edicao ou exclusao. A `FilmesPage` permite apenas um worker de operacao por vez, desabilita os botoes, mostra o estado, atualiza a tabela somente depois do sinal de sucesso e restaura os controles ao finalizar.

A `MainWindow` impede dois carregamentos simultaneos e aguarda, com timeout, carregamento, operacao de filme e exportacao antes de fechar.

## Fluxos

- Carregamento: `MainWindow` inicia `FilmeLoaderThread`; sucesso substitui o cache e atualiza FilmesPage e Dashboard.
- Cadastro: o dialogo valida os dados; um worker envia POST; somente a resposta 201 entra no cache.
- Edicao: a disponibilidade e somente leitura. O worker rele o filme, preserva o valor atual e envia PUT.
- Exclusao: a confirmacao ocorre na GUI; o worker envia DELETE; o cache so muda depois do 204.
- Pesquisa e filtros: executados localmente sobre dados confirmados pela API.

## Tratamento de erros

| Situacao | Mensagem publica |
|---|---|
| conexao | Nao foi possivel conectar ao servico de filmes |
| timeout | Nao foi possivel concluir a comunicacao no tempo esperado |
| JSON invalido | A API retornou uma resposta JSON invalida |
| HTTP 404 | Filme nao encontrado |
| HTTP 409 | Operacao impedida por regra de negocio |
| HTTP 422 | Dados informados sao invalidos |
| HTTP 500 | O servico encontrou um erro interno |
| HTTP 503 | O servico esta temporariamente indisponivel |

Detalhes de banco e credenciais enviados pelo servidor nao sao exibidos.

## Compatibilidade com locacoes

Nesta branch, o backend e o desktop de locacoes ainda nao estao integrados ao mesmo fluxo HTTP. A menor solucao segura foi:

- nao carregar `locacoes.csv` na `MainWindow` conectada;
- manter a pagina de locacoes visivel;
- desabilitar cadastro, edicao, devolucao e exclusao locais;
- exibir uma explicacao na pagina e no Dashboard;
- manter todos os arquivos e classes legados intactos.

O Dashboard mostra a quantidade de filmes disponiveis recebida da API. Indicadores de locacoes exibem `-` ate a integracao definitiva, evitando apresentar zero como dado confiavel.

## Disponibilidade

O dialogo conectado nao permite editar disponibilidade. Antes do PUT, o adapter rele o filme para preservar o valor mais recente. Ainda existe uma pequena janela de concorrencia entre GET e PUT porque `FilmeUpdate` aceita esse campo. A correcao definitiva deve remover a disponibilidade da edicao cadastral ou fazer o backend de locacoes validar a transacao de forma atomica.

## Testes

Os testes unitarios usam `httpx.MockTransport`, mocks e Qt offscreen; nao dependem de PostgreSQL. Os testes opcionais `tests/integration` usam `api_test`/`db_test`, dados sinteticos e removem os filmes criados.

```powershell
Push-Location locadora_filmes
python -m unittest discover -s tests -p "test_*.py" -v

$env:RUN_DESKTOP_API_INTEGRATION = "1"
$env:LOCADORA_TEST_API_BASE_URL = "http://127.0.0.1:8001"
python -m unittest discover -s tests/integration -p "test_*.py" -v
Pop-Location
```
