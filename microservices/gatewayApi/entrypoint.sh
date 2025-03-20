#!/bin/sh

mkdir -p ./config

cat > "${CONFIG_PATH:-./config/default.json}" <<EOF
{
    "logLevel": "${LOG_LEVEL:-DEBUG}",
    "apiPort": ${PORT:-2000},
    "oidcBaseUrl": "$OIDC_BASE_URL",
    "tokenMatch": {
        "aud": "$TOKEN_MATCH_AUD"
    },
    "kongAdminUrl": "$KONG_ADMIN_URL",
    "workingFolder": "$WORKING_FOLDER",
    "keycloak": {
        "serverUrl": "$KC_SERVER_URL",
        "realm": "$KC_REALM",
        "clientId": "$KC_CLIENT_ID",
        "clientSecret": "$KC_CLIENT_SECRET",
        "userRealm": "$KC_USER_REALM",
        "username": "$KC_USERNAME",
        "password": "$KC_PASSWORD"
    },
    "resourceAuthServer": {
        "serverUrl": "$KC_SERVER_URL",
        "realm": "$KC_REALM",
        "clientId": "$KC_RES_SVR_CLIENT_ID",
        "clientSecret": "$KC_RES_SVR_CLIENT_SECRET"
    },
    "applyAporetoNSP": ${NSP_ENABLED:-true},
    "protectedKubeNamespaces": "${PROTECTED_KUBE_NAMESPACES:-[]}",
    "hostTransformation": {
        "enabled": ${HOST_TRANSFORM_ENABLED:-false},
        "baseUrl": "${HOST_TRANSFORM_BASE_URL}"
    },
    "portal": {
        "url": "${PORTAL_ACTIVITY_URL:-""}",
        "token": "${PORTAL_ACTIVITY_TOKEN}"
    },
    "plugins": {
        "rate_limiting": {
            "redis_database": 0,
            "redis_host": "redis-master",
            "redis_port": 6379,
            "redis_password": "${PLUGINS_RATELIMITING_REDIS_PASSWORD}",
            "redis_timeout": 2000
        },
        "upstream_jwt": {
            "key_id": "${PLUGINS_UPSTREAM_JWT_KEY_ID}",
            "issuer": "${PLUGINS_UPSTREAM_JWT_ISSUER}",
            "private_key_location": "${PLUGINS_UPSTREAM_JWT_PRIVATE_KEY_FILE}",
            "public_key_location": "${PLUGINS_UPSTREAM_JWT_PUBLIC_KEY_FILE}"
        },
        "proxy_cache": {
            "strategy": "memory",
            "memory": { "dictionary_name": "${PLUGINS_PROXYCACHE_MEMORY_DICT:-"aps_proxy_cache"}" }
        }
    },
    "defaultDataPlane": "${DEFAULT_DATA_PLANE:-"dp-silver-kong-proxy"}",
    "kubeApiCreds": {
        "kubeApiUser": "${KUBE_API_USER}",
        "kubeApiPass": "${KUBE_API_PASS}"
    },
    "compatibilityApiUrl": "${COMPATIBILITY_API_URL}",
    "deckCLI": "${DECK_CLI}"
}
EOF

cat > /tmp/deck.yaml <<EOF
kong-addr: $KONG_ADMIN_URL
EOF

gunicorn --bind 0.0.0.0:2000 -t 0 -w 4 wsgi:app