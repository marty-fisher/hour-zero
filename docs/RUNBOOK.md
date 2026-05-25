# Hour-Zero Operational Runbook

## Overview
This document provides instructions for maintaining the Hour-Zero pipeline and troubleshooting common issues.

---

## 🚨 Critical Maintenance: Meta Access Token Refresh
The pipeline will stop if the `META_ACCESS_TOKEN` expires or is invalidated.

### Symptoms
*   `test_env.py` shows `HTTP 400` or `OAuthException`.
*   The `polls` table stops receiving new entries.
*   Logs in GCP Cloud Functions show authentication errors.

### Resolution
1.  Generate a new **Long-Lived Page Access Token** in the [Meta Developers Portal](https://developers.facebook.com/).
2.  Update the `META_ACCESS_TOKEN` in the `.env` file.
3.  **Redeploy:** Run `./deploy.sh` to update the environment variables in the Cloud Functions.

---

## 🛠 Persistence (Supabase)
Hour-Zero uses Supabase PostgreSQL.

### Connection Info
*   **Host:** `aws-1-us-east-1.pooler.supabase.com`
*   **Port:** `6543` (Transaction Pooling - **Mandatory** for serverless)
*   **Database:** `postgres`

### Common Queries
**Check Current Tracking State:**
```sql
SELECT * FROM tracking_state;
```

**Find Most Recent Polls:**
```sql
SELECT * FROM polls ORDER BY polled_at DESC LIMIT 10;
```

---

## 🚀 Deployment
Deployments are handled via the `deploy.sh` script.

### Prerequisites
*   GCP CLI (`gcloud`) installed.
*   Authenticated with `gcloud auth login`.
*   Active project set to `fit-heaven-494414-b0`.

### Command
```bash
./deploy.sh
```

---

## 📈 Monitoring
Check the health of the system by running the local diagnostic scripts:
*   `python scripts/ops/test_env.py`: Tests API and DB connections.
*   `python scripts/ops/check_db_recent.py`: Displays the latest data points in the DB.
