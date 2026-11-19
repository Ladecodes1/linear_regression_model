from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
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


def load_model():
    # Use a retrained model if one was saved, otherwise the model from the repository.
    path = RETRAINED_PATH if RETRAINED_PATH.exists() else MODEL_PATH
    return joblib.load(path)


model = load_model()

app = FastAPI(
    title="Maize Yield Prediction API",
    description="Predicts maize yield (kg per hectare) for smallholder farms.",
)

# CORS: only the websites listed here may call this API from a browser.
# Allowed: my local test pages and my deployed Render URL (update it after deployment).
# Restricted: every other website (no "*"), only GET and POST methods, only the
# Content-Type and Accept headers, and no cookies or login credentials.
# Why: the API needs no login and only reads and posts data, so extra permissions
# would only widen what a malicious website could do.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5000",
        "https://maize-yield-api-93ln.onrender.com",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
    allow_credentials=False,
)


class MaizeInput(BaseModel):
    country: Literal["kenya", "tanzania", "rwanda", "burundi", "zambia", "uganda", "nigeria"]
    elev: float = Field(ge=0, le=3000, description="Elevation in metres")
    pl_m2: float = Field(ge=0, le=15, description="Plants per square metre")
    hybrid: int = Field(ge=0, le=1, description="1 = hybrid seed, 0 = other seed")
    N_kg_ha: float = Field(ge=0, le=350, description="Nitrogen applied (kg per hectare)")
    P_kg_ha: float = Field(ge=0, le=120, description="Phosphorus applied (kg per hectare)")
    season_prec: float = Field(ge=200, le=2500, description="Season rainfall (mm)")


def predict_one_row(row: dict) -> float:
    frame = pd.DataFrame([row], columns=FEATURES)
    return float(model.predict(frame)[0])


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


@app.post("/predict")
def predict(item: MaizeInput):
    prediction = predict_one_row(item.model_dump())
    return {"predicted_yield_kg_ha": round(prediction, 1)}


@app.post("/retrain")
def retrain(file: UploadFile = File(...)):
    global model

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")
    try:
        uploaded = pd.read_csv(file.file)
    except Exception:
        raise HTTPException(status_code=400, detail="The file could not be read as a CSV.")

    missing = [c for c in REQUIRED_COLUMNS if c not in uploaded.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"The CSV is missing these columns: {missing}")

    new_rows = clean_data(uploaded)
    if len(new_rows) == 0:
        raise HTTPException(status_code=400, detail="No valid rows found in the uploaded CSV.")

    original = clean_data(pd.read_csv(TRAINING_DATA_PATH))
    combined = pd.concat([original, new_rows], ignore_index=True)

    new_model = build_pipeline()
    new_model.fit(combined[FEATURES], combined["yield_kg_ha"])

    joblib.dump(new_model, RETRAINED_PATH, compress=3)
    model = new_model  # /predict now uses the updated model, no redeploy needed

    return {
        "message": "Model retrained and now in use.",
        "rows_uploaded": len(uploaded),
        "valid_new_rows_used": len(new_rows),
        "total_rows_trained_on": len(combined),
    }
