import os
import pandas as pd
from sqlalchemy import create_engine

# -------------------------------------------------
# 1. Load PostgreSQL credentials from environment
# -------------------------------------------------
user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
db = os.getenv("POSTGRES_DB")
host = os.getenv("POSTGRES_HOST")
port = os.getenv("POSTGRES_PORT")

# Create database connection
engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")

# -------------------------------------------------
# 2. Load cleaned CSV from mounted volume
# -------------------------------------------------
csv_path = "/data/cleaned_flight.csv"

print(f"📥 Loading {csv_path}...")
df = pd.read_csv(csv_path, low_memory=False)
print(f"✅ {len(df)} rows, {len(df.columns)} columns loaded.")

# -------------------------------------------------
# 3. Keep and rename only relevant columns
# -------------------------------------------------
cols_to_keep = [
    "TimeStamp",
    "WEATHER.windDirection",
    "WEATHER.windSpeed [MPH]",
    "WEATHER.maxWindSpeed [MPH]",
    "WEATHER.windStrength"
]

# Keep only columns that exist in CSV
df = df[[c for c in cols_to_keep if c in df.columns]].copy()

# Rename to match database schema
df.rename(columns={
    "TimeStamp": "timestamp",
    "WEATHER.windDirection": "wind_dir",
    "WEATHER.windSpeed [MPH]": "wind_speed",
    "WEATHER.maxWindSpeed [MPH]": "gust_strength",
    "WEATHER.windStrength": "turbulence"
}, inplace=True)

# -------------------------------------------------
# 4. Clean and convert values
# -------------------------------------------------

# Map text turbulence levels → numeric scale
turbulence_map = {
    "Calm": 0,
    "Light": 1,
    "Moderate": 2,
    "Strong": 3,
    "Very Strong": 4
}
df["turbulence"] = df["turbulence"].map(turbulence_map).fillna(0).astype(float)

# Convert text wind direction (N, NE, etc.) → numeric degrees
dir_map = {
    "N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5,
    "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
    "S": 180, "SSW": 202.5, "SW": 225, "WSW": 247.5,
    "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5
}
df["wind_dir"] = df["wind_dir"].map(dir_map).fillna(0).astype(float)

# Convert numeric fields safely
for col in ["wind_speed", "gust_strength"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

print("✅ Cleaned and converted column types:")
print(df.dtypes)

# -------------------------------------------------
# 5. Insert into PostgreSQL
# -------------------------------------------------
print("📤 Importing data into PostgreSQL...")
df.to_sql("wind_measurements", engine, if_exists="append", index=False)
print("🎯 Data import complete.")
