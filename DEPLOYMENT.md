# Deployment Guide

How this warehouse runs day to day, and how to stand up your own copy of it
from nothing.

## Architecture

```
Cloud Scheduler (daily, 6 PM PKT / Asia/Karachi)
        |  triggers via OAuth, as the one service account below
        v
Cloud Run Job (pulls mtauha/psx-warehouse:latest from Docker Hub)
  1. python -m extract.main        -- scrape PSX, write raw.* tables
  2. dbt build --target prod       -- seed + staging + intermediate + marts
        |
        v
BigQuery (raw dataset; staging/intermediate/marts currently share it too --
          see "Known limitation" below)
```

One service account (`psx-warehouse-runner`) does double duty: it's the
identity Cloud Scheduler authenticates as to invoke the Job, and the identity
the Job itself runs as (attached directly, no downloadable key — both
`extract/bigquery_io.py` and dbt-bigquery's `oauth` auth method resolve
Application Default Credentials from Cloud Run's metadata server
automatically).

## Prerequisites

- A GCP project, with a billing account linked. Terraform does not create
  the project itself — see "Bootstrap" below.
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) and
  [Terraform](https://developer.hashicorp.com/terraform/downloads) installed
  locally.
- [uv](https://docs.astral.sh/uv/) and Docker, for local development and
  testing the image before it ships.
- Three GitHub repo secrets on this repo: `DOCKERHUB_USERNAME`,
  `DOCKERHUB_TOKEN` (for `docker-publish.yml`), `MOTHERDUCK_TOKEN` (for
  `dbt-docs.yml`).

## Local development

```bash
uv sync --extra dev --extra dbt
cp dbt/profiles.example.yml ~/.dbt/profiles.yml   # fill in your own MD_DATABASE
```

Run extraction against MotherDuck (never against production BigQuery from a
laptop):

```bash
BACKEND=motherduck MD_DATABASE=your_db MOTHERDUCK_TOKEN=... python -m extract.main
cd dbt && dbt build --target dev
```

See `CONTRIBUTING.md` if you're adding a new backend rather than running an
existing one.

## GCP bootstrap (one-time, manual)

Terraform (`infra/`) manages everything *inside* a project — the project's
own existence and billing link are outside its scope on purpose (there's no
clean unattended path for either at this project's personal scale).

1. Create the GCP project (console or `gcloud projects create`); note the
   Project ID.
2. Link a billing account: Billing -> Link a billing account. Consider
   setting a small budget alert (Billing -> Budgets & Alerts) — the design
   stays inside the free tier (~1.5GB/month of BigQuery scans against a
   1TB/month free allowance) but a linked billing account means real spend
   is now *possible*.
3. `gcloud auth application-default login` — gives Terraform's `google`
   provider your own credentials to plan/apply with.

## Deploying the infrastructure

```bash
cd infra
terraform init
```

Create `infra/terraform.tfvars` (gitignored) with the one variable that has
no default:

```hcl
gcp_project = "your-real-project-id"
```

(Every other variable — region, dataset name/location, image reference,
schedule — already defaults to this project's actual settings; override only
if you genuinely want something different. See `infra/variables.tf`.)

```bash
terraform plan
terraform apply
```

**Don't use `-target` to work around a partial failure.** It's tempting when
some resources are blocked (see below), but `-target` on a resource that
references any single instance of a `for_each`'d resource pulls the *entire*
`for_each` set into its operation — including instances you didn't touch and
don't want retried. A plain `terraform apply` with no `-target` flags
correctly creates everything whose real dependencies are satisfied and
leaves only the genuinely-blocked resources pending, because the normal
execution graph (unlike `-target`'s closure computation) respects per-instance
dependencies correctly. If you ever do need `-target` for a real emergency,
quote each value in PowerShell (`-target="type.name"`) — unquoted values get
mis-tokenized by this environment's PowerShell/Terraform combination.

### If billing isn't fully active yet

APIs that don't need billing (`bigquery`, `iam`, `cloudresourcemanager`,
`serviceusage`) enable fine, and everything depending only on those
(the service account, its two BigQuery IAM bindings, the `raw` dataset)
creates successfully. `run.googleapis.com` and `cloudscheduler.googleapis.com`
— and anything depending on them (the Cloud Run Job, its invoker binding,
the Scheduler job) — fail with:

```
Error 400: Billing account for project '...' is not found.
```

This is expected, not a config bug. Once billing is fully linked, re-run the
same plain `terraform apply` — already-created resources are a no-op (state
already matches), and only the previously-blocked resources get created.

If `google_project_service` itself fails to enable anything (a fresh project
without Service Usage API already on), the fallback is:

```bash
gcloud services enable serviceusage.googleapis.com
```

### Starting over

If you want a genuinely clean slate:

```bash
terraform destroy          # tears down what Terraform actually created
rm -rf infra/.terraform
terraform init             # fresh provider download
terraform apply
```

Never delete `infra/terraform.tfstate` by hand instead of running `destroy`
— that makes Terraform *forget* resources without deleting them in GCP,
orphaning real cloud resources it no longer tracks. Do leave
`infra/.terraform.lock.hcl` alone when clearing the cache — it pins the
exact provider version for reproducibility; deleting it lets `init` resolve
a potentially different one.

## Verifying a deployment

```bash
gcloud run jobs execute psx-warehouse-extract --region us-central1
```

Watch the execution in Cloud Run's own console/logs. Confirm rows land in
`raw.*` and the dbt layers build, then let Cloud Scheduler's daily cadence
take over unsupervised.

## CI/CD

- `ci.yml` — lint, test, `dbt parse` on every push/PR to `main`.
- `docker-publish.yml` — builds and pushes `mtauha/psx-warehouse:latest`
  (+ a short-sha tag) to Docker Hub on every push to `main`.
- `dbt-docs.yml` — publishes dbt docs to GitHub Pages
  (https://mtauha.github.io/psx-warehouse/) on every `dbt/` change.

## Known limitation: dbt writes into the `raw` dataset

As currently configured, dbt has no `+schema:`/`generate_schema_name`
override, so `staging`/`intermediate`/`marts` objects all land in the same
BigQuery dataset as the raw extraction tables (`raw` by default) — not in
separate datasets, despite what the layer names might suggest. This causes
no collisions today (verified: no name overlaps between raw tables and dbt
models) and predates the Terraform work entirely (true since
`dbt/profiles.example.yml` was first written). If you want genuine dataset
separation, that's an open design decision — not something this guide's
setup does for you.
