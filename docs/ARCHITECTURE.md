# hour-zero Architecture & Project Outline

hour-zero is a serverless event-driven pipeline deployed on Google Cloud Platform (GCP) for ingesting, tracking, and serving real-time Instagram Reel metrics as time-series data. It uses a zero-idle-cost architecture backed by Supabase Postgres.

## Directory Structure

```text
.
├── backend/
│   ├── api_bridge/           # Read-only GCP Cloud Function serving JSON data to the frontend
│   ├── ingestion/            # Core ingestion Cloud Function (Pub/Sub & Scheduler triggered)
│   └── webhook_handler/      # HTTP Cloud Function receiving events from Meta Webhooks
├── db/
│   └── schema.sql            # Postgres SQL schema for Supabase (tracking state, metrics, views)
├── analysis/                 # Data science and exploratory scripts
├── dashboard/                # Analytics UI / Streamlit dashboard
├── scripts/
│   ├── api/                  # Meta API exploration tools
│   ├── archive/              # Deprecated and migration scripts
│   └── ops/                  # General pipeline debugging and operational scripts
├── .env                      # Environment variables for local staging
├── deploy.sh                 # GCP deployment script for Cloud Functions
├── requirements.txt          # Shared python dependencies for local environment
└── README.md                 # Original project README
```

## Service Interactions & Framework

### 1. Webhook Handler (`backend/webhook_handler`)
- **Trigger**: External HTTP `POST` from Meta's Webhook service when a new post/reel is created.
- **Functionality**: 
  - Verifies the HMAC-SHA256 signature using `META_APP_SECRET`.
  - Publishes the verified payload to a GCP Pub/Sub topic (`media-ingestion-trigger`).
- **Role**: Decouples the immediate webhook response (required by Meta to avoid timeouts) from the potentially long-running metrics ingestion logic.

### 2. Ingestion Core (`backend/ingestion`)
- **Trigger**: Dual-triggered by both the GCP Pub/Sub topic (instant ingestion) and a Cloud Scheduler heartbeat (every 1 minute).
- **Functionality**:
  - Connects to Supabase Postgres to read the `tracking_state` table to determine the active reel.
  - Applies an **adaptive polling cadence**:
    - **0-30 min**: ~1 minute intervals.
    - **30 min - 2h**: ~2 minute intervals.
    - **2h - 24h**: ~5 minute intervals.
  - Queries the Meta Graph API for reel metrics (views, reach, engagement) and follower counts.
  - Upserts the latest time-series data directly into Supabase.

### 3. API Bridge (`backend/api_bridge`)
- **Trigger**: HTTP `GET` from the frontend dashboard or external consumers.
- **Functionality**:
  - Connects to Supabase and queries the `poll_metrics_enriched` SQL view.
  - Retrieves the most recent Reel's timeline data with all velocity calculations (e.g., views per minute) already pre-computed on the database level.
  - Returns a flattened JSON array with CORS headers enabled (`Access-Control-Allow-Origin: *`).

### 4. Database (Supabase Postgres)
- **`tracking_state`**: Singleton table managing the currently active Reel and tracking its 24-hour polling TTL.
- **`poll_metrics`**: Raw time-series data storage for views, engagement, and timestamps.
- **Views (`poll_metrics_enriched`)**: Complex Postgres views that handle the derivation of velocity, reach momentum, and follower-adjusted engagement ratios, offloading computational work from the API layer.

### 5. Utility Scripts & Analysis
- **`scripts/ops/`**: Operations and pipeline management (`backfill.py`, `check_db_recent.py`, `debug.py`, `test_env.py`).
- **`scripts/api/`**: API Testing & Exploration (`api_explorer.py`).
- **`scripts/archive/`**: Archived scripts like old migrations (`migrate_firestore_to_supabase.py`).
- **`analysis/`**: Data science and exploratory scripts (e.g., `analyze_boredom.py`, `analyze_lead_lag.py`, `reel_analysis.ipynb`, etc.).
- **`dashboard/`**: Streamlit dashboard implementation (`dashboard.py`).
