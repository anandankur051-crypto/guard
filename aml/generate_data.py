"""
generate_data.py

Creates a synthetic mobile-money transaction dataset that mimics the structure
of the public PaySim fraud dataset (Kaggle: "Synthetic Financial Datasets For
Fraud Detection"). This lets the whole prototype run end-to-end with zero
external downloads.

Swap-in note: if you want to use REAL PaySim data instead, download
"PS_20174392719_1491204439457_log.csv" from Kaggle and rename it to
data/transactions.csv with the same column names used below
(step, amount, nameOrig, oldbalanceOrg, newbalanceOrig, nameDest,
oldbalanceDest, newbalanceDest, isFraud). train_model.py will work unchanged.
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

N_ACCOUNTS = 2000
N_STEPS = 720          # "step" = 1 hour, so 720 steps = 30 days
N_NORMAL_TXNS = 40000
N_FRAUD_TXNS = 350      # keeps fraud at < 1% of alerts, like real AML data

RULE_AMOUNT_THRESHOLD = 1_000_000  # ₹10 lakh, the classic static rule


def make_accounts(n):
    ids = [f"C{100000 + i}" for i in range(n)]
    # each account has its own "normal" transaction size (this is what lets
    # the model later ask "is this unusual FOR THIS account", not just
    # unusual in absolute terms)
    mean_amt = RNG.lognormal(mean=9.5, sigma=1.0, size=n)  # ~ tens of thousands
    balances = RNG.lognormal(mean=11.5, sigma=1.2, size=n)  # starting balance
    account_open_step = RNG.integers(-500, N_STEPS, size=n)  # some pre-exist, some open during window
    return pd.DataFrame({
        "nameOrig": ids,
        "typical_amount": mean_amt,
        "balance": balances,
        "account_open_step": account_open_step,
    })


def generate_normal_transactions(accounts):
    rows = []
    sender_idx = RNG.integers(0, len(accounts), size=N_NORMAL_TXNS)
    dest_idx = RNG.integers(0, len(accounts), size=N_NORMAL_TXNS)
    steps = RNG.integers(0, N_STEPS, size=N_NORMAL_TXNS)

    for i in range(N_NORMAL_TXNS):
        s = accounts.iloc[sender_idx[i]]
        d = accounts.iloc[dest_idx[i]]
        amount = max(100, RNG.normal(s["typical_amount"], s["typical_amount"] * 0.3))
        old_bal_orig = max(amount * 1.2, s["balance"])
        new_bal_orig = old_bal_orig - amount
        old_bal_dest = d["balance"]
        new_bal_dest = old_bal_dest + amount
        hour = steps[i] % 24
        rows.append({
            "step": steps[i],
            "type": "TRANSFER",
            "amount": round(amount, 2),
            "nameOrig": s["nameOrig"],
            "oldbalanceOrg": round(old_bal_orig, 2),
            "newbalanceOrig": round(new_bal_orig, 2),
            "nameDest": d["nameOrig"],
            "oldbalanceDest": round(old_bal_dest, 2),
            "newbalanceDest": round(new_bal_dest, 2),
            "hour_of_day": hour,
            "account_open_step_orig": s["account_open_step"],
            "isFraud": 0,
        })
    return rows


def generate_hard_negative_transactions(accounts, n=600):
    """Legitimate transactions that superficially resemble fraud (large,
    high drain ratio, sometimes a new beneficiary) -- e.g. someone closing
    an account or paying off a large loan. Without these, the model could
    cheat by learning 'high drain ratio == fraud', which real rule-evading
    fraud won't always show and real legitimate transfers sometimes will."""
    rows = []
    sender_idx = RNG.integers(0, len(accounts), size=n)
    dest_idx = RNG.integers(0, len(accounts), size=n)
    steps = RNG.integers(0, N_STEPS, size=n)

    for i in range(n):
        s = accounts.iloc[sender_idx[i]]
        d = accounts.iloc[dest_idx[i]]
        drain_ratio = RNG.uniform(0.6, 0.95)
        amount = max(s["balance"] * drain_ratio, RULE_AMOUNT_THRESHOLD * RNG.uniform(0.8, 1.5))
        old_bal_orig = s["balance"]
        new_bal_orig = max(0, old_bal_orig - amount)
        old_bal_dest = d["balance"]
        new_bal_dest = old_bal_dest + amount
        hour = int(RNG.integers(8, 20))  # business hours, unlike fraud's odd hours
        rows.append({
            "step": steps[i],
            "type": "TRANSFER",
            "amount": round(amount, 2),
            "nameOrig": s["nameOrig"],
            "oldbalanceOrg": round(old_bal_orig, 2),
            "newbalanceOrig": round(new_bal_orig, 2),
            "nameDest": d["nameOrig"],
            "oldbalanceDest": round(old_bal_dest, 2),
            "newbalanceDest": round(new_bal_dest, 2),
            "hour_of_day": hour,
            "account_open_step_orig": s["account_open_step"],
            "isFraud": 0,
        })
        # ~30% of the time, a legit sender also has a burst of quick small
        # transactions beforehand (e.g. a small business paying several
        # suppliers) -- so velocity alone can't be a giveaway either
        if RNG.random() < 0.3:
            for _ in range(RNG.integers(2, 5)):
                pre_amt = round(RNG.uniform(500, 5000), 2)
                rows.append({
                    "step": max(0, steps[i] - RNG.integers(1, 3)),
                    "type": "TRANSFER",
                    "amount": pre_amt,
                    "nameOrig": s["nameOrig"],
                    "oldbalanceOrg": round(old_bal_orig, 2),
                    "newbalanceOrig": round(old_bal_orig - pre_amt, 2),
                    "nameDest": f"C{100000 + int(RNG.integers(0, N_ACCOUNTS))}",
                    "oldbalanceDest": 0.0,
                    "newbalanceDest": pre_amt,
                    "hour_of_day": hour,
                    "account_open_step_orig": s["account_open_step"],
                    "isFraud": 0,
                })
    return rows


def generate_fraud_transactions(accounts):
    """Injects the exact patterns described in the pitch: near-total account
    drain, brand-new beneficiary, odd hour, amount spike vs. own history,
    velocity spike (multiple quick transactions right before the big one)."""
    rows = []
    sender_idx = RNG.integers(0, len(accounts), size=N_FRAUD_TXNS)
    steps = RNG.integers(0, N_STEPS, size=N_FRAUD_TXNS)

    for i in range(N_FRAUD_TXNS):
        s = accounts.iloc[sender_idx[i]]
        # widen the range and add noise so fraud isn't perfectly separable --
        # some fraud looks only mildly suspicious, mimicking real data
        drain_ratio = RNG.uniform(0.45, 1.0)
        amount = max(s["balance"] * drain_ratio, RULE_AMOUNT_THRESHOLD * RNG.uniform(0.85, 2.2))
        amount *= RNG.uniform(0.9, 1.1)  # measurement-style noise
        old_bal_orig = s["balance"]
        new_bal_orig = max(0, old_bal_orig - amount)
        # most fraud goes to a brand-new mule account, but some reuses an
        # account the sender has paid before (harder case, no easy tell)
        if RNG.random() < 0.75:
            dest_id = f"MULE{RNG.integers(0, 999999)}"
            old_bal_dest = 0.0
        else:
            dest_id = f"C{100000 + int(RNG.integers(0, N_ACCOUNTS))}"
            old_bal_dest = RNG.lognormal(mean=10, sigma=1.0)
        new_bal_dest = old_bal_dest + amount
        # odd hour is common but not universal -- some fraud happens in daylight
        odd_hour = int(RNG.choice([1, 2, 3, 4, 23, 14, 10, 16],
                                   p=[0.15, 0.15, 0.15, 0.15, 0.15, 0.0834, 0.0833, 0.0833]))

        # velocity spike: a few small "testing" transactions right before --
        # only about 55% of fraud cases show this, the rest look quieter
        n_precursor = RNG.integers(2, 6) if RNG.random() < 0.55 else 0
        for _ in range(n_precursor):
            pre_amt = round(RNG.uniform(500, 5000), 2)
            rows.append({
                "step": max(0, steps[i] - RNG.integers(1, 3)),
                "type": "TRANSFER",
                "amount": pre_amt,
                "nameOrig": s["nameOrig"],
                "oldbalanceOrg": round(old_bal_orig, 2),
                "newbalanceOrig": round(old_bal_orig - pre_amt, 2),
                "nameDest": dest_id,
                "oldbalanceDest": 0.0,
                "newbalanceDest": pre_amt,
                "hour_of_day": odd_hour,
                "account_open_step_orig": s["account_open_step"],
                "isFraud": 0,   # precursor pings aren't the flagged txn itself
            })

        rows.append({
            "step": steps[i],
            "type": "TRANSFER",
            "amount": round(amount, 2),
            "nameOrig": s["nameOrig"],
            "oldbalanceOrg": round(old_bal_orig, 2),
            "newbalanceOrig": round(new_bal_orig, 2),
            "nameDest": dest_id,
            "oldbalanceDest": round(old_bal_dest, 2),
            "newbalanceDest": round(new_bal_dest, 2),
            "hour_of_day": odd_hour,
            "account_open_step_orig": s["account_open_step"],
            "isFraud": 1,
        })
    return rows


def main():
    accounts = make_accounts(N_ACCOUNTS)
    rows = (
        generate_normal_transactions(accounts)
        + generate_hard_negative_transactions(accounts)
        + generate_fraud_transactions(accounts)
    )
    df = pd.DataFrame(rows).sort_values("step").reset_index(drop=True)

    # velocity feature: count of this sender's transactions in the prior 24 steps
    df = df.sort_values(["nameOrig", "step"])
    df["velocity_24h"] = (
        df.groupby("nameOrig")["step"]
        .transform(lambda s: s.apply(lambda t: ((s >= t - 24) & (s < t)).sum()))
    )
    df = df.sort_values("step").reset_index(drop=True)

    # is this beneficiary new to this sender? (first time this pair appears)
    df["pair"] = df["nameOrig"] + "->" + df["nameDest"]
    first_seen = df.groupby("pair")["step"].transform("min")
    df["is_new_beneficiary"] = (df["step"] == first_seen).astype(int)
    df = df.drop(columns=["pair"])

    # the static rule engine banks use today: flag if amount crosses threshold
    # OR if it's a new beneficiary within 24 steps of account opening
    df["rule_flagged"] = (
        (df["amount"] > RULE_AMOUNT_THRESHOLD)
        | ((df["is_new_beneficiary"] == 1) & (df["step"] - df["account_open_step_orig"] <= 24))
    ).astype(int)

    import os
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/transactions.csv", index=False)
    print(f"Generated {len(df)} transactions, {df['isFraud'].sum()} fraudulent, "
          f"{df['rule_flagged'].sum()} rule-flagged alerts "
          f"({df.query('rule_flagged==1')['isFraud'].sum()} of those alerts are true fraud).")


if __name__ == "__main__":
    main()
