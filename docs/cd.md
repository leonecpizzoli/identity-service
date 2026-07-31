# Deploy automatizado (CD)

O deploy e disparado pelo pipeline, sem passo manual: a cada commit aprovado em
`main`, a imagem e publicada em um registry versionado e aplicada em um cluster
Kubernetes, que so e aceito como implantado depois de um smoke test da API.

## Escopo

O pipeline implanta **apenas o identity-service**. O servico nao depende de
nenhum outro componente da plataforma para funcionar: ele emite tokens e publica
a chave publica correspondente: quem consome esses tokens e problema de quem
consome. Essa e a razao de o repositorio ser separado, e o CD reflete isso.

Consequencia pratica: o smoke test cobre a superficie publica do proprio servico
— cadastro, login, perfil autenticado e o contrato do JWKS. Ele nunca sobe outro
servico nem valida integracao. A validacao da integracao real acontece no
ambiente local, com os dois repositorios lado a lado (ver `README.md`).

## Ambiente

O ambiente e um cluster Kubernetes **efemero** ([kind](https://kind.sigs.k8s.io/)),
criado dentro do proprio runner do GitHub Actions e destruido ao fim da execucao.
A escolha foi deliberada: nao ha custo de infraestrutura e o pipeline continua
exercitando o que importa em um CD — build da imagem, publicacao versionada,
aplicacao declarativa de manifests, rollout controlado e verificacao pos-deploy.
A contrapartida e que nao existe URL publica permanente; a evidencia de cada
deploy sao os logs do workflow e o artefato de diagnostico do cluster.

Trocar por um ambiente persistente nao muda o pipeline: os mesmos manifests em
`k8s/` se aplicam a qualquer cluster, bastando substituir a criacao do cluster
kind por um `kubeconfig` do cluster de destino.

## Pipeline

`.github/workflows/cd.yml`, disparado quando o workflow `ci` conclui com sucesso
em `main` (ou manualmente por `workflow_dispatch`).

| Job | O que faz |
| --- | --- |
| `publish` | Builda a imagem e publica em `ghcr.io/<owner>/identity-service:<sha>` (mais `:latest`). |
| `deploy` | Baixa a imagem publicada, cria o cluster kind, aplica os manifests, aguarda o rollout e roda o smoke test. |

O `deploy` usa a imagem baixada do registry, e nao um build local, para garantir
que o artefato validado e exatamente o artefato implantado. O passo de
diagnostico roda com `if: always()` e sobe recursos, eventos e logs dos pods como
artefato, o que preserva a evidencia mesmo quando o deploy falha.

> O evento `workflow_run` so e avaliado a partir do arquivo de workflow que esta
> na **branch padrao** do repositorio. Enquanto este `cd.yml` nao tiver sido
> promovido para `main`, o gatilho automatico nao existe e o deploy precisa ser
> acionado por `workflow_dispatch`.

## Topologia implantada

```
identity-service (2 replicas) ──> mongo-identity (replica set rs-identity)
        │
        └── GET /.well-known/jwks.json   ← contrato para consumidores do token
```

- O Service e `NodePort` e o cluster kind mapeia `30001 -> 8001` no host, entao a
  API responde no mesmo endereco usado no ambiente local com Docker Compose.
- Dentro de um cluster compartilhado, o mesmo Service resolve como
  `identity-service:8000` — e esse o endereco de JWKS que um consumidor usaria.
- Rollout com `maxUnavailable: 0`: um pod novo so recebe trafego depois que o
  `/health/ready` responde 200.

### Dependencias de inicializacao

O `lifespan` da aplicacao cria indices e o admin de bootstrap ainda no startup,
entao o banco precisa estar pronto antes do pod subir. A ordem e garantida por:

1. `readinessProbe` do mongod, que inicializa o replica set na primeira execucao
   e mantem o pod fora do Service enquanto o `rs.status()` nao responde;
2. um `Job` que cria o usuario de aplicacao de forma idempotente;
3. um `initContainer` `wait-for-mongo`, que so termina quando o banco aceita a
   conexao com as credenciais da aplicacao.

### Segredos

Nenhuma credencial fica nos manifests. O `scripts/deploy-kind.sh` cria os
`Secret`s no momento do deploy (credenciais do MongoDB, senha do admin de
bootstrap e chave RSA de assinatura dos JWTs, gerada se ainda nao existir). Em um
cluster real, os mesmos `Secret`s viriam de um gerenciador de segredos; os
defaults de desenvolvimento existem apenas para o pipeline rodar sem
configuracao adicional.

## Smoke test

`scripts/smoke-test.sh` exercita a API do servico implantado e falha o job em
qualquer divergencia:

1. readiness do servico;
2. liveness respondendo independentemente do banco;
3. cadastro de comprador;
4. cadastro duplicado recusado com `409`;
5. login do comprador;
6. login com senha errada recusado com `401`;
7. login do admin de bootstrap e verificacao do papel `ADMIN`;
8. consulta do proprio perfil com o token emitido;
9. consulta de perfil sem token recusada com `401`;
10. JWKS publicando chave RSA com `kid` e **sem** expor material privado;
11. token emitido com `alg` RS256, `kid` presente no JWKS, e `iss`, `aud`, `sub`
    e `roles` dentro do contrato.

As duas ultimas sao as que mais importam para quem consome o servico: sao elas
que garantem que um terceiro consegue validar o token sem falar com este
servico em nenhum momento alem do JWKS.

## Reproduzir localmente

Requer `docker`, `kind`, `kubectl`, `envsubst`, `jq`, `curl` e `openssl`.

```bash
docker build -t identity-service:local .

IMAGE_IDENTITY=identity-service:local ./scripts/deploy-kind.sh

./scripts/smoke-test.sh

kind delete cluster --name identity-service
```

Os scripts sao os mesmos executados pelo pipeline — o CD nao tem passos que so
existem no GitHub Actions.
