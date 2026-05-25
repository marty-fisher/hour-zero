# hour-zero Copilot Instructions

## Architecture
- hour-zero is a serverless event-driven pipeline on Google Cloud Platform (GCP).
- The primary database is Supabase PostgreSQL.
- The pipeline uses Python for GCP Cloud Functions and Streamlit for dashboards.
- Data ingestion is handled by time-series polling stored in PostgreSQL (`poll_metrics`, `reels`, `tracking_state`), with view enrichment and rolling statistics computed via SQL views.
- The 24-hour prediction strategy calculates total accrued views plus a remaining decay curve `((current_velocity/2) * remaining_minutes)`.
- Static presentation data is generated via Python scripts running on GitHub Actions (`export_static_data.py`), persisting to `data.json` for frontend display.

## Coding Guidelines
- Prefer serverless, zero-idle-cost solutions when suggesting architecture or code.
- Always use `psycopg2` or `supabase` python client for database interactions.
- Avoid modifying `.env` files directly. Assume secrets are managed via GCP Secret Manager or environment variables in production.
- Use `argparse` for scripts located in the `scripts/` directory. No hardcoded variables.
- Write functional, stateless code for Cloud Functions in the `backend/` directory. 
- Ensure HTTP Cloud Functions return proper JSON responses with CORS headers.

## Deployment Flow (Codespace to Production)
- The active repository name is `hour-zero`.
- Making edits to the frontend presentation or Python data scripts requires a normal `git add`, `git commit`, and `git push` to the `main` branch.
- **IMPORTANT**: If changes are made to the local `scripts/ops/export_static_data.py` script, the embedded copy of this script inside `.github/workflows/deploy-pages.yml` MUST be manually updated to mirror the changes.
- The `deploy-pages.yml` GitHub Action triggers automatically on pushes to `main` (if files in `public/` or the workflow itself are changed) and runs on a 15-minute cron schedule.
- The workflow runs the embedded python script to fetch fresh data from Supabase, outputs it to `public/data.json`, and deploys the `public/` directory via GitHub Pages.
