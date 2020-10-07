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
    "workingFolder": "$WORKING_FOLDER"
}
EOF

cat > /tmp/deck.yaml <<EOF
kong-addr: $KONG_ADMIN_URL
EOF

python wsgi.py
