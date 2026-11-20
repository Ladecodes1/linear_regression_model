from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "best_model.pkl"
RETRAINED_PATH = BASE_DIR / "retrained_model.pkl"
TRAINING_DATA_PATH = BASE_DIR / "training_data.csv"

COUNTRIES = ["kenya", "tanzania", "rwanda", "burundi", "zambia", "uganda", "nigeria"]
FEATURES = ["country", "elev", "pl_m2", "hybrid", "N_kg_ha", "P_kg_ha", "season_prec"]
NUMERIC_FEATURES = ["elev", "pl_m2", "hybrid", "N_kg_ha", "P_kg_ha", "season_prec"]
REQUIRED_COLUMNS = FEATURES + ["yield_kg_ha"]


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df[REQUIRED_COLUMNS].copy()
    df["hybrid"] = (
        df["hybrid"].astype(str).str.lower()
        .map({"true": 1, "false": 0, "1": 1, "0": 0, "1.0": 1, "0.0": 0})
    )
    for col in NUMERIC_FEATURES + ["yield_kg_ha"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["country"] = df["country"].astype(str).str.lower().str.strip()
    keep = df["country"].isin(COUNTRIES) & df["yield_kg_ha"].notna() & (df["yield_kg_ha"] >= 0)
    return df[keep].reset_index(drop=True)


def build_pipeline() -> Pipeline:
    preprocess = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["country"]),
    ])
    return Pipeline([
        ("prep", preprocess),
        ("model", RandomForestRegressor(n_estimators=200, min_samples_leaf=3, random_state=42, n_jobs=-1)),
    ])


def retrain_model(uploaded: pd.DataFrame):
    """Add the uploaded rows to the training data, retrain, save, and return (model, stats)."""
    missing = [c for c in REQUIRED_COLUMNS if c not in uploaded.columns]
    if missing:
        raise ValueError(f"The CSV is missing these columns: {missing}")

    new_rows = clean_data(uploaded)
    if len(new_rows) == 0:
        raise ValueError("No valid rows found in the uploaded CSV.")

    original = clean_data(pd.read_csv(TRAINING_DATA_PATH))
    combined = pd.concat([original, new_rows], ignore_index=True)

    new_model = build_pipeline()
    new_model.fit(combined[FEATURES], combined["yield_kg_ha"])
    joblib.dump(new_model, RETRAINED_PATH, compress=3)

    stats = {
        "rows_uploaded": len(uploaded),
        "valid_new_rows_used": len(new_rows),
        "total_rows_trained_on": len(combined),
    }
    return new_model, stats
