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
    "workingFolder": "$WORKING_FOLDER",
    "keycloak": {
        "serverUrl": "$KC_SERVER_URL",
        "realm": "$KC_REALM",
        "clientId": "$KC_CLIENT_ID",
        "clientSecret": "$KC_CLIENT_SECRET",
        "userRealm": "$KC_USER_REALM",
        "username": "$KC_USERNAME",
        "password": "$KC_PASSWORD"
    }
}
EOF

cat > /tmp/deck.yaml <<EOF
kong-addr: $KONG_ADMIN_URL
EOF

python wsgi.py
