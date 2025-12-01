import os
import pandas as pd
from sqlalchemy import create_engine, Table, Column, MetaData, Text, Numeric
from sqlalchemy.dialects.postgresql import insert, TIMESTAMP
from zoneinfo import ZoneInfo  # currently unused, but kept since it was in original

# ---- Connection (reads .env values) ----
PG_USER = os.getenv("POSTGRES_USER", "postgres")
PG_PW   = os.getenv("POSTGRES_PASSWORD", "postgres")
PG_DB   = os.getenv("POSTGRES_DB", "postgres")
PG_HOST = os.getenv("POSTGRES_HOST", "postgres")  # service name in compose
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))

engine = create_engine(
    f"postgresql+psycopg2://{PG_USER}:{PG_PW}@{PG_HOST}:{PG_PORT}/{PG_DB}"
)

DATA_DIR  = "/data"
DRONE_CSV = os.path.join(DATA_DIR, "CLEAN_COMBINED.csv")
ANEMO_CSV = os.path.join(DATA_DIR, "CLEAN_ANEMOMETER.csv")

# ---- SQLAlchemy table metadata (mirrors init.sql; just for inserts) ----
meta = MetaData()

drone_table = Table(
    "drone_measurements",
    meta,
    Column("drone_time_utc", TIMESTAMP(timezone=True), primary_key=True),
    Column("drone_serial", Text, primary_key=True),
    Column("drone_time_pst", TIMESTAMP(timezone=True)),
    Column("update_time_local_raw", Text),
    Column("wind_direction", Text),
    Column("wind_relative_direction", Text),
    Column("wind_speed_mph", Numeric),
    Column("max_wind_speed_mph", Numeric),
    Column("wind_strength", Text),
    Column("is_facing_wind", Text),
    Column("is_flying_into_wind", Text),
    Column("drone_direction_deg", Numeric),
    Column("wind_speed_mps", Numeric),
)

anemo_table = Table(
    "anemometer_measurements",
    meta,
    Column("ts_utc", TIMESTAMP(timezone=True), primary_key=True),
    Column("raw_ts", Text),
    Column("sn1", Numeric, primary_key=True),
    Column("u", Numeric),
    Column("v", Numeric),
    Column("temperature_c", Numeric),
    Column("battery_pct", Numeric),
    Column("batt_v", Numeric),
    Column("batt_c", Numeric),
    Column("vector_mag", Numeric),
    Column("vector_dir_deg", Numeric),
)

# ---- Helpers ----

def to_bool(x):
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    if s in {"true", "t", "1", "yes", "y"}:
        return True
    if s in {"false", "f", "0", "no", "n"}:
        return False
    return None  # will store as NULL

def to_num(x):
    try:
        if x == "" or x is None:
            return None
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
        "Drone_Time(UTC+RFC3339)",
        # "Drone_Time(PST)_Clean",
        "Drone_Direction",
        "WindSpeed(m/s)",
        "DETAILS.aircraftSerial",
    ]
    df = pd.read_csv(DRONE_CSV, usecols=usecols, low_memory=False)

    # Timestamps
    # 1) UTC RFC3339 with Z
    df["drone_time_utc"] = pd.to_datetime(
        df["Drone_Time(UTC+RFC3339)"], utc=True, errors="coerce"
    )

    # Serial
    df["drone_serial"] = df["DETAILS.aircraftSerial"]

    # Directions: import AS-IS (no trimming/casing/mapping)
    df["wind_direction"] = df["WEATHER.windDirection"]
    df["wind_relative_direction"] = df["WEATHER.windRelativeDirection"]

    # Other fields (keep wind_strength, booleans AS-IS)
    df["update_time_local_raw"] = df["CUSTOM.updateTime [local]"]
    df["wind_strength"] = df["WEATHER.windStrength"]
    df["is_facing_wind"] = df["WEATHER.isFacingWind"]
    df["is_flying_into_wind"] = df["WEATHER.isFlyingIntoWind"]

    # Numerics
    df["wind_speed_mph"] = pd.to_numeric(
        df["WEATHER.windSpeed [MPH]"], errors="coerce"
    )
    df["max_wind_speed_mph"] = pd.to_numeric(
        df["WEATHER.maxWindSpeed [MPH]"], errors="coerce"
    )
    df["drone_direction_deg"] = pd.to_numeric(
        df["Drone_Direction"], errors="coerce"
    )
    df["wind_speed_mps"] = pd.to_numeric(
        df["WindSpeed(m/s)"], errors="coerce"
    )

    # Drop rows missing PK components to avoid PK errors
    df = df.dropna(subset=["drone_time_utc", "drone_serial"])

    # Final selection in table order
    out = df[
        [
            "drone_time_utc",
            "drone_serial",
            # "drone_time_pst",  # not currently populated
            "update_time_local_raw",
            "wind_direction",          # raw, unchanged
            "wind_relative_direction", # raw, unchanged
            "wind_speed_mph",
            "max_wind_speed_mph",
            "wind_strength",           # raw
            "is_facing_wind",          # raw
            "is_flying_into_wind",     # raw
            "drone_direction_deg",
            "wind_speed_mps",
        ]
    ]

    rows = out.to_dict(orient="records")
    if not rows:
        print("[INFO] No drone rows to insert.")
        return

    # Insert with ON CONFLICT DO NOTHING on the PK (drone_time_utc, drone_serial)
    with engine.begin() as conn:
        stmt = insert(drone_table).on_conflict_do_nothing()
        conn.execute(stmt, rows)

    print(f"[INFO] Drone ingest: attempted {len(rows)} rows (duplicates skipped).")


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
        errors="coerce",
    )
    if ts_from_raw.dt.tz is None:
        ts_from_raw = ts_from_raw.dt.tz_localize("UTC")

    # Combine: prefer 'ts', then 'raw_ts'
    ts_utc = ts_from_ts.fillna(ts_from_raw)

    # Count issues before dropping
    total_rows = len(df)
    bad_ts = ts_utc.isna().sum()
    if bad_ts:
        print(
            f"[WARN] {bad_ts} / {total_rows} anemometer rows have no valid timestamp and will be skipped."
        )

    df["ts_utc"] = ts_utc

    # Drop rows with no timestamp to satisfy NOT NULL/PK
    df = df.dropna(subset=["ts_utc"])

    out = pd.DataFrame(
        {
            "ts_utc": df["ts_utc"],
            "raw_ts": df["raw_ts"].astype(str),
            "sn1": df["sn1"].apply(to_num),
            "u": df["U"].apply(to_num),
            "v": df["V"].apply(to_num),
            "temperature_c": df["T"].apply(to_num),
            "battery_pct": df["BatteryPct"].apply(to_num),
            "batt_v": df["BattV"].apply(to_num),
            "batt_c": df["BattC"].apply(to_num),
            "vector_mag": df["VectorMag"].apply(to_num),
            "vector_dir_deg": df["VectorDir"].apply(to_num),
        }
    )

    # sn1 is part of PK, so drop rows where it's missing
    out = out.dropna(subset=["ts_utc", "sn1"])

    rows = out.to_dict(orient="records")
    if not rows:
        print("[INFO] No anemometer rows to insert.")
        return

    # Insert with ON CONFLICT DO NOTHING on PK (ts_utc, sn1)
    with engine.begin() as conn:
        stmt = insert(anemo_table).on_conflict_do_nothing()
        conn.execute(stmt, rows)

    print(
        f"[INFO] Anemometer ingest: attempted {len(rows)} rows "
        f"(skipped {bad_ts} with bad timestamps; duplicates skipped)."
    )


if __name__ == "__main__":
    if not os.path.exists(DRONE_CSV):
        raise SystemExit(f"Missing {DRONE_CSV}")
    if not os.path.exists(ANEMO_CSV):
        raise SystemExit(f"Missing {ANEMO_CSV}")

    ingest_drone()
    ingest_anemometer()
    print("Done.")
