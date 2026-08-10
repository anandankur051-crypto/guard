"""
AML Alert Re-ranker, refactored into a single render_aml_tab() function so
the unified guard/app.py can embed it as one tab alongside RegTrack.

Before this works, run (from the aml/ folder, once):
    python3 generate_data.py
    python3 train_model.py
"""

import os

import joblib
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Resolve paths relative to THIS file, not the caller's working directory --
# this is what lets the unified app.py at the repo root import this module
# and still find aml/artifacts correctly.
_HERE = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(_HERE, "artifacts")

FEATURE_LABELS = {
    "amount": "Transaction amount",
    "amount_vs_sender_avg": "Amount vs. this sender's usual size",
    "drain_ratio": "% of balance drained",
    "velocity_24h": "Transactions in last 24h (velocity)",
    "is_new_beneficiary": "First-time beneficiary",
    "hour_of_day": "Hour of day",
    "account_age_steps": "Account age (hours)",
}


@st.cache_data
def _load_artifacts():
    scored = pd.read_csv(f"{ARTIFACTS_DIR}/scored_alerts.csv")
    precision_at_k = pd.read_csv(f"{ARTIFACTS_DIR}/precision_at_k.csv")
    features = joblib.load(f"{ARTIFACTS_DIR}/features.joblib")
    return scored, precision_at_k, features


def render_aml_tab():
    try:
        scored, precision_at_k, features = _load_artifacts()
    except FileNotFoundError:
        st.error(
            "No trained artifacts found. From the `aml/` folder, run:\n\n"
            "1. `python3 generate_data.py`\n"
            "2. `python3 train_model.py`\n\n"
            "Then restart this app."
        )
        return

    st.caption(
        "Rules decide WHAT gets flagged. This model decides WHAT ORDER an analyst should look at "
        "them in. Same rule engine, same alerts — just triaged smartest-first instead of "
        "first-in-first-out."
    )

    st.subheader("The pitch, in one chart")
    st.write(
        "Out of the same set of alerts, if an analyst can only review the top K today, "
        "how many real frauds do they actually catch?"
    )

    fig = go.Figure()
    fig.add_bar(name="Today (arrival order)", x=precision_at_k["K"], y=precision_at_k["fifo_frauds_caught"],
                marker_color="#94a3b8")
    fig.add_bar(name="Re-ranked by suspicion score", x=precision_at_k["K"],
                y=precision_at_k["reranked_frauds_caught"], marker_color="#0d9488")
    fig.update_layout(
        barmode="group", xaxis_title="Alerts reviewed (K)", yaxis_title="True frauds caught",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=380, margin=dict(t=10, b=10),
    )
    st.plotly_chart(fig, use_container_width=True, key="aml_precision_chart")

    total_fraud = int(scored["isFraud"].sum())
    st.caption(f"Test set: {len(scored):,} alerts already flagged by the rule engine, "
               f"{total_fraud} of them true fraud.")

    st.divider()
    st.subheader("Same alerts, two different queues")
    col1, col2 = st.columns(2)
    display_cols = ["step", "amount", "hour_of_day", "is_new_beneficiary", "drain_ratio", "isFraud"]

    with col1:
        st.markdown("**Today: first-in, first-out**")
        fifo_view = scored.sort_values("step").head(20)[display_cols].copy()
        fifo_view.insert(0, "queue_position", range(1, len(fifo_view) + 1))
        st.dataframe(
            fifo_view.style.apply(
                lambda row: ["background-color: #fee2e2" if row["isFraud"] == 1 else "" for _ in row], axis=1
            ),
            use_container_width=True, height=460,
        )

    with col2:
        st.markdown("**Re-ranked: highest suspicion score first**")
        reranked_view = scored.sort_values("suspicion_score", ascending=False).head(20)
        reranked_view = reranked_view[["suspicion_score"] + display_cols].copy()
        reranked_view.insert(0, "queue_position", range(1, len(reranked_view) + 1))
        st.dataframe(
            reranked_view.style.apply(
                lambda row: ["background-color: #d1fae5" if row["isFraud"] == 1 else "" for _ in row], axis=1
            ),
            use_container_width=True, height=460,
        )

    st.caption("Rows highlighted are confirmed fraud (ground truth, for demo purposes only — "
               "a real analyst wouldn't see this column).")

    st.divider()
    st.subheader("Why did this alert get this score?")
    st.write("Pick any alert from the re-ranked queue to see which signals drove its suspicion score.")

    reranked_all = scored.sort_values("suspicion_score", ascending=False).reset_index(drop=True)
    top_n = reranked_all.head(50).reset_index(drop=True)
    options = [
        f"#{i+1} — score {row.suspicion_score:.0f} — ₹{row.amount:,.0f} — "
        f"{'FRAUD' if row.isFraud == 1 else 'not fraud'}"
        for i, row in top_n.iterrows()
    ]
    choice = st.selectbox("Select an alert (top 50 of the re-ranked queue):", options, key="aml_alert_select")
    idx = options.index(choice)
    row = top_n.iloc[idx]

    shap_cols = [f"shap_{f}" for f in features]
    shap_row = row[shap_cols].rename(lambda c: c.replace("shap_", ""))
    shap_row = shap_row.reindex(shap_row.abs().sort_values(ascending=False).index)

    shap_fig = go.Figure(go.Bar(
        x=shap_row.values,
        y=[FEATURE_LABELS.get(f, f) for f in shap_row.index],
        orientation="h",
        marker_color=["#dc2626" if v > 0 else "#2563eb" for v in shap_row.values],
    ))
    shap_fig.update_layout(
        xaxis_title="Contribution to suspicion score (red = up, blue = down)",
        height=320, margin=dict(t=10, b=10, l=10, r=10),
    )
    st.plotly_chart(shap_fig, use_container_width=True, key="aml_shap_chart")

    top_driver = shap_row.abs().idxmax()
    st.info(
        f"**Score: {row.suspicion_score:.0f}/100.** Biggest driver: "
        f"**{FEATURE_LABELS.get(top_driver, top_driver)}** "
        f"({'pushed the score up' if shap_row[top_driver] > 0 else 'pushed the score down'})."
    )
