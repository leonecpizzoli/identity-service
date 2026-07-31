#!/usr/bin/env bash
# Valida o identity-service recem-implantado percorrendo a superficie publica dele.
# O deploy so e considerado bem-sucedido se este script sair com codigo 0.
#
# O escopo e deliberadamente o proprio servico: ele nao conhece nenhum consumidor
# do token, entao nada aqui depende de outro componente estar no ar.
set -euo pipefail

IDENTITY_URL="${IDENTITY_URL:-http://localhost:8001}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@vehicle-resale.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-ChangeMeAdmin123}"
ISSUER="${ISSUER:-https://identity.vehicle-resale.local}"
AUDIENCE="${AUDIENCE:-vehicle-resale-backend}"

RUN_ID="$(date +%s)$RANDOM"
BUYER_EMAIL="smoke.${RUN_ID}@vehicle-resale.local"
BUYER_PASSWORD="SmokeTest123"
BUYER_DOCUMENT="SMOKE${RUN_ID}"

checks=0
step() { checks=$((checks + 1)); printf '\n[%02d] %s\n' "$checks" "$1"; }
fail() { printf 'FALHOU: %s\n' "$1" >&2; exit 1; }

# Ecoa o corpo na stdout e o status HTTP na ultima linha, para validar os dois.
request() {
  local method="$1" url="$2"
  shift 2
  curl -sS -X "$method" "$url" -w '\n%{http_code}' "$@"
}

body_of() { sed '$d' <<<"$1"; }
status_of() { tail -n1 <<<"$1"; }

expect_status() {
  local response="$1" expected="$2" what="$3"
  local actual
  actual="$(status_of "$response")"
  if [[ "$actual" != "$expected" ]]; then
    printf '%s\n' "$(body_of "$response")" >&2
    fail "${what}: esperava HTTP ${expected}, recebeu ${actual}"
  fi
}

# Decodifica um segmento base64url de JWT sem depender de biblioteca externa.
decode_segment() {
  local segment="${1//-/+}"
  segment="${segment//_//}"
  case $(( ${#segment} % 4 )) in
    2) segment="${segment}==" ;;
    3) segment="${segment}=" ;;
  esac
  base64 -d <<<"$segment" 2>/dev/null
}

wait_for_ready() {
  local url="$1" name="$2" attempt
  for attempt in $(seq 1 60); do
    if [[ "$(curl -so /dev/null -w '%{http_code}' "${url}/health/ready" || true)" == "200" ]]; then
      printf '%s pronto (tentativa %d)\n' "$name" "$attempt"
      return 0
    fi
    sleep 2
  done
  fail "${name} nao ficou pronto em 120s"
}

step "readiness do servico"
wait_for_ready "$IDENTITY_URL" identity-service

step "liveness responde independente do banco"
response="$(request GET "${IDENTITY_URL}/health/live")"
expect_status "$response" 200 "liveness"

step "cadastro do comprador"
response="$(request POST "${IDENTITY_URL}/api/v1/auth/register" \
  -H 'Content-Type: application/json' \
  -d "{\"full_name\":\"Smoke Test\",\"email\":\"${BUYER_EMAIL}\",\"document\":\"${BUYER_DOCUMENT}\",\"phone\":\"+5511999${RUN_ID: -6}\",\"password\":\"${BUYER_PASSWORD}\"}")"
expect_status "$response" 201 "cadastro do comprador"

step "cadastro duplicado e recusado"
response="$(request POST "${IDENTITY_URL}/api/v1/auth/register" \
  -H 'Content-Type: application/json' \
  -d "{\"full_name\":\"Smoke Test\",\"email\":\"${BUYER_EMAIL}\",\"document\":\"${BUYER_DOCUMENT}\",\"phone\":\"+5511999${RUN_ID: -6}\",\"password\":\"${BUYER_PASSWORD}\"}")"
expect_status "$response" 409 "cadastro duplicado"

step "login do comprador"
response="$(request POST "${IDENTITY_URL}/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"${BUYER_EMAIL}\",\"password\":\"${BUYER_PASSWORD}\"}")"
expect_status "$response" 200 "login do comprador"
BUYER_TOKEN="$(body_of "$response" | jq -re .access_token)"

step "login com senha errada e recusado"
response="$(request POST "${IDENTITY_URL}/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"${BUYER_EMAIL}\",\"password\":\"SenhaErrada999\"}")"
expect_status "$response" 401 "login com senha errada"

step "login do admin de bootstrap"
response="$(request POST "${IDENTITY_URL}/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}")"
expect_status "$response" 200 "login do admin"
[[ "$(body_of "$response" | jq -re '.user.roles | index("ADMIN")')" != "null" ]] \
  || fail "admin de bootstrap sem o papel ADMIN"

step "perfil do comprador autenticado"
response="$(request GET "${IDENTITY_URL}/api/v1/users/me" -H "Authorization: Bearer ${BUYER_TOKEN}")"
expect_status "$response" 200 "consulta do proprio perfil"
[[ "$(body_of "$response" | jq -re .email)" == "$BUYER_EMAIL" ]] || fail "perfil retornou outro e-mail"

step "perfil sem token e recusado"
response="$(request GET "${IDENTITY_URL}/api/v1/users/me")"
expect_status "$response" 401 "perfil sem token"

# O JWKS e o unico contrato que o servico expoe para terceiros validarem os
# tokens que ele emite. Sem chave publica utilizavel aqui, nenhum consumidor
# consegue autenticar ninguem — por isso ele e verificado no smoke test.
step "JWKS publica chave RSA utilizavel"
response="$(request GET "${IDENTITY_URL}/.well-known/jwks.json")"
expect_status "$response" 200 "consulta do JWKS"
jwks="$(body_of "$response")"
[[ "$(jq -re '.keys | length' <<<"$jwks")" -ge 1 ]] || fail "JWKS veio sem chaves"
[[ "$(jq -re '.keys[0].kty' <<<"$jwks")" == "RSA" ]] || fail "JWKS nao expos uma chave RSA"
JWKS_KID="$(jq -re '.keys[0].kid' <<<"$jwks")"
[[ -n "$JWKS_KID" ]] || fail "JWKS veio sem kid"
[[ "$(jq -re '.keys[0] | has("d")' <<<"$jwks")" == "false" ]] || fail "JWKS vazou a chave privada"

step "token emitido casa com o kid e o contrato do JWKS"
header="$(decode_segment "$(cut -d. -f1 <<<"$BUYER_TOKEN")")"
claims="$(decode_segment "$(cut -d. -f2 <<<"$BUYER_TOKEN")")"
[[ "$(jq -re .alg <<<"$header")" == "RS256" ]] || fail "token nao foi assinado com RS256"
[[ "$(jq -re .kid <<<"$header")" == "$JWKS_KID" ]] || fail "kid do token nao existe no JWKS"
[[ "$(jq -re .iss <<<"$claims")" == "$ISSUER" ]] || fail "issuer do token divergiu do contrato"
[[ "$(jq -re .aud <<<"$claims")" == "$AUDIENCE" ]] || fail "audience do token divergiu do contrato"
[[ "$(jq -re '.roles | index("BUYER")' <<<"$claims")" != "null" ]] || fail "token sem o papel BUYER"
[[ "$(jq -re .sub <<<"$claims")" =~ ^[0-9a-f]{32}$ ]] || fail "subject do token fora do formato esperado"

printf '\nsmoke test concluido: %d verificacoes aprovadas\n' "$checks"
