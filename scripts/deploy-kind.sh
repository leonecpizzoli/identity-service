#!/usr/bin/env bash
# Aplica o identity-service em um cluster Kubernetes efemero (kind).
# Usado pelo pipeline de CD e reproduzivel localmente com o mesmo comando.
#
# O servico e implantado sozinho: ele nao depende de nenhum outro componente da
# plataforma para funcionar. Quem depende dele e o consumidor do token.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER_NAME="${CLUSTER_NAME:-identity-service}"
NAMESPACE="${NAMESPACE:-vehicle-resale}"
KEYS_DIR="${KEYS_DIR:-${ROOT_DIR}/.cd}"

: "${IMAGE_IDENTITY:?defina IMAGE_IDENTITY com a imagem completa do identity-service}"

# Credenciais do ambiente efemero. Em um cluster real viriam de um gerenciador de
# segredos; aqui os defaults existem para o pipeline rodar sem configuracao extra.
MONGO_ROOT_USERNAME="${MONGO_ROOT_USERNAME:-identity-root}"
MONGO_ROOT_PASSWORD="${MONGO_ROOT_PASSWORD:-identity-root-dev-password}"
MONGO_APP_USERNAME="${MONGO_APP_USERNAME:-identity-app}"
MONGO_APP_PASSWORD="${MONGO_APP_PASSWORD:-identity-app-dev-password}"
BOOTSTRAP_ADMIN_PASSWORD="${BOOTSTRAP_ADMIN_PASSWORD:-ChangeMeAdmin123}"

MONGO_URI="mongodb://${MONGO_APP_USERNAME}:${MONGO_APP_PASSWORD}@mongo-identity:27017/identity_db?authSource=identity_db&replicaSet=rs-identity"

log() { printf '\n==> %s\n' "$1"; }

if ! kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
  log "criando cluster kind ${CLUSTER_NAME}"
  kind create cluster --name "${CLUSTER_NAME}" --config "${ROOT_DIR}/k8s/kind-cluster.yaml" --wait 120s
else
  log "cluster kind ${CLUSTER_NAME} ja existe"
fi

log "carregando imagem no cluster"
kind load docker-image "${IMAGE_IDENTITY}" --name "${CLUSTER_NAME}"

log "aplicando namespace"
kubectl apply -f "${ROOT_DIR}/k8s/namespace.yaml"

log "gerando chave de assinatura JWT"
mkdir -p "${KEYS_DIR}"
if [[ -n "${JWT_PRIVATE_KEY_PEM:-}" ]]; then
  printf '%s' "${JWT_PRIVATE_KEY_PEM}" > "${KEYS_DIR}/jwt_private.pem"
elif [[ ! -f "${KEYS_DIR}/jwt_private.pem" ]]; then
  openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "${KEYS_DIR}/jwt_private.pem"
fi
chmod 600 "${KEYS_DIR}/jwt_private.pem"

apply_secret() {
  # kubectl create --dry-run | kubectl apply mantem o comando idempotente entre deploys.
  kubectl create secret generic "$@" \
    --namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
}

log "aplicando secrets"
apply_secret mongo-identity-credentials \
  --from-literal=root-username="${MONGO_ROOT_USERNAME}" \
  --from-literal=root-password="${MONGO_ROOT_PASSWORD}" \
  --from-literal=app-username="${MONGO_APP_USERNAME}" \
  --from-literal=app-password="${MONGO_APP_PASSWORD}"
apply_secret identity-service-secrets \
  --from-literal=mongo-uri="${MONGO_URI}" \
  --from-literal=bootstrap-admin-password="${BOOTSTRAP_ADMIN_PASSWORD}"
apply_secret jwt-signing-key \
  --from-file=jwt_private.pem="${KEYS_DIR}/jwt_private.pem"

log "aplicando manifests do MongoDB"
# O spec de um Job e imutavel: remover antes mantem o redeploy repetivel.
kubectl delete job mongo-identity-init \
  --namespace "${NAMESPACE}" --ignore-not-found --wait=true
kubectl apply -f "${ROOT_DIR}/k8s/mongo-identity.yaml"

log "aguardando MongoDB e criacao do usuario de aplicacao"
kubectl rollout status deployment/mongo-identity --namespace "${NAMESPACE}" --timeout=300s
kubectl wait --for=condition=complete job/mongo-identity-init --namespace "${NAMESPACE}" --timeout=300s

log "aplicando manifests do servico (identity=${IMAGE_IDENTITY})"
export IMAGE_IDENTITY
envsubst '${IMAGE_IDENTITY}' < "${ROOT_DIR}/k8s/identity-service.yaml" | kubectl apply -f -

log "aguardando rollout do servico"
kubectl rollout status deployment/identity-service --namespace "${NAMESPACE}" --timeout=300s

log "deploy concluido"
kubectl get pods,services --namespace "${NAMESPACE}"
