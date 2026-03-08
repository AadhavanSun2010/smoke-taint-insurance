"""
dashboard.py
============
Smoke Taint Parametric Insurance — Live Risk Dashboard
Built with Streamlit | M&T Passion Project POC

Run with:  streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random
import time
from smoke_taint_model import (
    simulate_sensor_reading,
    evaluate_trigger,
    estimate_guaiacol_deposition,
    calculate_information_asymmetry_cost,
    PolicyState,
    PAYOUT_TRIGGER_THRESHOLD_UGM3,
    SUSTAINED_EXPOSURE_HOURS,
    INSURED_VALUE_PER_ACRE,
    GUAIACOL_SENSORY_THRESHOLD_UGL,
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smoke Taint Insurance | Risk Dashboard",
    page_icon="🍇",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS — Dark Wine-Country Aesthetic
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=JetBrains+Mono:wght@400;600&family=Inter:wght@300;400;500&display=swap');

/* Global */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.stApp {
    background: linear-gradient(135deg, #0d0d0d 0%, #1a0a0a 50%, #0d1a0d 100%);
    color: #e8dcc8;
}

/* Header */
.main-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.8rem;
    font-weight: 700;
    color: #c9a84c;
    letter-spacing: -0.02em;
    line-height: 1.1;
    margin-bottom: 0.2rem;
}
.sub-title {
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    color: #8a7a6a;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 2rem;
}

/* Status Cards */
.status-card {
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    border: 1px solid rgba(255,255,255,0.08);
}
.status-normal {
    background: linear-gradient(135deg, #0a1f0a, #0d2b0d);
    border-left: 4px solid #4caf50;
}
.status-warning {
    background: linear-gradient(135deg, #1f1a0a, #2b230d);
    border-left: 4px solid #ff9800;
}
.status-critical {
    background: linear-gradient(135deg, #1f0a0a, #2b0d0d);
    border-left: 4px solid #f44336;
    animation: pulse-border 2s infinite;
}
@keyframes pulse-border {
    0%, 100% { border-left-color: #f44336; }
    50% { border-left-color: #ff6b6b; }
}

/* Metric labels */
.metric-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #8a7a6a;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.3rem;
}
.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.2rem;
    font-weight: 600;
    line-height: 1;
}
.metric-unit {
    font-size: 0.9rem;
    color: #8a7a6a;
    margin-left: 0.2rem;
}

/* Info boxes */
.info-box {
    background: rgba(201, 168, 76, 0.08);
    border: 1px solid rgba(201, 168, 76, 0.2);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    font-size: 0.85rem;
    color: #c9a84c;
}

/* Payout alert */
.payout-alert {
    background: linear-gradient(135deg, #1a0a2e, #0a1a2e);
    border: 2px solid #7b68ee;
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
    animation: glow 2s infinite;
}
@keyframes glow {
    0%, 100% { box-shadow: 0 0 20px rgba(123,104,238,0.3); }
    50% { box-shadow: 0 0 40px rgba(123,104,238,0.6); }
}

/* Streamlit overrides */
[data-testid="stMetricValue"] { color: #e8dcc8 !important; }
[data-testid="stSidebar"] { background: #0a0a0a !important; }
.stButton>button {
    background: linear-gradient(135deg, #722f37, #9b2335) !important;
    color: #e8dcc8 !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    letter-spacing: 0.05em !important;
    padding: 0.6rem 1.5rem !important;
}
.stButton>button:hover {
    background: linear-gradient(135deg, #9b2335, #c0392b) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(155,35,53,0.4) !important;
}
div[data-testid="stSelectbox"] label { color: #8a7a6a !important; }
.stSlider>div>div { color: #c9a84c !important; }

/* Section headers */
.section-header {
    font-family: 'Playfair Display', serif;
    font-size: 1.1rem;
    color: #c9a84c;
    border-bottom: 1px solid rgba(201,168,76,0.2);
    padding-bottom: 0.5rem;
    margin: 1.5rem 0 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────
if "policy" not in st.session_state:
    st.session_state.policy = PolicyState()
if "history" not in st.session_state:
    st.session_state.history = []
if "scenario" not in st.session_state:
    st.session_state.scenario = "normal"
if "payout_simulated" not in st.session_state:
    st.session_state.payout_simulated = False
if "acres" not in st.session_state:
    st.session_state.acres = 10.0

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — Configuration & Controls
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🍇 Vineyard Config")
    st.markdown("---")

    acres = st.slider("Insured Acres", 1, 100, 10)
    st.session_state.acres = float(acres)

    st.markdown("---")
    st.markdown("### 🌫️ Smoke Scenario")
    scenario = st.selectbox(
        "Select atmospheric condition",
        ["normal", "moderate", "critical", "extreme"],
        format_func=lambda x: {
            "normal": "🟢 Normal (< 12 µg/m³)",
            "moderate": "🟡 Moderate (12–35 µg/m³)",
            "critical": "🔴 Critical (35–75 µg/m³)",
            "extreme": "⚫ Extreme (> 80 µg/m³)",
        }[x]
    )
    st.session_state.scenario = scenario

    if st.button("📡 Fetch New Reading"):
        reading = simulate_sensor_reading(st.session_state.scenario)
        st.session_state.policy = evaluate_trigger(reading, st.session_state.policy)
        st.session_state.history.append({
            "time": reading.timestamp.strftime("%H:%M:%S"),
            "pm25": reading.pm25_atm,
            "temp_f": reading.temperature_f,
            "humidity": reading.humidity_pct,
            "threshold": PAYOUT_TRIGGER_THRESHOLD_UGM3,
        })
        # Keep last 30 readings
        if len(st.session_state.history) > 30:
            st.session_state.history = st.session_state.history[-30:]

    if st.button("🔄 Reset Policy"):
        st.session_state.policy = PolicyState()
        st.session_state.history = []
        st.session_state.payout_simulated = False

    st.markdown("---")
    st.markdown("### 📋 Policy Parameters")
    st.markdown(f"""
    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #8a7a6a; line-height: 1.8;">
    Trigger: <span style="color:#c9a84c">{PAYOUT_TRIGGER_THRESHOLD_UGM3} µg/m³</span><br>
    Duration: <span style="color:#c9a84c">{SUSTAINED_EXPOSURE_HOURS}h sustained</span><br>
    Insured: <span style="color:#c9a84c">${INSURED_VALUE_PER_ACRE:,}/acre</span><br>
    Guaiacol threshold: <span style="color:#c9a84c">{GUAIACOL_SENSORY_THRESHOLD_UGL} µg/L</span>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🍷 Smoke Taint Risk Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Parametric Crop Insurance · Real-Time PM₂.₅ Intelligence · M&T Passion Project</div>', unsafe_allow_html=True)

# ── Live Status Banner ──────────────────────────────────────────────────────
policy = st.session_state.policy
latest_pm25 = st.session_state.history[-1]["pm25"] if st.session_state.history else 0.0

if policy.payout_triggered or st.session_state.payout_simulated:
    status_class = "status-critical"
    status_icon = "🚨"
    status_text = "PAYOUT TRIGGERED — CONTRACT EXECUTED"
    status_color = "#f44336"
elif latest_pm25 >= PAYOUT_TRIGGER_THRESHOLD_UGM3:
    status_class = "status-warning"
    status_icon = "⚠️"
    status_text = f"SMOKE EVENT ACTIVE — Monitoring ({policy.cumulative_exposure_hours:.1f}h / {SUSTAINED_EXPOSURE_HOURS}h required)"
    status_color = "#ff9800"
else:
    status_class = "status-normal"
    status_icon = "✅"
    status_text = "NORMAL — PM₂.₅ Below Trigger Threshold"
    status_color = "#4caf50"

st.markdown(f"""
<div class="status-card {status_class}">
    <span style="font-size:1.3rem">{status_icon}</span>
    <span style="font-family:'JetBrains Mono',monospace; font-size:0.9rem; color:{status_color}; font-weight:600; margin-left:0.8rem">
        {status_text}
    </span>
</div>
""", unsafe_allow_html=True)

# ── Key Metrics Row ──────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    pm_color = "#f44336" if latest_pm25 >= PAYOUT_TRIGGER_THRESHOLD_UGM3 else "#4caf50"
    st.markdown(f"""
    <div class="metric-label">Current PM₂.₅</div>
    <div class="metric-value" style="color:{pm_color}">{latest_pm25}<span class="metric-unit">µg/m³</span></div>
    """, unsafe_allow_html=True)

with col2:
    exp_color = "#f44336" if policy.cumulative_exposure_hours >= SUSTAINED_EXPOSURE_HOURS else "#e8dcc8"
    st.markdown(f"""
    <div class="metric-label">Exposure Duration</div>
    <div class="metric-value" style="color:{exp_color}">{policy.cumulative_exposure_hours:.1f}<span class="metric-unit">hours</span></div>
    """, unsafe_allow_html=True)

with col3:
    payout = policy.payout_amount_usd * (st.session_state.acres / 1)
    payout_color = "#7b68ee" if policy.payout_triggered else "#8a7a6a"
    st.markdown(f"""
    <div class="metric-label">Payout Amount</div>
    <div class="metric-value" style="color:{payout_color}">${payout:,.0f}<span class="metric-unit">USD</span></div>
    """, unsafe_allow_html=True)

with col4:
    peak_color = "#f44336" if policy.peak_pm25 >= PAYOUT_TRIGGER_THRESHOLD_UGM3 else "#e8dcc8"
    st.markdown(f"""
    <div class="metric-label">Peak PM₂.₅</div>
    <div class="metric-value" style="color:{peak_color}">{policy.peak_pm25:.1f}<span class="metric-unit">µg/m³</span></div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Charts ──────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown('<div class="section-header">📊 PM₂.₅ Time Series vs. Insurance Trigger</div>', unsafe_allow_html=True)

    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)

        fig = go.Figure()

        # Threshold zone fill
        fig.add_hrect(
            y0=PAYOUT_TRIGGER_THRESHOLD_UGM3, y1=max(df["pm25"].max() * 1.2, 50),
            fillcolor="rgba(244,67,54,0.08)", line_width=0,
            annotation_text="PAYOUT ZONE", annotation_position="top right",
            annotation_font_color="#f44336", annotation_font_size=10
        )

        # PM2.5 line
        fig.add_trace(go.Scatter(
            x=df["time"], y=df["pm25"],
            name="PM₂.₅ (µg/m³)",
            line=dict(color="#c9a84c", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(201,168,76,0.1)",
            mode="lines+markers",
            marker=dict(size=5, color="#c9a84c")
        ))

        # Trigger threshold line
        fig.add_hline(
            y=PAYOUT_TRIGGER_THRESHOLD_UGM3,
            line_dash="dash", line_color="#f44336", line_width=1.5,
            annotation_text=f"Trigger: {PAYOUT_TRIGGER_THRESHOLD_UGM3} µg/m³",
            annotation_font_color="#f44336",
            annotation_position="bottom right"
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="JetBrains Mono", color="#8a7a6a", size=11),
            xaxis=dict(
                showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                title="Time", title_font_color="#8a7a6a",
                tickfont_color="#8a7a6a", showline=False
            ),
            yaxis=dict(
                showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                title="PM₂.₅ (µg/m³)", title_font_color="#8a7a6a",
                tickfont_color="#8a7a6a", showline=False, rangemode="tozero"
            ),
            legend=dict(font=dict(color="#8a7a6a"), bgcolor="rgba(0,0,0,0)"),
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown("""
        <div class="info-box">
            📡 No readings yet. Use the sidebar to fetch sensor data and populate the chart.
        </div>
        """, unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="section-header">🧪 Guaiacol Risk Model</div>', unsafe_allow_html=True)

    risk = estimate_guaiacol_deposition(policy.readings_above_threshold)

    # Guaiacol gauge
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=risk["guaiacol_ugl"],
        delta={"reference": GUAIACOL_SENSORY_THRESHOLD_UGL, "increasing": {"color": "#f44336"}},
        title={"text": "Est. Guaiacol<br><span style='font-size:0.7em;color:#8a7a6a'>µg/L in grape tissue</span>",
               "font": {"color": "#c9a84c", "family": "Playfair Display"}},
        number={"suffix": " µg/L", "font": {"color": "#e8dcc8", "family": "JetBrains Mono"}},
        gauge={
            "axis": {"range": [0, GUAIACOL_SENSORY_THRESHOLD_UGL * 4],
                     "tickcolor": "#8a7a6a", "tickfont": {"color": "#8a7a6a", "size": 9}},
            "bar": {"color": "#c9a84c"},
            "bgcolor": "rgba(0,0,0,0)",
            "steps": [
                {"range": [0, GUAIACOL_SENSORY_THRESHOLD_UGL * 0.5], "color": "rgba(76,175,80,0.15)"},
                {"range": [GUAIACOL_SENSORY_THRESHOLD_UGL * 0.5, GUAIACOL_SENSORY_THRESHOLD_UGL], "color": "rgba(255,152,0,0.15)"},
                {"range": [GUAIACOL_SENSORY_THRESHOLD_UGL, GUAIACOL_SENSORY_THRESHOLD_UGL * 4], "color": "rgba(244,67,54,0.15)"},
            ],
            "threshold": {
                "line": {"color": "#f44336", "width": 2},
                "thickness": 0.8,
                "value": GUAIACOL_SENSORY_THRESHOLD_UGL
            }
        }
    ))
    fig_gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        height=230,
        margin=dict(l=10, r=10, t=30, b=10),
        font=dict(family="JetBrains Mono", color="#8a7a6a")
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    risk_colors = {"NONE": "#4caf50", "LOW": "#8bc34a", "MODERATE": "#ff9800",
                   "HIGH": "#f44336", "CATASTROPHIC": "#9c27b0"}
    rc = risk_colors.get(risk["risk_level"], "#8a7a6a")
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; font-family:'JetBrains Mono',monospace; font-size:0.78rem; margin-top:-0.5rem">
        <span style="color:#8a7a6a">Risk Level: <span style="color:{rc}; font-weight:600">{risk["risk_level"]}</span></span>
        <span style="color:#8a7a6a">Devaluation: <span style="color:{rc}">{risk["devaluation_pct"]:.0f}%</span></span>
    </div>
    """, unsafe_allow_html=True)

# ── Payout Simulation ────────────────────────────────────────────────────────
st.markdown('<div class="section-header">⚡ Smart Contract Execution</div>', unsafe_allow_html=True)

col_btn1, col_btn2, col_spacer = st.columns([2, 2, 4])

with col_btn1:
    can_simulate = latest_pm25 >= PAYOUT_TRIGGER_THRESHOLD_UGM3 or len(st.session_state.history) == 0
    if st.button("🚀 Simulate Payout", disabled=False):
        st.session_state.payout_simulated = True
        if not policy.payout_triggered:
            # Force a critical scenario for demo
            for _ in range(5):
                r = simulate_sensor_reading("critical")
                r.timestamp = datetime.now() - timedelta(hours=5)
                policy = evaluate_trigger(r, policy)
            st.session_state.policy = policy

with col_btn2:
    if st.button("📊 Load Demo Scenario"):
        # Populate with a realistic smoke event
        st.session_state.policy = PolicyState()
        st.session_state.history = []
        base_time = datetime.now() - timedelta(hours=6)
        event_pms = [8.2, 11.5, 22.3, 38.7, 55.1, 72.4, 61.8, 48.3, 39.1, 41.7, 44.2, 37.8]
        for i, pm in enumerate(event_pms):
            r = simulate_sensor_reading("normal")
            r.pm25_atm = pm
            r.timestamp = base_time + timedelta(minutes=i * 30)
            st.session_state.policy = evaluate_trigger(r, st.session_state.policy)
            st.session_state.history.append({
                "time": r.timestamp.strftime("%H:%M"),
                "pm25": pm,
                "temp_f": r.temperature_f,
                "humidity": r.humidity_pct,
                "threshold": PAYOUT_TRIGGER_THRESHOLD_UGM3,
            })
        st.rerun()

if st.session_state.payout_simulated or policy.payout_triggered:
    total_payout = max(policy.payout_amount_usd, INSURED_VALUE_PER_ACRE * 0.6) * st.session_state.acres
    st.markdown(f"""
    <div class="payout-alert">
        <div style="font-family:'Playfair Display',serif; font-size:1.5rem; color:#c9a84c; margin-bottom:0.5rem">
            ⚡ Parametric Payout Executed
        </div>
        <div style="font-family:'JetBrains Mono',monospace; font-size:2.5rem; color:#e8dcc8; font-weight:600">
            ${total_payout:,.2f} USD
        </div>
        <div style="font-size:0.8rem; color:#8a7a6a; margin-top:0.5rem">
            Triggered: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} · Settlement: Instant ·
            Basis: PM₂.₅ ≥ {PAYOUT_TRIGGER_THRESHOLD_UGM3} µg/m³ for ≥ {SUSTAINED_EXPOSURE_HOURS}h
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Business Case: Information Asymmetry ─────────────────────────────────────
st.markdown('<div class="section-header">📐 Why Parametric? — The Information Asymmetry Case</div>', unsafe_allow_html=True)

info_gap = calculate_information_asymmetry_cost(st.session_state.acres)

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric("Traditional Lab Delay", f"{info_gap['avg_lab_delay_days']} days",
              delta=f"{info_gap['days_past_harvest']:.1f} days past harvest", delta_color="inverse")
with col_b:
    st.metric("Parametric Payout Speed", f"{info_gap['parametric_payout_delay_hours']} hours",
              delta=f"{info_gap['time_value_improvement_factor']}× faster", delta_color="normal")
with col_c:
    st.metric("Cost of Information Gap", f"${info_gap['cost_of_information_gap_usd']:,.0f}",
              delta="Eliminated by parametric trigger", delta_color="normal")

st.markdown("""
<div class="info-box" style="margin-top:1rem">
    <strong>Engineering Insight:</strong> The GC-MS testing bottleneck (10–19 days) exceeds the harvest window
    (7–10 days), creating a <em>structurally unsolvable information problem</em> for traditional indemnity insurance.
    Parametric insurance resolves this by replacing the lab oracle with a real-time atmospheric oracle (PurpleAir),
    enabling trustless, instant settlement — identical to how catastrophe bonds function in capital markets.
    The PM₂.₅ proxy is scientifically justified: volatile phenols (guaiacol, 4-methylguaiacol) travel on
    fine particulate matter in the same 0.1–2.5 µm size range as wildfire smoke particles.
</div>
""", unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="font-family:'JetBrains Mono',monospace; font-size:0.7rem; color:#3a3030; text-align:center">
    Smoke Taint Parametric Insurance · M&T Dual-Degree Passion Project · Engineering × Business<br>
    Data: PurpleAir API v1 · Science: Kennison et al. (2008) · Model: Simplified Linear Phenol Transfer Function
</div>
""", unsafe_allow_html=True)
