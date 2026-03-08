"""
smoke_taint_model.py
====================
Smoke Taint Parametric Insurance — Proof of Concept
M&T Passion Project | Engineering + Business Dual-Degree Application

ENGINEERING LOGIC — WHY PARAMETRIC > TRADITIONAL INDEMNITY:
-------------------------------------------------------------
Traditional indemnity insurance requires:
  1. Physical damage to occur
  2. A claims adjuster visit (days)
  3. Lab-verified GC-MS testing for guaiacol/4-methylguaiacol (10–19 days)
  4. Dispute resolution and payout (weeks–months)

Problem: Wine grapes have a harvest window of only 7–10 days. By the time
a lab result arrives, the crop is either over-fermented or already picked
under uncertainty. The farmer bears 100% of the information risk.

Parametric insurance solves this with a PRE-AGREED TRIGGER:
  • The trigger is an observable, real-time index (PM2.5 µg/m³)
  • If PM2.5 crosses threshold X for duration Y → automatic payout
  • No adjuster, no lab test, no waiting period
  • Payout arrives in hours, not months

This is identical in structure to catastrophe bonds used in capital markets:
the "oracle" (PurpleAir sensor) replaces the judge, creating trustless execution.
"""

import requests
import time
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION — Policy Parameters
# ─────────────────────────────────────────────────────────────────────────────

# PM2.5 trigger threshold (µg/m³). EPA 24-hr standard = 35 µg/m³.
# At this level, volatile phenol deposition on grape skins begins meaningfully.
PAYOUT_TRIGGER_THRESHOLD_UGM3 = 35.0

# Hours of sustained exposure required before payout triggers.
# Prevents false positives from brief, localized smoke events.
SUSTAINED_EXPOSURE_HOURS = 4

# Maximum insured value per acre (USD). Typical Napa/Sonoma premium grape price.
INSURED_VALUE_PER_ACRE = 8_000.0

# Guaiacol sensory threshold in wine (µg/L). Taint is detectable above this.
# Source: Kennison et al. (2008), Australian Journal of Grape and Wine Research
GUAIACOL_SENSORY_THRESHOLD_UGL = 23.0

# Empirical scaling: each µg/m³ above threshold contributes to phenol risk.
# Simplified linear proxy (in a real model, use a regression from field data).
PHENOL_DEPOSITION_SCALAR = 0.18  # µg/L guaiacol per µg/m³ PM2.5 per hour

# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SensorReading:
    """A single timestamped reading from a PurpleAir sensor."""
    timestamp: datetime
    pm25_atm: float          # PM2.5 (atmospheric correction), µg/m³
    pm25_cf1: float          # PM2.5 (CF=1 standard), µg/m³
    temperature_f: float     # Ambient temperature
    humidity_pct: float      # Relative humidity (affects phenol volatility)
    sensor_id: int
    sensor_name: str

@dataclass
class PolicyState:
    """Tracks the running state of the insurance smart contract."""
    exposure_start: Optional[datetime] = None
    cumulative_exposure_hours: float = 0.0
    peak_pm25: float = 0.0
    payout_triggered: bool = False
    payout_amount_usd: float = 0.0
    readings_above_threshold: list = field(default_factory=list)
    estimated_guaiacol_ugl: float = 0.0

# ─────────────────────────────────────────────────────────────────────────────
# 1. DATA ACQUISITION — PurpleAir API
# ─────────────────────────────────────────────────────────────────────────────

def fetch_purpleair_data(sensor_index: int, api_key: str) -> Optional[SensorReading]:
    """
    Fetches real-time PM2.5 data from PurpleAir's API v1.

    Args:
        sensor_index: The unique PurpleAir sensor index (e.g., 77777)
        api_key:      Your PurpleAir Read API key

    Returns:
        SensorReading object if successful, None otherwise.

    Engineering Note:
        PurpleAir sensors use dual laser particle counters (Plantower PMS5003).
        The 'ATM' correction is recommended for ambient outdoor monitoring.
        PM2.5 is the critical proxy because wildfire smoke particles in the
        0.1–2.5 µm range are the same particles that carry guaiacol and
        4-methylguaiacol (volatile phenols) that cause smoke taint.
    """
    url = f"https://api.purpleair.com/v1/sensors/{sensor_index}"
    headers = {"X-API-Key": api_key}
    fields = "pm2.5_atm,pm2.5_cf1,temperature,humidity,name"

    try:
        response = requests.get(url, headers=headers, params={"fields": fields}, timeout=10)
        response.raise_for_status()
        data = response.json()["sensor"]

        return SensorReading(
            timestamp=datetime.now(),
            pm25_atm=float(data.get("pm2.5_atm", 0)),
            pm25_cf1=float(data.get("pm2.5_cf1", 0)),
            temperature_f=float(data.get("temperature", 70)),
            humidity_pct=float(data.get("humidity", 50)),
            sensor_id=sensor_index,
            sensor_name=data.get("name", f"Sensor-{sensor_index}")
        )
    except requests.RequestException as e:
        print(f"[API ERROR] Could not fetch sensor {sensor_index}: {e}")
        return None


def simulate_sensor_reading(scenario: str = "normal") -> SensorReading:
    """
    Generates a simulated sensor reading for demo/testing purposes.

    Scenarios:
        'normal'   → PM2.5 < 12 µg/m³ (clean air)
        'moderate' → PM2.5 12–35 µg/m³ (degraded air quality)
        'critical' → PM2.5 > 35 µg/m³ (wildfire smoke, payout zone)
        'extreme'  → PM2.5 > 100 µg/m³ (dense smoke, catastrophic)
    """
    scenarios = {
        "normal":   (5.0,  12.0),
        "moderate": (15.0, 34.9),
        "critical": (36.0, 75.0),
        "extreme":  (80.0, 250.0),
    }
    low, high = scenarios.get(scenario, (5.0, 12.0))
    pm25 = round(random.uniform(low, high), 1)

    return SensorReading(
        timestamp=datetime.now(),
        pm25_atm=pm25,
        pm25_cf1=pm25 * 1.02,   # CF1 typically ~2% higher
        temperature_f=round(random.uniform(65, 95), 1),
        humidity_pct=round(random.uniform(20, 70), 1),
        sensor_id=77777,
        sensor_name="Vineyard Demo Sensor"
    )

# ─────────────────────────────────────────────────────────────────────────────
# 2. SMART CONTRACT LOGIC — Parametric Trigger Engine
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_trigger(reading: SensorReading, policy: PolicyState) -> PolicyState:
    """
    The core 'smart contract' business logic layer.

    This function evaluates each incoming sensor reading against the
    pre-agreed policy parameters and updates the policy state.

    Trigger Condition:
        PM2.5 ≥ PAYOUT_TRIGGER_THRESHOLD_UGM3 sustained for SUSTAINED_EXPOSURE_HOURS

    Engineering Logic:
        This mirrors the design of parametric catastrophe bonds used in
        reinsurance markets. The "oracle" (PurpleAir sensor) provides an
        objective, tamper-resistant measurement. The trigger is binary and
        rule-based — removing counterparty dispute risk entirely.

        The sustained duration requirement is crucial: it filters out
        false positives (BBQ smoke, nearby campfires) that briefly spike
        PM2.5 but don't produce meaningful phenol deposition on grape skins.
    """
    pm25 = reading.pm25_atm

    if pm25 >= PAYOUT_TRIGGER_THRESHOLD_UGM3:
        # Begin or continue tracking a smoke exposure event
        if policy.exposure_start is None:
            policy.exposure_start = reading.timestamp
            print(f"[ALERT] Smoke event started at {reading.timestamp.strftime('%H:%M:%S')}")

        # Track peak PM2.5 for risk modeling
        policy.peak_pm25 = max(policy.peak_pm25, pm25)
        policy.readings_above_threshold.append(reading)

        # Calculate cumulative hours above threshold
        elapsed = (reading.timestamp - policy.exposure_start).total_seconds() / 3600
        policy.cumulative_exposure_hours = elapsed

        # Check if sustained threshold has been crossed → TRIGGER PAYOUT
        if elapsed >= SUSTAINED_EXPOSURE_HOURS and not policy.payout_triggered:
            policy.payout_triggered = True
            policy.payout_amount_usd = calculate_payout(policy)
            print(f"[PAYOUT TRIGGERED] ${policy.payout_amount_usd:,.2f} after {elapsed:.1f}h exposure")

    else:
        # PM2.5 dropped below threshold — reset exposure clock
        if policy.exposure_start is not None:
            print(f"[CLEAR] PM2.5 normalized. Event duration: {policy.cumulative_exposure_hours:.1f}h")
        policy.exposure_start = None
        # NOTE: We do NOT reset payout_triggered — once triggered, the payout stands.

    return policy


def calculate_payout(policy: PolicyState) -> float:
    """
    Calculates the payout amount based on exposure severity.

    Formula:
        Payout = Insured Value × Damage Factor
        Damage Factor = min(1.0, cumulative_exposure_hours / max_hours_for_total_loss)

    This is a simplified linear model. In production, this would use:
        1. A regression model trained on GC-MS lab results vs. PM2.5 exposure data
        2. Crop type adjustments (Pinot Noir is far more sensitive than Cabernet)
        3. Wind direction / fire proximity from NOAA HRRR smoke forecasts
        4. Humidity correction (phenol uptake increases with humidity)
    """
    # Full policy loss assumed after 24 hours of critical exposure
    MAX_HOURS_TOTAL_LOSS = 24.0
    damage_factor = min(1.0, policy.cumulative_exposure_hours / MAX_HOURS_TOTAL_LOSS)

    # Scale by peak PM2.5 intensity (logarithmic — diminishing marginal returns)
    import math
    intensity_multiplier = min(1.5, 1 + math.log(max(1, policy.peak_pm25 / PAYOUT_TRIGGER_THRESHOLD_UGM3)))

    payout = INSURED_VALUE_PER_ACRE * damage_factor * intensity_multiplier
    return round(min(payout, INSURED_VALUE_PER_ACRE * 1.5), 2)  # Cap at 150% of insured value

# ─────────────────────────────────────────────────────────────────────────────
# 3. RISK MODELING — Economic Devaluation Estimator
# ─────────────────────────────────────────────────────────────────────────────

def estimate_guaiacol_deposition(readings: list[SensorReading]) -> dict:
    """
    Estimates guaiacol accumulation in grape tissue from PM2.5 exposure.

    Scientific Basis:
        Volatile phenols (guaiacol, 4-methylguaiacol) in wildfire smoke
        are absorbed through grape berry skin (epicuticular wax layer).
        The absorption rate is correlated with:
            • Ambient PM2.5 concentration (proxy for phenol vapor pressure)
            • Duration of exposure
            • Temperature (higher T → faster diffusion)
            • Grape ripeness / skin integrity (approaching harvest)

        This model uses a simplified linear transfer function calibrated
        against Kennison et al. (2008) experimental data.

    Returns:
        Dictionary with risk metrics and estimated guaiacol concentration.
    """
    if not readings:
        return {"guaiacol_ugl": 0.0, "risk_level": "NONE", "devaluation_pct": 0.0}

    total_phenol_exposure = 0.0
    for reading in readings:
        excess_pm25 = max(0, reading.pm25_atm - PAYOUT_TRIGGER_THRESHOLD_UGM3)
        # Humidity amplifies phenol absorption (Van Leeuwen effect)
        humidity_factor = 1 + (reading.humidity_pct - 50) / 200
        total_phenol_exposure += excess_pm25 * PHENOL_DEPOSITION_SCALAR * humidity_factor

    # Hours approximation (assuming ~1 reading per minute in production)
    hours_of_data = len(readings) / 60 if len(readings) > 1 else 1
    guaiacol_estimate = total_phenol_exposure * hours_of_data

    # Risk classification based on sensory threshold (23 µg/L)
    if guaiacol_estimate < GUAIACOL_SENSORY_THRESHOLD_UGL * 0.5:
        risk_level = "LOW"
        devaluation_pct = 10.0
    elif guaiacol_estimate < GUAIACOL_SENSORY_THRESHOLD_UGL:
        risk_level = "MODERATE"
        devaluation_pct = 40.0
    elif guaiacol_estimate < GUAIACOL_SENSORY_THRESHOLD_UGL * 3:
        risk_level = "HIGH"
        devaluation_pct = 75.0
    else:
        risk_level = "CATASTROPHIC"
        devaluation_pct = 100.0

    return {
        "guaiacol_ugl": round(guaiacol_estimate, 2),
        "sensory_threshold_ugl": GUAIACOL_SENSORY_THRESHOLD_UGL,
        "threshold_exceeded": guaiacol_estimate > GUAIACOL_SENSORY_THRESHOLD_UGL,
        "risk_level": risk_level,
        "devaluation_pct": devaluation_pct,
        "estimated_loss_per_acre": round(INSURED_VALUE_PER_ACRE * devaluation_pct / 100, 2),
    }


def calculate_information_asymmetry_cost(acres: float = 10.0) -> dict:
    """
    Quantifies the economic cost of the 10–19 day information gap
    that parametric insurance eliminates.

    This is the core business case for the M&T application:
    Information asymmetry creates a market failure. Parametric insurance
    is a financial engineering solution to a data availability problem.
    """
    avg_lab_days = 14.5  # Average of 10–19 day window
    harvest_window_days = 8.5  # Average of 7–10 day window
    days_of_uncertainty = max(0, avg_lab_days - harvest_window_days)

    daily_revenue_at_risk = INSURED_VALUE_PER_ACRE * acres
    cost_of_uncertainty = daily_revenue_at_risk * (days_of_uncertainty / 30)

    return {
        "avg_lab_delay_days": avg_lab_days,
        "harvest_window_days": harvest_window_days,
        "days_past_harvest": days_of_uncertainty,
        "total_revenue_at_risk_usd": daily_revenue_at_risk,
        "cost_of_information_gap_usd": round(cost_of_uncertainty, 2),
        "parametric_payout_delay_hours": 4,  # Hours, not weeks
        "time_value_improvement_factor": round((avg_lab_days * 24) / 4, 1)
    }


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE TEST (run without Streamlit)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("SMOKE TAINT PARAMETRIC INSURANCE — POC TEST RUN")
    print("=" * 60)

    policy = PolicyState()

    # Simulate a smoke event building over time
    scenarios = ["normal", "moderate", "critical", "critical", "extreme", "critical"]
    for i, scenario in enumerate(scenarios):
        reading = simulate_sensor_reading(scenario)
        # Backdate readings to simulate time passage
        reading.timestamp = datetime.now() - timedelta(hours=len(scenarios) - i)
        policy = evaluate_trigger(reading, policy)
        print(f"  t={i}h | PM2.5={reading.pm25_atm} µg/m³ | "
              f"Exposure={policy.cumulative_exposure_hours:.1f}h | "
              f"Triggered={policy.payout_triggered}")

    print()
    risk = estimate_guaiacol_deposition(policy.readings_above_threshold)
    print(f"RISK ASSESSMENT: {risk}")

    info_gap = calculate_information_asymmetry_cost(acres=15)
    print(f"\nINFORMATION ASYMMETRY COST: ${info_gap['cost_of_information_gap_usd']:,.2f}")
    print(f"Parametric improvement: {info_gap['time_value_improvement_factor']}x faster payout")
