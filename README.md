# Serviço de Identidade

Esse é o serviço de identidade da plataforma de revenda de veículos. Ele cuida só de gente: cadastro de compradores, login, emissão dos tokens e as chaves para validar esses tokens. É um serviço totalmente apartado do resto da plataforma, exatamente como o enunciado pede, para que os dados de cliente fiquem separados dos dados transacionais de veículos e vendas.

Quem faz a parte de veículos e vendas é o outro serviço (o de vendas), que roda em outro repositório, com outro banco, e nunca toca no banco daqui. A única coisa que os dois compartilham é a confiança no token: este serviço assina os JWTs com uma chave RSA privada e publica a chave pública num endpoint JWKS, e o serviço de vendas usa essa chave pública para validar.

| Item | Valor |
|---|---|
| Porta local | `8001` |
| Banco | MongoDB `identity_db` (replica set `rs-identity`) |
| Assinatura dos tokens | RSA, algoritmo RS256 |

## Stack

Python 3.12, FastAPI, Pydantic 2, Uvicorn, MongoDB 8 (PyMongo assíncrono oficial), PyJWT com cryptography (RS256/JWKS), Argon2 via argon2-cffi, prometheus-client, uv, pytest com pytest-asyncio, httpx e Testcontainers, Ruff, MyPy strict, Bandit, pip-audit, Docker, Docker Compose e GitHub Actions.

Optei por não usar Redis. Ele só entraria se houvesse uma necessidade técnica concreta, e não teve: os índices únicos no MongoDB já garantem a unicidade de e-mail e documento, e o rate limiting de login e cadastro usa uma janela deslizante em memória, por instância, que resolve.

## Como foi implementado

### Clean Architecture

O serviço segue Clean Architecture, com as dependências sempre apontando para dentro:

```text
src/identity_service/
  domain/          entidades (dataclasses), value objects, enums, exceções, serviços de domínio
  application/     casos de uso, DTOs, portas de entrada e saída (Protocol)
  infrastructure/  MongoDB (repositório, índices), segurança (JWT, Argon2, chaves RSA, rate limiter),
                   settings tipadas, observabilidade, clock e gerador de IDs
  entrypoints/http routers, schemas Pydantic (extra="forbid"), dependencies, exception handlers,
                   middlewares (correlation id, métricas, security headers, limite de corpo)
  main.py          composição da aplicação (o lifespan cria os índices e injeta as dependências)
```

Algumas decisões que valem destacar:

- O domínio não importa FastAPI, Pydantic, PyMongo, JWT nem nada de infraestrutura. Isso não fica na boa fé: tem teste arquitetural baseado em AST cuidando disso (`tests/architecture/`).
- Os casos de uso dependem só de portas (`Protocol`). Os adaptadores concretos entram na composição, no `main.py`.
- As entidades de domínio são `dataclasses`. O documento do MongoDB fica mapeado num adaptador dedicado e nunca vaza direto pela API.
- Senha e hash nunca aparecem em resposta nem em log. O documento é mascarado quando volta pela API.

### Modelagem do comprador

O comprador (`identity_db.buyers`) tem nome completo, e-mail e documento normalizados e únicos (índices `ux_buyers_email` e `ux_buyers_document`), telefone validado, hash Argon2 da senha, papéis (`BUYER`, `ADMIN`), status (`ACTIVE`, `INACTIVE`, `BLOCKED`), datas em UTC e versão.

As regras que importam: e-mail e documento obrigatórios, normalizados e únicos; telefone validado; senha com política mínima (10 caracteres ou mais, com maiúscula, minúscula e dígito) e guardada só como hash Argon2; conta que não está ativa não autentica; e cadastro concorrente com o mesmo e-mail ou documento é resolvido pelo índice único, devolvendo conflito em vez de criar dois registros.

### Segurança e tokens

O token é um JWT em RS256 com `sub`, `roles`, `iss`, `aud`, `iat`, `nbf`, `exp`, `jti` e `kid`, e expiração curta de 15 minutos. A chave privada nunca sai do serviço e nunca vai para o repositório: em produção ela vem de variável de ambiente ou de um arquivo montado. A chave pública é publicada no endpoint JWKS, que é o que o serviço de vendas consome para validar os tokens.

Além disso: schemas de entrada com `extra="forbid"` para travar mass assignment, rate limiting no login e no cadastro (`429`), headers de segurança, limite de tamanho do corpo (`413`), CORS configurável e segredos só por variável de ambiente.

### Observabilidade e contrato de erro

O serviço expõe `/health`, `/health/live`, `/health/ready` e `/metrics` (Prometheus com requisições, duração, autenticação e conflitos), loga em JSON estruturado com `QueueHandler` para não bloquear, e tem um correlation id por requisição (header `X-Correlation-ID`, que volta na resposta e aparece no log). Todo erro segue o mesmo contrato:

```json
{
  "code": "EMAIL_ALREADY_REGISTERED",
  "message": "email is already registered",
  "timestamp": "2026-07-22T12:00:00Z",
  "path": "/api/v1/auth/register",
  "correlation_id": "...",
  "field_errors": []
}
```

## API

| Método | Rota | Auth | O que faz |
|---|---|---|---|
| POST | `/api/v1/auth/register` | pública | Cadastra comprador com papel `BUYER`, responde `201` |
| POST | `/api/v1/auth/login` | pública | Autentica e devolve `access_token`, `token_type`, `expires_in` e os dados públicos do usuário |
| GET | `/api/v1/users/me` | Bearer | Dados da conta autenticada, sem nada sensível e com o documento mascarado |
| GET | `/.well-known/jwks.json` | pública | Chaves públicas para validar os tokens |

## Como usar localmente

Você precisa de Docker e Docker Compose. Depois é só:

```bash
docker compose up --build
```

Isso sobe o MongoDB 8 como replica set de nó único (com keyFile e autenticação), o job de init que cria o usuário de aplicação do banco, o job que gera a chave RSA (no volume `jwt-keys`) e o serviço em `http://localhost:8001`. O serviço espera as dependências ficarem prontas pelos healthchecks, sem sleep fixo.

No primeiro boot já provisiono um administrador (dá para configurar pelas variáveis `IDENTITY_BOOTSTRAP__*`): `admin@vehicle-resale.local` com senha `ChangeMeAdmin123`. É credencial de desenvolvimento, então troque em qualquer ambiente de verdade.

### Fluxo de exemplo

```bash
curl -s -X POST http://localhost:8001/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"full_name":"Carlos Lima","email":"carlos@example.com","document":"98765432100","phone":"+5511998765432","password":"SuperSecret1"}'

curl -s -X POST http://localhost:8001/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"carlos@example.com","password":"SuperSecret1"}'

curl -s http://localhost:8001/.well-known/jwks.json | jq
```

O token que sai do login é o que o serviço de vendas espera no header `Authorization: Bearer`. A documentação interativa do OpenAPI fica em `http://localhost:8001/docs`.

### Rodando junto com o serviço de vendas

Os dois serviços vivem em repositórios separados e continuam separados quando rodam juntos: o que existe entre eles é uma rede Docker e um contrato de token, nada mais.

Este compose cria a rede `vehicle-resale-platform` e publica o serviço nela. É por ali que um consumidor alcança `http://identity-service:8000/.well-known/jwks.json` para validar os tokens que eu emito. O `mongo-identity` fica fora dessa rede — só o serviço entra nela.

A ordem importa, e ela é a própria direção da dependência:

```bash
# 1) primeiro aqui, que é quem publica a rede e o JWKS
docker compose up -d --build

# 2) depois, no repositório vehicle-sales-service
docker compose up -d --build
```

Para derrubar, o caminho inverso: primeiro o serviço de vendas, depois este. Se derrubar este primeiro, o Docker avisa que não conseguiu remover a rede porque ainda tem contêiner ligado nela — é só ruído, nada quebra.

Repare que eu não preciso saber nada sobre o serviço de vendas para isso funcionar. Não há `depends_on`, variável de ambiente ou manifesto aqui que cite o outro serviço.

### Rodando fora do Docker

```bash
uv sync
IDENTITY_MONGO__URI='mongodb://localhost:27017/?directConnection=true' \
IDENTITY_JWT__PRIVATE_KEY_PATH=./jwt_private.pem \
uv run uvicorn identity_service.main:app --port 8001
```

As configurações são tipadas com pydantic-settings, usando o prefixo `IDENTITY_` e o delimitador `__` (por exemplo `IDENTITY_JWT__ISSUER`). Se faltar alguma configuração obrigatória, como o material da chave JWT, a aplicação já quebra no boot em vez de subir quebrada.

## Como testar

Você precisa do [uv](https://docs.astral.sh/uv/) e do Docker rodando, porque os testes de integração sobem um MongoDB real como replica set pelo Testcontainers. Não tem mock de banco.

```bash
uv sync

uv run pytest                                    # suíte completa (88 testes)
uv run pytest tests/unit                         # unitários
uv run pytest tests/integration                  # integração (Docker)
uv run pytest tests/architecture                 # testes arquiteturais
uv run pytest --cov=identity_service --cov-fail-under=85

uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy src tests
uv run bandit -c pyproject.toml -r src
uv export --no-dev --no-emit-project --format requirements.txt -o requirements-audit.txt
uv run pip-audit -r requirements-audit.txt --disable-pip
```

A suíte cobre cadastro, cadastro concorrente com o mesmo e-mail e o mesmo documento (garantindo que só um registro é criado), login válido e inválido, conta inativa e bloqueada, e a validação do token (issuer, audience, assinatura, expiração e algoritmo).

## CI/CD

O arquivo `.github/workflows/ci.yml` roda em todo Pull Request e em todo push na `main`:

- **quality**: `uv lock --check`, instalação com uv, Ruff (lint e format), MyPy strict no src e nos testes, Bandit, pip-audit e a suíte completa de pytest com cobertura mínima de 85% e upload do relatório.
- **docker**: `docker compose config` e build da imagem.
- **release** (só na `main`, depois que os outros jobs passam): constrói a imagem versionada pelo SHA do commit e publica o artefato com `docker save`. Se qualquer etapa falhar, nada é publicado.

O fluxo já foi pensado para branch protection: é só exigir os checks `quality` e `docker` nos Pull Requests.

O arquivo `.github/workflows/cd.yml` entra depois que o `ci` passa na `main`: publica a imagem em `ghcr.io/<owner>/identity-service:<sha>`, sobe um cluster Kubernetes efêmero com kind, aplica os manifests de `k8s/` e só considera o deploy bem-sucedido se o `scripts/smoke-test.sh` passar. Os detalhes — topologia, segredos, ordem de inicialização e como reproduzir tudo localmente — estão em [`docs/cd.md`](docs/cd.md).

O CD implanta **apenas este serviço**. Ele não sobe nem conhece nenhum consumidor do token, e o smoke test cobre só a superfície pública dele, incluindo o contrato do JWKS. A integração de verdade é exercitada localmente, com os dois repositórios lado a lado.

Para rodar o mesmo deploy na sua máquina:

```bash
docker build -t identity-service:local .
IMAGE_IDENTITY=identity-service:local ./scripts/deploy-kind.sh
./scripts/smoke-test.sh
kind delete cluster --name identity-service
```

## Estado da última verificação local

- 88 testes passando (unitários, integração com MongoDB replica set de verdade e arquitetura). Cobertura em 94%, com a trava em 85%.
- Ruff (lint e format), MyPy strict, Bandit e pip-audit sem nenhum apontamento. `uv lock --check` ok.
- Imagem Docker construída. O `docker compose up --build` sobe o serviço saudável, com o admin provisionado e o JWKS respondendo.
