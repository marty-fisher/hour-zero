# hour-zero Copilot Instructions

## Architecture
- hour-zero is a serverless event-driven pipeline on Google Cloud Platform (GCP).
- The primary database is Supabase PostgreSQL.
- The pipeline uses Python for GCP Cloud Functions and Streamlit for dashboards.

## Coding Guidelines
- Prefer serverless, zero-idle-cost solutions when suggesting architecture or code.
- Always use `psycopg2` or `supabase` python client for database interactions.
- Avoid modifying `.env` files directly. Assume secrets are managed via GCP Secret Manager or environment variables in production.
- Use `argparse` for scripts located in the `scripts/` directory. No hardcoded variables.
- Write functional, stateless code for Cloud Functions in the `backend/` directory. 
- Ensure HTTP Cloud Functions return proper JSON responses with CORS headers.
