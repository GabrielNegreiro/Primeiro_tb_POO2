# Modelagem do módulo de locações — Trabalho 3 de POO II

Autor: Nilson Bruno · Branch: `feature/nilson-locacoes-api` · Etapa 1 (preparação e modelagem)

> Escopo desta etapa: análise, modelagem, schemas Pydantic, contrato da API e testes dos schemas. Models SQLAlchemy, repositories, services e endpoints ficam para a Etapa 2.

## 1. Descrição do módulo de locações

Base: código do Trabalho 2 (`locadora_filmes/app`), arquitetura atual desktop PySide6 com persistência em CSV (locações) e JSON (filmes).

| Componente | Arquivo | Papel |
|---|---|---|
| Modelo | `models/locacao.py` | `Locacao`: filme, cliente_nome, data_locacao (padrão hoje), data_devolucao_prevista, data_devolucao_real |
| Serviço | `services/locacao_service.py` | Regras de criar, editar, devolver, excluir e listar |
| Repositório | `data/locacao_repository.py` | Leitura e gravação do `locacoes.csv` |
| Tela | `views/locacoes_page.py` | Tabela, botões e exportação |
| Diálogo | `views/locacao_dialog.py` | Formulário de cadastro e edição |
| Exportação | `views/exportar_thread.py`, `services/relatorio_service.py` | Relatório TXT em `QThread` |

Comportamento atual:

- **Status:** `Devolvido` se há data de devolução real, senão `Em aberto`.
- **Atrasada:** não devolvida, com data prevista, e hoje posterior à data prevista.
- **Criação:** `criar_locacao(filme, cliente_nome, dias_previstos=7)`. O filme precisa estar disponível (senão `ValueError`). A data prevista é hoje + dias. O filme fica indisponível.
- **Edição:** somente locação em aberto. Nome não vazio, prazo de pelo menos 1 dia. Ao trocar o filme, o anterior volta a ficar disponível e o novo, indisponível. A nova data prevista é `data_locacao + dias`.
- **Devolução:** `ValueError` se já devolvida. Registra a data real (hoje) e libera o filme.
- **Exclusão:** somente locação já devolvida.
- **Listagens:** todas, ativas (em aberto) e atrasadas.
- **Disponibilidade ao carregar:** vem das locações (`_sincronizar_disponibilidade`), porque o `filmes.json` pode estar desatualizado.
- **CSV:** colunas `filme_id`, `cliente_nome`, `data_locacao`, `data_devolucao_prevista`, `data_devolucao_real`, datas em ISO. Locações de filmes que não existem mais são ignoradas na leitura.
- **Interface:** tabela de 5 colunas (Filme, Cliente, Locação, Prevista, Status). O diálogo pede filme, cliente e dias (de 1 a 30, padrão 7). A exclusão pede confirmação. A exportação roda em thread.
- **Relatório TXT:** cabeçalho, um bloco por locação (Filme, Cliente, Locação, Prevista, Devolução, com `-` se vazia, e Status) e o total de locações. Esse comportamento deve ser preservado.

## 2. Relacionamento com filmes

O filme tem `id`, `titulo`, `genero`, `ano`, `duracao` e `disponivel`.

- Um filme pode aparecer em várias locações históricas.
- Cada locação pertence a um único filme.
- Um filme não pode ter duas locações abertas ao mesmo tempo.
- A devolução devolve a disponibilidade ao filme quando não houver outra locação aberta.
- A exclusão de filme com histórico não apaga as locações. A proposta é bloquear a exclusão (`ON DELETE RESTRICT`), a alinhar com o Gabriel.

## 3. Tabela `locacoes` (planejada)

| Campo | Tipo | Regra |
|---|---|---|
| id | INTEGER | Chave primária, gerada pelo banco |
| filme_id | INTEGER | Obrigatório, chave estrangeira para `filmes(id)` |
| cliente_nome | VARCHAR | Obrigatório, não vazio |
| data_locacao | DATE | Obrigatório |
| data_devolucao_prevista | DATE | Obrigatório, maior ou igual à data da locação |
| data_devolucao_real | DATE | Nulo enquanto aberta, maior ou igual à data da locação |

Restrições planejadas:

- Chave estrangeira `filme_id` para `filmes(id)`, com `ON DELETE RESTRICT`.
- `CHECK` das duas datas em relação a `data_locacao`.
- Índice único parcial em `filme_id` onde `data_devolucao_real IS NULL`, para impedir duas locações abertas do mesmo filme.

A definição final depende do model SQLAlchemy de filmes do Gabriel. Não será criada outra tabela de filmes.

## 4. Schemas Pydantic (`backend/app/schemas/locacoes.py`)

| Schema | Uso | Campos | Observações |
|---|---|---|---|
| `LocacaoCreate` | corpo do POST | `filme_id` (inteiro > 0), `cliente_nome`, `data_locacao` (padrão hoje), `data_devolucao_prevista` | Prevista não anterior à locação. Rejeita `id`, `status` e `atrasada` |
| `LocacaoUpdate` | corpo do PUT | `filme_id`, `cliente_nome`, `data_devolucao_prevista` | A data da locação não pode ser alterada |
| `LocacaoDevolucaoRequest` | corpo da devolução | `data_devolucao_real` (opcional) | Sem data, usa hoje |
| `LocacaoResponse` | resposta | `id`, `filme_id`, `cliente_nome`, as três datas, `status`, `atrasada` | `status` é `Em aberto` ou `Devolvido`; valida a ordem das datas |
| `FiltroLocacao` | parâmetro `situacao` | `todas`, `ativas`, `atrasadas` | Espelha as três listagens |

Os schemas representam os dados da API. Os models SQLAlchemy da Etapa 2 representarão as tabelas.

## 5. Contrato dos endpoints

Erros seguem o formato padrão do FastAPI: `{"detail": "mensagem"}`.

| Método | Endpoint | Sucesso | Erros |
|---|---|---|---|
| GET | `/locacoes?situacao=todas` | 200, lista de `LocacaoResponse` | 422 se `situacao` inválida |
| GET | `/locacoes/{id}` | 200 | 404 locação não encontrada |
| POST | `/locacoes` | 201, `LocacaoResponse` | 404 filme não existe; 409 filme indisponível; 422 dados inválidos |
| PUT | `/locacoes/{id}` | 200 | 404 locação ou filme; 409 locação devolvida ou filme indisponível; 422 dados inválidos |
| POST | `/locacoes/{id}/devolucao` | 200 | 404 locação; 409 já devolvida; 422 data anterior à locação |
| DELETE | `/locacoes/{id}` | 204, sem corpo | 404 locação; 409 ainda não devolvida |

Exemplo de `POST /locacoes`:

```json
{
  "filme_id": 3,
  "cliente_nome": "Ana",
  "data_locacao": "2026-11-13",
  "data_devolucao_prevista": "2026-11-20"
}
```

Resposta `201`:

```json
{
  "id": 10,
  "filme_id": 3,
  "cliente_nome": "Ana",
  "data_locacao": "2026-11-13",
  "data_devolucao_prevista": "2026-11-20",
  "data_devolucao_real": null,
  "status": "Em aberto",
  "atrasada": false
}
```

Exemplo de `POST /locacoes/10/devolucao` (o corpo pode ser `{}` para usar a data de hoje):

```json
{ "data_devolucao_real": "2026-11-18" }
```

Critério dos códigos: **404** quando o recurso não existe; **409** quando o pedido é válido mas o estado atual não permite; **422** quando o conteúdo do pedido é inválido. Filme inexistente no corpo do POST retorna 404, e a alternativa seria 422.

## 6. Validações

No schema: tipos, `filme_id` positivo, nome não vazio e sem espaços nas pontas, datas reais, ordem das datas na criação, campos desconhecidos rejeitados, resposta coerente.

No service (Etapa 2), por dependerem do estado salvo:

- A nova data prevista da edição não pode anteceder a `data_locacao` da locação.
- A data real da devolução não pode anteceder a `data_locacao` da locação.
- Existência e disponibilidade do filme.
- Locação já devolvida e exclusão de locação aberta.

## 7. Regras de negócio a preservar

- **Cadastro:** o filme existe e está disponível. A locação é registrada e o filme fica indisponível.
- **Devolução:** a locação existe, não foi devolvida antes, a data real é salva e o filme volta a ficar disponível quando não houver outra locação aberta.
- **Atraso:** locação não devolvida cuja data prevista já passou.
- **Exclusão:** só de locação devolvida. O histórico não é apagado automaticamente.
- **Transação:** cadastro, devolução e atualização da disponibilidade devem acontecer na mesma transação, sem alterações parciais.

## 8. CSV e PostgreSQL

| Aspecto | Trabalho 2 (CSV) | Trabalho 3 (PostgreSQL) |
|---|---|---|
| Identificador | Não existe (posição na lista) | `id` gerado pelo banco |
| Relação com filme | `filme_id` em texto, sem garantia | Chave estrangeira |
| Disponibilidade | Recalculada ao carregar | Atualizada junto com a locação, na transação |
| Duas locações abertas do mesmo filme | Evitado só pela regra do service | Também impedido por índice único parcial |
| Prazo | Informado em dias (1 a 30 na tela) | Informado como data prevista |
| Prazo mínimo | Pelo menos 1 dia | Data prevista igual à locação é aceita |
| Acesso | Direto ao arquivo | Pela API FastAPI |
| Exportação TXT | `RelatorioService` | Continua como arquivo de saída |

O `LocacaoRepository` e o `locacoes.csv` permanecem como recurso legado. Não haverá gravação duplicada em CSV e banco.

## 9. Responsabilidades dos componentes

- **Schemas:** validam e descrevem os dados da API.
- **Models SQLAlchemy (Etapa 2):** representam as tabelas.
- **Repositories (Etapa 2):** acesso ao banco.
- **Services (Etapa 2):** regras de negócio e transação.
- **Rotas (Etapa 2):** traduzem erros de regra para 404, 409 e 422.
- **Desktop (etapa futura):** consome a API e converte os dias do formulário em data prevista (hoje + dias).
- **Gabriel:** infraestrutura, Docker, PostgreSQL e filmes. **Nilson:** locações.

## 10. Pendências para a Etapa 2

- Model SQLAlchemy de `Locacao`, compatível com o de filmes.
- Repository, service e endpoints de locações, com transação.
- Validações do service listadas na seção 6.
- Confirmar com o Gabriel a chave estrangeira com `RESTRICT` e o índice único parcial.
- Decidir se a resposta incluirá dados do filme, já que a tabela da tela exibe o título.
- Decidir como o desktop acessa o banco, com Docker local ou remoto.
- Integrar a `LocacoesPage` com a API e preservar a exportação TXT.
- Testes do service e dos endpoints.