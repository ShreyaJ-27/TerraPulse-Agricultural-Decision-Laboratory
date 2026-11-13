# TerraPulse — Interactive Judge & Demo Walkthrough Guide

**Team:** Kalakand  
**Date:** November 14, 2026  
**Target Branch:** `feature/terrapulse-complete-platform`

---

## 1. Quick Access & Live Service URLs

| Interface | URL | Purpose |
| :--- | :--- | :--- |
| **Cinematic Landing Page** | [http://127.0.0.1:5173/](http://127.0.0.1:5173/) | 3D visual showcase, feature overviews, 1-click demo launch |
| **Demo Farm Direct** | [http://127.0.0.1:5173/demo](http://127.0.0.1:5173/demo) | 1-click entry into pre-configured PAU-UAS research farm |
| **Agricultural Dashboard** | [http://127.0.0.1:5173/dashboard](http://127.0.0.1:5173/dashboard) | Unified decision cockpit across all 8 modules |
| **Interactive API Documentation** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Fast-API OpenAPI Swagger specification & live testing |
| **Database Connection** | `localhost:5433` (PostGIS) | PostgreSQL 16 + PostGIS 3.4 (`terrapulse` / `terrapulse`) |

> **Pre-Seeded Demo Farm ID**: `00000000-0000-0000-0000-000000000001`  
> **Location**: Punjab Agricultural University (PAU) & UAS Joint Agro-Research Station, Ludhiana ($30.9010^\circ\text{N}, 75.8073^\circ\text{E}$).

---

## 2. Walkthrough Scenarios for Judges

### Scenario A: Cinematic 3D First Impressions
**Goal**: Experience the living environment and entry points.

1. Open your browser and navigate to **`http://127.0.0.1:5173/`**.
2. **Visual Observation**:
   - Notice the procedural 3D field with animated waving crops responding to the dynamic wind shader.
   - The golden-hour atmosphere renders real-time volumetric shadows and soft sky illumination.
   - Slowly move your cursor across the screen: the 3D camera gently responds with parallax perspective.
3. Click the prominent glowing button: **`Launch Interactive Demo Farm`** (or **`Explore Demo Farm`**).
4. You are instantly routed into the **Agricultural Dashboard** with the pre-seeded Ludhiana research station loaded.

---

### Scenario B: The Living Field & Soil Cutaway Inspection
**Goal**: Inspect multi-plot agricultural states and sub-surface soil moisture in 3D.

1. In the dashboard top navigation bar, click on **`Living Field`** (or the **`3D Field`** badge).
2. **Explore 3D Plots**:
   - **Field 1 (North)**: Hybrid Maize (Pioneer 3396) — Broad green leaf canopies.
   - **Field 2 (Center)**: Turmeric (Prathibha) — Raised beds with moisture indicators.
   - **Field 3 (South)**: Wheat (PBW 824) — Dense tillering canopy.
3. Click on **`Field 1 (Maize)`**:
   - The detail drawer opens displaying live telemetry:
     - Stage: *Vegetative / Tasseling*
     - Root Depth: $0.85\text{ m}$
     - Actual Evapotranspiration ($ET_a$): $5.2\text{ mm/day}$
     - Soil Moisture Deficit: $18.4\%$
4. Click the **`Inspect Soil Profile`** toggle switch:
   - The terrain renders a 4-layer soil cutaway:
     - **0–15 cm (Topsoil)**: $0.28\text{ m}^3/\text{m}^3$
     - **15–30 cm (Subsoil)**: $0.32\text{ m}^3/\text{m}^3$
     - **30–60 cm (Deep Root Zone)**: $0.29\text{ m}^3/\text{m}^3$
     - **60–100 cm (Substratum)**: $0.24\text{ m}^3/\text{m}^3$

---

### Scenario C: Future Fold & Water Decision Comparison
**Goal**: Compare two alternate futures under identical weather trajectories.

1. Click on the **`Future Fold`** tab in the top navigation.
2. Observe the synchronized side-by-side view:
   - **Left Panel (Branch A - Baseline)**: Conventional Flood Irrigation (80 mm flood event every 14 days).
   - **Right Panel (Branch B - Precision Drip)**: Deficit-scheduled drip irrigation (25 mm pulse upon reaching 50% RAW threshold).
3. **Inspect the Water-Decision Score (Contract C5)**:
   - Branch A Score: **68.2 / 100**
   - Branch B Score: **92.0 / 100** (+23.8 points!)
4. **Review Metric Breakdown**:
   - **Water Applied**: Branch A used $240\text{ mm}$; Branch B used only $145\text{ mm}$ (39.5% water savings).
   - **Water Stress Days**: Branch A had 4 days of intermittent waterlogging and 3 days of late stress; Branch B had 0 stress days.
   - **Reservoir Impact**: Branch B preserved $117,500\text{ Litres}$ in the shared farm reservoir.
5. **Verify Weather Fairness (Contract C4)**:
   - Note the weather overlay badge: both branches were evaluated against the exact same Open-Meteo ensemble forecast (Max Temp $36.4^\circ\text{C}$, $0\text{ mm}$ rain).

---

### Scenario D: Agricultural Calendar 2.0 & Agronomic "Why?"
**Goal**: Review season-wise crop planning and scientific rationale.

1. Click on the **`Agricultural Calendar`** tab in the dashboard.
2. **Season Selector**:
   - Switch between **`Kharif (Monsoon)`**, **`Rabi (Winter)`**, and **`Zaid (Summer)`**.
3. **Regional Intelligence Profile**:
   - Select **`Central Punjab (PAU Ludhiana)`** from the regional dropdown.
   - Notice the recommended sowing windows, critical irrigation timings, and fertilizer application stages.
4. **Inspect "Why?" Explanations**:
   - Click on the informational badge next to *Maize Sowing (June 1–15)*.
   - Notice the scientific justification: *"Aligns peak vegetative water demand with onset of South-West monsoon; protects silk emergence from extreme pre-monsoon heat waves exceeding 42°C."*
5. Test the custom calendar generation by changing soil type or target crop and clicking **`Regenerate Recommendations`**.

---

### Scenario E: Real-Time Alerts & Telegram Simulation
**Goal**: Trigger automated notifications and verify Telegram outbox delivery.

1. Click on the **`Notifications & Telegram`** tab.
2. Notice the active alerts table:
   - `CRITICAL`: *Extreme Heatwave Warning (Day 14)* — Temperature forecast exceeds $38.5^\circ\text{C}$.
   - `WARNING`: *Root Zone Moisture Depletion in Field 1* — Soil moisture dropped below 50% RAW.
   - `ADVISORY`: *Optimal Sowing Window Opening for Wheat (Field 3)*.
3. **Simulate Live Test Dispatch**:
   - Click the green **`Test Alert Dispatch`** button.
   - The backend runs `POST /api/v1/notifications/farms/00000000-0000-0000-0000-000000000001/test`.
   - A success banner will confirm: *"Alert evaluated and dispatched to Telegram outbox!"*
4. **Verify Telegram Status**:
   - Under the *Telegram Channel Binding* card, notice:
     - Status: **CONNECTED** (Chat ID: `demo_farmer_chat_9814`)
     - Channel: `@TerraPulseAlertsBot`
     - Last Delivery: *Just now (Delivered with 0ms delay)*.
5. **Quiet Hours Verification**:
   - Toggle the quiet hours switch to test nighttime suppression logic (22:00–07:00 IST).

---

### Scenario F: Crop Lens & Multicrop Reservoir Ledger
**Goal**: Search botanical taxonomy and verify farm-level water conservation (Contract C8).

1. Click on the **`Crop Lens`** tab:
   - Type `Turmeric` or `Curcuma longa` into the search bar.
   - The dynamic resolver pulls data from FAO AGROVOC and GBIF:
     - Botanical Binomial: *Curcuma longa L.* (Family: Zingiberaceae).
     - Authoritative Engine: *FAO-56 Dual Crop Coefficient Model*.
     - Parameters: $K_{cb,ini} = 0.50$, $K_{cb,mid} = 1.05$, $K_{cb,end} = 0.75$, Max Root Depth: $0.60\text{ m}$.
2. Click on the **`Water Management`** tab:
   - Central Reservoir: **750,000 Litres Capacity**.
   - Available Balance: **632,500 Litres** (84.3% full).
   - Review the multi-plot withdrawal ledger:
     - Plot 1 (Maize): $48,000\text{ L}$ withdrawn on Day 6.
     - Plot 2 (Turmeric): $32,000\text{ L}$ withdrawn on Day 8.
     - Plot 3 (Wheat): $37,500\text{ L}$ withdrawn on Day 12.
   - **Contract C8 Invariant**: Water ledger strictly verifies that $1\text{ mm} \times 1\text{ m}^2 = 1\text{ Litre}$ across all plot boundaries.

---

## 3. Fast CLI Verification Commands for Judges

You can also verify any subsystem directly from your terminal using `curl`:

```bash
# 1. Fetch Demo Farm Metadata
curl -s http://127.0.0.1:8000/api/v1/farms/00000000-0000-0000-0000-000000000001 | jq .name

# 2. Query Agricultural Calendar Seasons
curl -s http://127.0.0.1:8000/api/v1/agri-calendar/seasons | jq .seasons[].name

# 3. Query Regional Profile for Central Punjab
curl -s http://127.0.0.1:8000/api/v1/agri-calendar/regional/punjab_central | jq .region_name

# 4. Trigger Real-Time Notification Evaluation
curl -s -X POST http://127.0.0.1:8000/api/v1/notifications/farms/00000000-0000-0000-0000-000000000001/test | jq .

# 5. Check Telegram Subscription Status
curl -s http://127.0.0.1:8000/api/v1/notifications/telegram/status/00000000-0000-0000-0000-000000000001 | jq .
```

