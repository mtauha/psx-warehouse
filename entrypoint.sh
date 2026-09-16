#!/bin/sh
set -eu

python -m extract.main

mkdir -p "$HOME/.dbt"
cat > "$HOME/.dbt/profiles.yml" <<EOF
psx_warehouse:
  target: prod
  outputs:
    prod:
      type: bigquery
      method: oauth
      project: "${GCP_PROJECT}"
      dataset: "${BQ_DATASET}"
      threads: 4
EOF

cd dbt
dbt build --target prod
