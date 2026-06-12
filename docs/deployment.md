# Deployment runbook

End state: the app live at https://elijahwf.com/ttb. Steps marked **[YOU]** are manual;
everything else is automatic once configured.

## 0. Prerequisites

- Azure CLI logged in (`az login`), subscription selected.
- This repo pushed to GitHub.
- An Anthropic API key.

## 1. [YOU] Provision Azure resources

```bash
az group create -n ttb-rg -l eastus2

az deployment group create -g ttb-rg -f infra/main.bicep \
  --parameters postgresAdminPassword='<CHOOSE-A-STRONG-PASSWORD>' \
  --query properties.outputs
```

Record the outputs: `staticWebAppName`, `staticWebAppHostname`,
`storageAccountName`, `postgresServerFqdn`, `postgresUrlTemplate`.

## 2. [YOU] Get the deployment token and wire up GitHub

```bash
az staticwebapp secrets list -n <staticWebAppName> -g ttb-rg \
  --query properties.apiKey -o tsv
```

In the GitHub repo → Settings:

- **Secrets → Actions**: add `AZURE_STATIC_WEB_APPS_API_TOKEN` (the token above)
  and `RETENTION_SWEEP_KEY` (any random string — also used in step 3).
- **Variables → Actions**: add `SWA_HOSTNAME` = `staticWebAppHostname` output.

## 3. [YOU] Set application settings on the Static Web App

```bash
az staticwebapp appsettings set -n <staticWebAppName> -g ttb-rg --setting-names \
  ANTHROPIC_API_KEY='sk-ant-...' \
  POSTGRES_URL='postgresql://ttbadmin:<PASSWORD>@<postgresServerFqdn>:5432/ttb?sslmode=require' \
  AZURE_STORAGE_CONNECTION_STRING="$(az storage account show-connection-string -n <storageAccountName> -g ttb-rg -o tsv)" \
  AZURE_STORAGE_CONTAINER_QUARANTINE='quarantine' \
  AZURE_STORAGE_CONTAINER_LABELS='labels' \
  IMAGE_RETENTION_DAYS='30' \
  RETENTION_SWEEP_KEY='<same random string as the GitHub secret>'
```

If the Postgres password contains URL-special characters (`@ : / ? #`), percent-encode
them in `POSTGRES_URL`.

## 4. Deploy the app

Push to `master` (or run the **Deploy to Azure Static Web Apps** workflow manually).
The workflow builds the Vite frontend and packages the Python API. The database schema
is applied automatically on the API's first connection — no psql step.

Verify on the SWA host directly:

- `https://<staticWebAppHostname>/api/health` → `{"status": "ok"}`
- `https://<staticWebAppHostname>/ttb/` → the landing page
- Submit a test application end-to-end from `/ttb/submit`.

## 5. [YOU] Add the Vercel rewrite on the personal site

Copy the `rewrites` from `vercel.json` (repo root) into the personal-site repo's
vercel.json, replacing `<swa-hostname>` with the real hostname, and deploy the
personal site. All three rules matter — `/ttb`, `/ttb/api/:path*` (API proxy), and
`/ttb/:path*`, in that order.

Then verify `https://elijahwf.com/ttb` loads and a submission works (the SPA calls
`/ttb/api/*` on this origin).

## 6. Retention sweep

The **Retention sweep** workflow runs daily at 07:00 UTC and POSTs
`/api/retention-sweep` with the `x-sweep-key` header. Trigger it once manually
(Actions → Retention sweep → Run workflow) to confirm a 200 `{"swept": 0, ...}`.

## Cost guardrails

Burstable B1ms Postgres (~$13–15/mo) + SWA Standard ($9/mo) + LRS storage (cents) ≈
**$25–35/month**. No per-request compute billing (managed functions are included in
SWA Standard). The Anthropic spend is per submission (~1 image-pair call each).
To pause spend: `az postgres flexible-server stop -n <pgServerName> -g ttb-rg`.
To tear down everything: `az group delete -n ttb-rg`.
