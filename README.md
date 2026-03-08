# 🍷 Smoke Taint Parametric Insurance — Proof of Concept

### M&T Dual-Degree Passion Project | Engineering × Business

---

## Overview

This project addresses the **smoke taint crisis** in the wine industry using a
**parametric insurance model** that eliminates the deadly information asymmetry
between wildfire events and crop loss decisions.

---

## The Problem (Market Failure Analysis)

| Variable | Traditional System | Parametric System |
|---|---|---|
| Lab test delay | 10–19 days | N/A (not needed) |
| Harvest window | 7–10 days | 7–10 days |
| Information gap | **7–12 days past harvest** | Eliminated |
| Payout speed | Weeks–months | **< 4 hours** |
| Dispute risk | High | Zero (objective oracle) |

The core issue is a **structural information asymmetry**: GC-MS lab testing for
guaiacol (the volatile phenol that causes smoke taint) takes 10–19 days. But wine
grapes only remain harvestable for 7–10 days. By the time a farmer gets lab
results, their crop decision window has already closed.

This is a classic **liquidity risk + information risk** problem from financial
economics — identical to markets with delayed price discovery.

---

## The Parametric Solution

**Parametric insurance** replaces subjective damage assessment with a
pre-agreed, objective trigger:

```
IF PM2.5 ≥ 35 µg/m³ for ≥ 4 hours THEN trigger payout
```

Why PM2.5 as the trigger proxy?
- Wildfire smoke is composed of fine particulate matter (0.1–2.5 µm)
- Guaiacol and 4-methylguaiacol travel **adsorbed on these same particles**
- PM2.5 sensors (PurpleAir) provide real-time, tamper-resistant data
- This mirrors how catastrophe bonds use hurricane wind speed as a trigger

---

## Code Architecture

```
smoke_taint_poc/
├── smoke_taint_model.py   # Core business logic (4 modules)
│   ├── fetch_purpleair_data()      # 1. Data Acquisition
│   ├── evaluate_trigger()          # 2. Smart Contract Logic
│   ├── estimate_guaiacol_deposition()  # 3. Risk Modeling
│   └── calculate_information_asymmetry_cost()  # Business case
│
├── dashboard.py           # Streamlit web dashboard
└── requirements.txt       # Dependencies
```

### Module 1: Data Acquisition
Fetches real-time PM2.5 from PurpleAir API v1 using dual laser particle
counters (Plantower PMS5003). Uses the ATM correction factor for outdoor
ambient monitoring accuracy.

### Module 2: Smart Contract Logic
A stateful trigger engine that:
- Tracks sustained exposure above threshold
- Resets on normalization (prevents false positives)
- Executes payout calculation once trigger conditions are met
- Never reverts a triggered payout (irreversibility = contract validity)

### Module 3: Risk Modeling
Simplified linear phenol transfer function based on:
- Kennison et al. (2008): *Effect of smoke application to field-grown Merlot*
- Phenol deposition rate: 0.18 µg/L guaiacol per µg/m³ excess PM2.5 per hour
- Humidity correction factor (Van Leeuwen effect)
- Sensory threshold: 23 µg/L (below which wine is commercially viable)

---

## Setup & Run

```bash
# 1. Clone / download the project
cd smoke_taint_poc

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run standalone model test (no UI)
python smoke_taint_model.py

# 4. Launch the Streamlit dashboard
streamlit run dashboard.py
```

For live PurpleAir data (optional):
1. Register at purpleair.com → request a free Read API key
2. Find your nearest sensor index at map.purpleair.com
3. Call `fetch_purpleair_data(sensor_index=YOUR_INDEX, api_key="YOUR_KEY")`

---

## Why This Is an M&T Problem (Not Just Engineering OR Business)

This project sits at the exact intersection the M&T program targets:

**Engineering side:**
- Signal processing (PM2.5 as proxy for molecular phenol concentration)
- Sensor network architecture (PurpleAir mesh vs. point-source GC-MS)
- Parametric risk model design and calibration

**Business side:**
- Market failure identification (information asymmetry theory)
- Parametric financial product structuring (cat bond analogy)
- Basis risk quantification (PM2.5 ≠ guaiacol, but correlated enough)
- Liquidity provision to agricultural markets

The **engineering solution** (real-time sensor data) enables a **financial
innovation** (parametric payout) that creates **market efficiency** (no more
information asymmetry). Neither discipline alone gets you there.

---

## Limitations & Future Work

1. **Basis Risk**: PM2.5 is a proxy, not a direct guaiacol measurement.
   A true production model would require ML regression trained on paired
   PM2.5/GC-MS datasets from multiple wildfire seasons.

2. **Wind Direction**: Smoke must actually reach the vineyard. NOAA HRRR
   smoke forecasts should be incorporated for directional filtering.

3. **Grape Variety Adjustment**: Pinot Noir absorbs phenols 3× faster than
   Cabernet Sauvignon. Policy premiums should reflect variety sensitivity.

4. **Moral Hazard**: Parametric insurance can incentivize risky planting
   locations. Premium pricing must reflect micro-climate smoke exposure history.

---

## References

- Kennison, K.R. et al. (2008). *Effect of smoke application to field-grown
  Merlot grapevines at key phenological growth stages.* AJGWR.
- Cain, R.F. (2021). *Parametric insurance: A primer for agricultural risk.*
  Geneva Papers on Risk and Insurance.
- PurpleAir API Documentation: api.purpleair.com
- EPA PM2.5 NAAQS Standard: 35 µg/m³ (24-hour)
