#!/usr/bin/env sh
set -eu

if [ -e .env ]; then
  echo ".env already exists; refusing to overwrite it" >&2
  exit 1
fi

db_password=$(openssl rand -hex 24)
grafana_password=$(openssl rand -hex 24)
jwt_key=$(openssl rand -hex 48)
admin_password=$(openssl rand -hex 24)

umask 077
sed \
  -e "s/REPLACE_ME_DATABASE_PASSWORD/$db_password/g" \
  -e "s/REPLACE_ME_GRAFANA_PASSWORD/$grafana_password/g" \
  -e "s/REPLACE_ME_WITH_AT_LEAST_32_RANDOM_CHARACTERS/$jwt_key/g" \
  -e "s/REPLACE_ME_ADMIN_PASSWORD_14_CHARS_MINIMUM/$admin_password/g" \
  .env.example > .env

echo "Created .env with mode 600. Store the generated credentials securely."
