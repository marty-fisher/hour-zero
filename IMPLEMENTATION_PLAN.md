# Implementation Plan: hour-zero Data & Analytics

This document outlines the step-by-step execution path for Phase 1 (Plumbing), Phase 2 (Usability), and Phase 3 (Novelty) as defined in `APPROACH.md`.

## Stage 1: Data Validity (Testing the Plumbing)
- [x] **1.1: Quantify the "Zero-Bounce" Effect**
    - Create `scripts/analyze_zero_bounce.py` to calculate time intervals between polls when `views_delta == 0`.
    - Identify Instagram's CDN cache replication lag.
- [x] **1.2: Profile Ingestion Jitter**
    - Audit the variance between expected poll intervals (1m, 2m, 5m) and actual `polled_at` timestamps.
- [x] **1.3: Mitigate "Data Gulps" (Smoothing Spikes)**
    - Implement a smoothing algorithm to distribute "gulped" views across preceding zero-delta periods.

## Stage 2: Usability (Database & Normalization Upgrades)
- [x] **2.1: Implement Scale Normalization (Relative VPM)**
    - Update `db/schema.sql` to include `relative_velocity` in `poll_metrics` views.
    - Formula: `velocity / follower_count_at_post`.
- [x] **2.2: Standardize Cohort Time Bins**
    - Add pre-calculated `age_minutes` and rounded time bins to the database views for easier aggregation.

## Stage 3: Novelty (Hunting for Algorithmic Signals)
- [x] **3.1: Lead-Lag Cross-Correlation Analysis**
    - Analyze which engagement metrics (shares vs saves vs likes) have the shortest lag time to positive acceleration.
- [x] **3.2: Audience Temperature Deflection Points**
    - Map `audience_temperature` drops against future `acceleration` decay.

## Stage 4: Visualization (Interactive Dashboard)
- [ ] **4.1: Virality Phase Space (Velocity vs Acceleration)**
- [ ] **4.2: Multi-Line Normalized Growth Trails**
- [ ] **4.3: Engagement Lead-Lag Streamgraph**
