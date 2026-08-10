"""
train_model.py

Trains the re-ranking model and produces everything the Streamlit app needs:
  - a trained XGBoost model (model.joblib)
  - the scored test-set alert queue, in both FIFO and re-ranked order
  - the Precision@K comparison numbers (the core demo chart)
  - SHAP values for every test-set alert (per-alert explainability)

Run this after generate_data.py. Everything is saved to artifacts/.
"""

import os
import joblib
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.metrics import average_precision_score

DATA_PATH = "data/transactions.csv"
ARTIFACTS_DIR = "artifacts"
FEATURES = [
    "amount",
    "amount_vs_sender_avg",     # is this unusual FOR THIS account?
    "drain_ratio",               # % of balance being sent out
    "velocity_24h",               # transaction velocity spike
    "is_new_beneficiary",
    "hour_of_day",
    "account_age_steps",         # new account = higher risk
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    sender_avg = df.groupby("nameOrig")["amount"].transform("mean")
    df["amount_vs_sender_avg"] = df["amount"] / sender_avg.replace(0, np.nan)
    df["amount_vs_sender_avg"] = df["amount_vs_sender_avg"].fillna(1.0)
    df["drain_ratio"] = df["amount"] / df["oldbalanceOrg"].replace(0, np.nan)
    df["drain_ratio"] = df["drain_ratio"].clip(0, 2).fillna(0)
    df["account_age_steps"] = (df["step"] - df["account_open_step_orig"]).clip(lower=0)
    return df


def precision_at_k(df_sorted: pd.DataFrame, k_values):
    out = {}
    for k in k_values:
        top_k = df_sorted.head(k)
        out[k] = int(top_k["isFraud"].sum())
    return out


def main():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    df = pd.read_csv(DATA_PATH)
    df = build_features(df)

    # Only rows the rule engine already flagged are the "alert queue" analysts
    # actually deal with -- the re-ranker sits downstream of the rule engine,
    # it doesn't replace it.
    alerts = df[df["rule_flagged"] == 1].reset_index(drop=True)

    # Time-based split: train on the earlier 70% of steps, test on the later
    # 30%. This avoids "seeing the future," which is the #1 way fraud-model
    # demos accidentally cheat.
    cutoff = alerts["step"].quantile(0.70)
    train = alerts[alerts["step"] <= cutoff].reset_index(drop=True)
    test = alerts[alerts["step"] > cutoff].reset_index(drop=True)

    X_train, y_train = train[FEATURES], train["isFraud"]
    X_test, y_test = test[FEATURES], test["isFraud"]

    pos = max(y_train.sum(), 1)
    neg = len(y_train) - pos
    scale_pos_weight = neg / pos  # tells XGBoost to care much more about the rare fraud rows

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.08,
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr",
        random_state=42,
    )
    model.fit(X_train, y_train)

    test = test.copy()
    test["suspicion_score"] = (model.predict_proba(X_test)[:, 1] * 100).round(1)

    ap = average_precision_score(y_test, test["suspicion_score"])
    print(f"Test set: {len(test)} alerts, {y_test.sum()} true frauds, "
          f"average precision = {ap:.3f}")

    # --- Precision@K: the headline comparison chart ---
    fifo_order = test.sort_values("step")                       # today's system
    reranked_order = test.sort_values("suspicion_score", ascending=False)  # the pitch

    k_values = [5, 10, 20, 50]
    fifo_hits = precision_at_k(fifo_order, k_values)
    reranked_hits = precision_at_k(reranked_order, k_values)

    comparison = pd.DataFrame({
        "K": k_values,
        "fifo_frauds_caught": [fifo_hits[k] for k in k_values],
        "reranked_frauds_caught": [reranked_hits[k] for k in k_values],
    })
    comparison.to_csv(f"{ARTIFACTS_DIR}/precision_at_k.csv", index=False)
    print(comparison.to_string(index=False))

    # --- SHAP values for every test alert, so the app can explain any one of them ---
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)
    shap_df = pd.DataFrame(shap_values, columns=[f"shap_{c}" for c in FEATURES])
    test = pd.concat([test.reset_index(drop=True), shap_df.reset_index(drop=True)], axis=1)

    test.to_csv(f"{ARTIFACTS_DIR}/scored_alerts.csv", index=False)
    joblib.dump(model, f"{ARTIFACTS_DIR}/model.joblib")
    joblib.dump(FEATURES, f"{ARTIFACTS_DIR}/features.joblib")

    print(f"\nSaved model + scored alerts + SHAP values to {ARTIFACTS_DIR}/")


if __name__ == "__main__":
    main()
