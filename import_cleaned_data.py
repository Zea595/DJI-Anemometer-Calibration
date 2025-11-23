import os
import pandas as pd
from sqlalchemy import create_engine
from zoneinfo import ZoneInfo

# ---- Connection (reads .env values) ----
PG_USER = os.getenv("POSTGRES_USER", "postgres")
PG_PW   = os.getenv("POSTGRES_PASSWORD", "postgres")
PG_DB   = os.getenv("POSTGRES_DB", "postgres")
PG_HOST = os.getenv("POSTGRES_HOST", "postgres")  # service name in compose
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))

engine = create_engine(f"postgresql+psycopg2://{PG_USER}:{PG_PW}@{PG_HOST}:{PG_PORT}/{PG_DB}")

DATA_DIR = "/data"
DRONE_CSV = os.path.join(DATA_DIR, "CLEAN_COMBINED.csv")
ANEMO_CSV = os.path.join(DATA_DIR, "CLEAN_ANEMOMETER.csv")

# ---- Helpers ----
DIR_MAP = {
    "N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,"SSE":157.5,
    "S":180,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,"WNW":292.5,"NW":315,"NNW":337.5
}

def to_bool(x):
    if isinstance(x, bool): return x
    s = str(x).strip().lower()
    if s in {"true","t","1","yes","y"}: return True
    if s in {"false","f","0","no","n"}: return False
    return None  # will store as NULL

def to_num(x):
    try:
        if x == "" or x is None: return None
        return float(x)
    except Exception:
        return None

# =========================
# Ingest DRONE CSV
# =========================
def ingest_drone():
    # Read exactly these columns (robust if the file grows extra columns later)
    usecols = [
        "CUSTOM.updateTime [local]",
        "WEATHER.windDirection",
        "WEATHER.windRelativeDirection",
        "WEATHER.windSpeed [MPH]",
        "WEATHER.maxWindSpeed [MPH]",
        "WEATHER.windStrength",
        "WEATHER.isFacingWind",
        "WEATHER.isFlyingIntoWind",
        "Drone_Time(PST)",
        "Drone_Time(UTC+RFC3339)",
        "Drone_Direction",
    ]
    df = pd.read_csv(DRONE_CSV, usecols=usecols, low_memory=False)

    # Timestamps
    # 1) UTC RFC3339 with Z
    df["drone_time_utc"] = pd.to_datetime(
        df["Drone_Time(UTC+RFC3339)"], utc=True, errors="coerce"
    )

    # 2) Local PST (AM/PM with fractional seconds) -> localize then convert to UTC
    pst = pd.to_datetime(df["Drone_Time(PST)"], errors="coerce")
    pst_aware = pst.dt.tz_localize("America/Vancouver", nonexistent="NaT", ambiguous="NaT")
    df["drone_time_pst"] = pst_aware.dt.tz_convert("UTC")

    # Directions: import AS-IS (no trimming/casing/mapping)
    df["wind_direction"] = df["WEATHER.windDirection"]
    df["wind_relative_direction"] = df["WEATHER.windRelativeDirection"]

    # Other fields (keep wind_strength, booleans AS-IS)
    df["update_time_local_raw"] = df["CUSTOM.updateTime [local]"]
    df["wind_strength"] = df["WEATHER.windStrength"]
    df["is_facing_wind"] = df["WEATHER.isFacingWind"]
    df["is_flying_into_wind"] = df["WEATHER.isFlyingIntoWind"]

    # Numerics
    df["wind_speed_mph"] = pd.to_numeric(df["WEATHER.windSpeed [MPH]"], errors="coerce")
    df["max_wind_speed_mph"] = pd.to_numeric(df["WEATHER.maxWindSpeed [MPH]"], errors="coerce")
    df["drone_direction_deg"] = pd.to_numeric(df["Drone_Direction"], errors="coerce")

    # Final selection in table order
    out = df[[
        "drone_time_utc",
        "drone_time_pst",
        "update_time_local_raw",
        "wind_direction",              # raw, unchanged
        "wind_relative_direction",     # raw, unchanged
        "wind_speed_mph",
        "max_wind_speed_mph",
        "wind_strength",               # raw
        "is_facing_wind",              # raw
        "is_flying_into_wind",         # raw
        "drone_direction_deg",
    ]]

    # Insert
    out.to_sql("drone_measurements", engine, if_exists="append", index=False)

    # Quick visibility to confirm non-null counts
    print(
        "Inserted rows:",
        len(out),
        "| non-null wind_direction:",
        out["wind_direction"].notna().sum(),
        "| non-null wind_relative_direction:",
        out["wind_relative_direction"].notna().sum(),
        "| non-null wind_speed_mph:",
        out["wind_speed_mph"].notna().sum(),
    )




# =========================
# Ingest ANEMOMETER CSV
# =========================
def ingest_anemometer():
    df = pd.read_csv(ANEMO_CSV, low_memory=False)

    # 1) Primary parse from 'ts' (RFC3339 Z)
    ts_from_ts = pd.to_datetime(df.get("ts"), utc=True, errors="coerce")

    # 2) Fallback: parse 'raw_ts' like "23:11:01:17:39:22.316" = %y:%m:%d:%H:%M:%S.%f
    #    Treat as UTC (sensor logs are typically UTC; adjust if you know otherwise).
    ts_from_raw = pd.to_datetime(
        df.get("raw_ts"),
        format="%y:%m:%d:%H:%M:%S.%f",
        errors="coerce"
    )
    if ts_from_raw.dt.tz is None:
        ts_from_raw = ts_from_raw.dt.tz_localize("UTC")

    # Combine: prefer 'ts', then 'raw_ts'
    ts_utc = ts_from_ts.fillna(ts_from_raw)

    # Count issues before dropping
    total_rows = len(df)
    bad_ts = ts_utc.isna().sum()
    if bad_ts:
        print(f"[WARN] {bad_ts} / {total_rows} anemometer rows have no valid timestamp and will be skipped.")

    df["ts_utc"] = ts_utc

    # Drop rows with no timestamp to satisfy NOT NULL
    df = df.dropna(subset=["ts_utc"])

    out = pd.DataFrame({
        "ts_utc"        : df["ts_utc"],
        "raw_ts"        : df["raw_ts"].astype(str),
        "u"             : df["U"].apply(to_num),
        "v"             : df["V"].apply(to_num),
        "temperature_c" : df["T"].apply(to_num),
        "battery_pct"   : df["BatteryPct"].apply(to_num),
        "batt_v"        : df["BattV"].apply(to_num),
        "batt_c"        : df["BattC"].apply(to_num),
        "vector_mag"    : df["VectorMag"].apply(to_num),
        "vector_dir_deg": df["VectorDir"].apply(to_num),
    })

    out.to_sql("anemometer_measurements", engine, if_exists="append", index=False)
    print(f"Inserted {len(out)} anemometer rows (skipped {bad_ts}).")


if __name__ == "__main__":
    if not os.path.exists(DRONE_CSV):
        raise SystemExit(f"Missing {DRONE_CSV}")
    if not os.path.exists(ANEMO_CSV):
        raise SystemExit(f"Missing {ANEMO_CSV}")

    ingest_drone()
    ingest_anemometer()
    print("Done.")
