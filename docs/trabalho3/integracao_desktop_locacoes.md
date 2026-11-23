# Integração do desktop com a API de locações (Etapa 3)

Trabalho 3 de POO II (UFPI), Locadora de Filmes. Autor desta etapa: Nilson Bruno. Infraestrutura e filmes: Gabriel Negreiro.

## 1. Objetivo

Integrar o módulo de locações do desktop PySide6 à API FastAPI, de modo que o PostgreSQL seja a fonte de verdade. Cadastro, edição, devolução e exclusão de locações, o dashboard e a exportação TXT passam a usar dados da API.

## 2. Arquitetura

PySide6 -> HTTP/JSON -> FastAPI -> SQLAlchemy -> PostgreSQL (Docker).

- Toda chamada HTTP roda em `QThread`. Nenhum handler da interface faz rede.
- O `ApiClient` é um só e é compartilhado entre `FilmeApiService` e `LocacaoApiService`. O `closeEvent` da janela fecha o cliente uma vez.
- O cache em memória (`LocacaoApiService.locacoes` e `FilmeApiService.filmes`) só recebe dados confirmados pela API.

## 3. Arquivos

Novos (em `locadora_filmes/`):

- `app/models/locacao_api.py`: dataclass `LocacaoApi` e a função `titulo_do_filme`, que serve ao modelo legado e ao da API.
- `app/services/locacao_api_service.py`: `LocacaoApiService`, com consultas, escritas, cache e tradução de erros 404, 409 e 422.
- `app/workers/locacao_loader_thread.py`: `LocacaoLoaderThread`.
- `app/workers/locacao_operation_thread.py`: `LocacaoOperationThread`.
- `tests/test_locacao_api_service.py`, `tests/test_locacoes_page_http.py` e `tests/integration/test_locacoes_api_e2e.py`.

Alterados:

- `app/network/api_client.py`: `ApiHttpError` guarda o `detail` do backend em atributo, sem expô-lo na mensagem pública.
- `app/services/relatorio_service.py`, `app/views/dashboard_page.py`, `app/views/locacao_dialog.py`, `app/views/locacoes_page.py` e `app/views/main_window.py`.

## 4. Endpoints usados

- `GET /locacoes` e `GET /locacoes?situacao=ativas|atrasadas`
- `GET /locacoes/{id}`
- `POST /locacoes`
- `PUT /locacoes/{id}`
- `POST /locacoes/{id}/devolucao`
- `DELETE /locacoes/{id}`

## 5. Fluxo das operações

1. A página valida a seleção, que é feita pelo ID da locação (guardado em `Qt.UserRole`) e não pela posição da linha.
2. `LocacoesPage._executar_operacao` cria um `LocacaoOperationThread`. Enquanto ele roda, os botões ficam desabilitados e uma segunda operação é bloqueada.
3. O worker executa a escrita **uma única vez**. Em seguida chama `atualizar_filmes`, porque a disponibilidade dos filmes muda no servidor.
4. Se a escrita falha, o worker emite `erro` e a tela não muda. Se a escrita funciona mas a atualização do acervo falha, ele emite `sucesso_sem_atualizacao` e **nunca repete a escrita**.
5. Só depois da confirmação a página redesenha a tabela e emite `locacoes_alteradas`, que atualiza filmes, locações e dashboard a partir dos caches.

Regras de negócio refletidas na interface: o filme alugado deixa de aparecer entre os disponíveis; locação em aberto não pode ser excluída (a página avisa antes de chamar a API); na edição, o prazo conta a partir da data original da locação.

## 6. Tratamento de erros

- Erros 404, 409 e 422 são traduzidos para mensagens curtas. O `detail` do backend só é usado se tiver até 150 caracteres e não for o texto genérico "not found".
- Falha de conexão vira "Nao foi possivel conectar ao servico de locacoes."
- Se o carregamento das locações falha, o dashboard mostra "-" e a mensagem de erro, e não zeros.
- A exportação TXT é bloqueada enquanto as locações não foram carregadas da API.

## 7. Preservação do legado

`LocacaoService`, `LocacaoRepository`, os arquivos CSV/JSON e os testes antigos foram preservados. O `MainWindow(api_client=None, filme_service=None, locacao_service=None)` entra em modo HTTP quando recebe `api_client` ou `locacao_service`, ou quando é criada sem argumentos (caso do `main.py`). Com apenas um `filme_service` injetado, continua no modo pendente, com as locações bloqueadas. Isso mantém `test_main_window.py` e `test_close_event.py` válidos.

## 8. Testes e validação

Saídas obtidas em 22/11/2026, no Windows, com PowerShell:

- Desktop (`python -m unittest discover -s tests -p "test_*.py"`, dentro de `locadora_filmes`): `Ran 127 tests`, `OK (skipped=6)`. Os 6 pulados são os e2e, que exigem variável de ambiente.
- Backend unitário: `Ran 119 tests`, `OK`.
- Backend integração, com `RUN_POSTGRES_INTEGRATION=1` e a API de teste na porta 8001: filmes `Ran 1 test`, `OK`; locações `Ran 4 tests`, `OK`.
- Desktop e2e, com `RUN_DESKTOP_API_INTEGRATION=1`: `Ran 6 tests`, `OK`. Cobre o ciclo de locação pela interface (cadastro, filme indisponível, segunda locação rejeitada, devolução, nova locação, persistência com cliente novo, exportação TXT e dashboard), edição, devolução e exclusão pelo serviço, e o fechamento da janela com os loaders ativos.
- Validação visual, feita manualmente pelo autor em 22/11/2026 contra a API de teste (porta 8001, banco em tmpfs): cadastro de filme, locação, barreiras (filme alugado fora do combo e exclusão de locação aberta recusada), persistência após reiniciar o app, edição, devolução, exportação TXT pela caixa de salvar e exclusão. Todos os passos ocorreram como esperado.

Ambiente de teste: `docker compose --profile test up -d --build db_test api_test`.

## 9. Limitações conhecidas

- O botão "Atualizar" desenhado dentro do dashboard só redesenha a partir dos caches. O "Atualizar" da barra de ferramentas recarrega filmes e locações pela API. Correção possível: conectar o botão do dashboard a `atualizar_tudo` em `_conectar_integracao`, só no modo HTTP.
- Os workers gravam os caches fora da thread gráfica. Os botões ficam desabilitados durante a operação e a tela só redesenha após o sinal, mas o `_atualizar_cache` ordena a lista já publicada. Uma troca atômica da lista eliminaria a brecha teórica.
- Com a API fora do ar aparecem dois avisos seguidos (filmes e locações).
- "Movimentações recentes" usa as últimas 5 locações na ordem devolvida pela API.
- O teste e2e de exportação usa o `RelatorioService` diretamente. O botão com a caixa de salvar foi verificado só na validação visual manual.
- A tela com a API parada (tratamento visual de erro) não foi validada manualmente.