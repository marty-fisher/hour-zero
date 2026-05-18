# VeloBot Roadmap & Future Scaling

## Overview
This roadmap outlines the planned evolution of VeloBot from a single-account experimental tool to a robust, multi-tenant analytical platform.

---

## Phase 1: Public-Facing Platform & "Building in Public" (Short Term)
*   [ ] **Frontend Display of Instagram Data:** Develop a public-facing web application (e.g., using React/Next.js) to visualize the collected Instagram metrics and trends without exposing sensitive account details.
*   [ ] **Methodology & Architecture Deep-Dive:** Create comprehensive public documentation detailing the data ingestion strategies, backend architecture (GCP/Supabase), and predictive modeling methodologies to share insights with the developer community.
*   [ ] **Future Directions Roadmap:** Maintain a living document of upcoming features, open-source contributions, and community-driven ideas for expanding the "Building in Public" initiative.

## Phase 2: Data Science & Analytics (Medium Term)
*   [ ] **Automated Daily Reports:** Create a Cloud Function that generates a daily PDF/Markdown summary of the previous 24 hours of Reel performance.
*   [ ] **Predictive Modeling:** Use the 1-minute time-series data to train a lightweight model that predicts 24-hour total views based on the first 30 minutes of velocity.
*   [ ] **Hashtag Correlation:** Analyze the impact of `hashtag_count` and specific keywords on the initial "Fast Tier" velocity.

## Phase 3: Multi-Account Support (Long Term)
*   [ ] **Multi-Tenant Tracking:** Redesign `tracking_state` to support multiple active reels across different Instagram Account IDs simultaneously.
*   [ ] **User Dashboard:** Build a React/Next.js frontend to replace the Streamlit dashboard, allowing users to toggle between accounts.
*   [ ] **Competitive Benchmarking:** Implement tracking for "competitor" public metrics (views/likes) to compare internal growth against market trends.

## Phase 4: Institutional Security (Long Term)
*   [ ] **Secret Management:** Move `META_ACCESS_TOKEN` and `SUPABASE_DB_URL` from environment variables to **GCP Secret Manager**.
*   [ ] **CI/CD Pipeline:** Implement GitHub Actions to run `pytest` and auto-deploy to GCP on every push to `main`.
*   [ ] **Comprehensive Logging:** Integrate with GCP Cloud Logging to create alerts for failed polls or 400-series errors from Meta.
