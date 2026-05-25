# Predictive Modeling Optimization Plan

## Current State & Diagnostics
Our early projections (15m, 30m, 45m, 60m) are prone to large extrapolation errors ("Flash in the Pan" syndrome). The current model uses a simplified dynamic half-life `590.0m * momentum_ratio`, but it solely evaluates `views` and `velocity` without factoring in secondary engagement properties that actually drive the Instagram algorithm.

Based on the feedback, we need to ingest secondary features at timestamp intervals and cluster Reels by content archetypes to forcefully apply accurate decaying limits. 

## Action Plan

### 1. Implement a Dynamic "Velocity Decay" Factor (Non-Linear Smoothing)
Currently, if velocity at 15m is massive, `export_static_data.py` assumes sustained algorithmic distribution.
- **Action:** Introduce an exponential penalization multiplier `D`. The algorithm will examine the 2nd derivative (`acceleration`): if velocity is high but `acceleration` is negative (slowing down), the half-life penalty becomes aggressively logarithmic, crushing the 24-hr projected curve.

### 2. Incorporate Real-Time Engagement Ratios
Views do not dictate the explore algorithm; retention, likes, shares, and saves do. Currently in schema `poll_metrics`: `likes`, `comments`, `shares`, `saved`, `reach`.
- **Action:** Add `Share-to-View` and `Save-to-View` thresholds to `export_static_data.py`. If a Reel's `shares / views` drops below an empirical threshold (e.g. `1%`), immediately flag the Reel as entering a "Plateau State".
- *Note:* We do not have "Average Watch Time" natively accessible in the standard Graph API Webhooks, but "Saves and Shares" are powerful alternative signals for retention/value.

### 3. Transition from Time-Fixed to Trend-Based Adjustments
Currently, the model only looks at static lookbacks (`[-15:]` minute chunks).
- **Action:** Measure the True Views slope inflection point. Compare the `15-30m` velocity average against the `30-45m` velocity average. If `V(30-45) < V(15-30)` while absolute views are high, force the mathematical projection to pivot downwards toward the "Flash in the Pan" archetype.

### 4. Cluster Reels by "Content Archetypes"
Instead of letting the model guess the curve freely, assign the projection mathematically to one of three archetypes based on the first hour's `velocity`, `acceleration`, and `engagement_rate`:
1. **The Flash in the Pan:** Sudden velocity burst in first 30m, `acceleration < 0` immediately following, low `share-to-view`. (Action: Set half-life to aggressive `120m`).
2. **The Slow Burner:** Low initial views, `acceleration ± 0`, high `engagement_rate`. (Action: Set half-life to steady `1000m`).
3. **The Exponential Viral:** Slope increasing over hours (`acceleration > 0`). 

## Implementation Steps
1. Create `analysis/archetype_clustering.py` to identify these 3 archetypes in our historical database to generate the threshold numbers.
2. Update `scripts/ops/export_static_data.py` to fetch `shares` and `saved` metrics from the database during generating.
3. Update the `predict_at_minute` logic to read these boundaries and assign the `baseline_half_life` penalty conditionally.
4. Deploy to `.github/workflows/deploy-pages.yml`.
