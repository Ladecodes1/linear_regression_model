from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "best_model.pkl"

FEATURES = ["country", "elev", "pl_m2", "hybrid", "N_kg_ha", "P_kg_ha", "season_prec"]

model = joblib.load(MODEL_PATH)

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
        "https://YOUR-SERVICE-NAME.onrender.com",
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


@app.post("/predict")
def predict(item: MaizeInput):
    prediction = predict_one_row(item.model_dump())
    return {"predicted_yield_kg_ha": round(prediction, 1)}
