# ADR 0001: Use Supabase Postgres for Time-Series Metrics

## Status
Accepted

## Context
VeloBot requires a storage layer to track Instagram Reel metrics (views, reach, engagement) over time. Previously, the project used Google Firestore (NoSQL), but as the analytical requirements grew (velocity calculation, acceleration, rolling averages), the logic became complex to handle in application code.

## Decision
We decided to migrate from Firestore to **Supabase (PostgreSQL)**.

## Consequences

### Positive
*   **Compute-on-Read:** We can use SQL Window Functions (`LAG`, `AVG() OVER`, etc.) to calculate velocity and acceleration at the database level, keeping the API Bridge code extremely simple.
*   **Data Integrity:** Foreign key constraints ensure that `polls` always belong to a valid `reel_id`.
*   **Standardization:** Using standard SQL makes the data easily accessible to standard Data Science tools (Pandas, SQL explorers).
*   **Zero-Idle Cost:** Supabase's free tier and connection pooling (PgBouncer) align with our serverless architecture.

### Negative / Risks
*   **Schema Rigidity:** Changes to the metric structure require SQL migrations.
*   **Connection Management:** As a serverless app, we must use a connection pooler (port 6543) to avoid exhausting database connections.

---

# ADR 0002: 1-Minute Polling Resolution for 24-Hour Window

## Status
Accepted

## Context
Originally, VeloBot used an adaptive polling cadence (1m, 2m, 5m) to save on GCP costs and Meta API rate limits. However, to support deep data science analysis and "algorithmic reverse engineering," we require higher resolution data.

## Decision
We have standardized on a **1-minute polling interval** for the entire 24-hour tracking window of a Reel.

## Consequences

### Positive
*   **High Resolution:** Provides 1,440 data points per day, allowing for granular "inflection point" analysis.
*   **Consistent Narrative:** Easier to compare different Reels when they all share the same time-series resolution.

### Negative / Risks
*   **Rate Limits:** Increases the number of calls to the Meta Graph API. (Mitigation: Currently well within limits for a single account).
*   **Database Growth:** Approximately 1,500 rows per day. (Mitigation: Postgres handles this volume with ease; storage cost is negligible).
