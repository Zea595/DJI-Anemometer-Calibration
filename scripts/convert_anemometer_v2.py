"""
convert_anemometer_simple_v2.py

Goal (v2 changes):
------------------
- Discard SN items entirely (We won't need SN1/SN2 at all).
- Raw timestamp is ALREADY in UTC and only format it to RFC3339.
  No timezone conversion is performed.

Input line example:
    23:11:01:17:39:22.316 SN150 SN151 U -00.90 V -00.21 T  19.78 Battery% 100 BATTV  4.16 BATTC  0.000

What we do:
-----------
1) Read each line.
2) Parse the first item as a timestamp:
   - Format is assumed to be: YY:MM:DD:HH:MM:SS.mmm  (e.g., 23:11:01:17:39:22.316)
   - We interpret YY as 2000+YY (e.g., "23" -> year 2023).
   - We assume the timezone (default America/Vancouver) and then convert to UTC.
   - We output RFC3339 formated timestamp like: 2023-11-02T00:39:22.316Z
3) Extract key/value pairs: 
    U (Zonal wind speed component == x-axis) , 
    V (Meridional wind speed component == y-axis), 
    T (Temperature), 
    Battery%, BATTV, BATTC
4) Output CSV columns (v2)

Usage:
------
python3 convert_anemometer_v2.py INPUT.txt OUTPUT.csv

Columns written:
----------------
raw_ts, ts, U, V, T, BatteryPct, BattV, BattC
"""

import argparse
import csv
from datetime import datetime, timezone
from zoneinfo import ZoneInfo  # kept for consistency of format, not used for tz conversion
import sys, pathlib
import math
import os
from pathlib import Path
import numpy as np

def get_wind_speed(u, v):
    """
    Calculates the magnitude of the wind vector.
    Uses math.hypot(u, v) which is equivalent to sqrt(u*u + v*v)
    """
    return math.hypot(u, v)

def get_wind_direction(u, v):
    """
    Calculates the wind direction in degrees (0-360).
    0 = North, 90 = East, 180 = South, 270 = West.
    Returns the direction the wind is COMING FROM.
    """
    # # Calculate the angle in radians using atan2(y, x)
    # angle_radians = math.atan2(v, u)
    # # Convert to degrees
    # angle_degrees = math.degrees(angle_radians)
    # # 3. Convert from "Math Angle" (0 is East, Counter-Clockwise) 
    # # to "Meteorological Angle" (0 is North, Clockwise)
    # wind_direction = (270 - angle_degrees) % 360
    return (270-math.atan2(v,u)*180/math.pi) % 360

def get_cardinal_point(degree):
    """
    Converts degrees (0-360) to a cardinal point string.
    Handles 16-point compass (N, NNE, NE, etc.)
    """
    directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]
    # There are 360 degrees and 16 directions. 
    # Each direction covers a sector of 360 / 16 = 22.5 degrees.
    # We shift by half a sector (11.25) so that "N" centers on 0/360.
    index = int((degree + 11.25) / 22.5)
    return directions[index % 16]

def parse_line(line, assume_tz_name, keep_sn=True):
    """
    Parse one log line.
    Returns a dict with column names and values, or None if the line is empty/invalid.

    We look for items in this order:
      - First item: timestamp (required)
      - Then key/value pairs: U, V, T, Battery%, BATTV, BATTC
    v2 change: SN items are ignored entirely.
    """
    # Clean and split the line
    line = line.strip()
    if not line:
        return None

    parts = line.split()
    if not parts:
        return None

    # 1) Timestamp (first item)
    raw_ts = parts[0]
    ts = parse_timestamp(raw_ts, assume_tz_name)  # assume_tz_name is not used inside; kept for format consistency

    # Prepare the output row with defaults set to empty strings (Template for one row of the CSV)
    row = {
        "raw_ts": raw_ts,
        "ts": ts if ts is not None else "",
        "U": "",
        "V": "",
        "T": "",
        "BatteryPct": "",
        "BattV": "",
        "BattC": "",
        "VectorMag": "",
        "VectorDir": "",
        "cardinal_dir": "",
    }

    # 2) Key/value pairs for the rest of the items
    #    We accept only known keys; anything else is ignored.
    known_keys = {
        "U": "U", 
        "V": "V", 
        "T": "T", 
        "Battery%": "BatteryPct", 
        "BATTV": "BattV", 
        "BATTC": "BattC"
        }
    current_key = None

    index = 1
    while index < len(parts):
        item = parts[index]

        if item in known_keys:
            current_key = known_keys[item]
            index += 1
            continue

       # If we have a current key, try to read this item as the corresponding value
        if current_key is not None:
            # Try to convert to float where it makes sense; if it fails, leave as empty
            try:
                # BatteryPct can be int-like; float covers both
                value = float(item)
            except ValueError:
                value = ""  # could not parse; leave empty

            row[current_key] = value
            current_key = None
            index += 1
            continue

        # If item is neither a key nor a value, we skip it
        index += 1

    # Derived wind metrics
    try:
        u_value = float(row["U"])
        v_value = float(row["V"])

        vector_mag = get_wind_speed(u_value, v_value)       # magnitude
        vector_dir = get_wind_direction(u_value, v_value)   # degrees (coming from)
        cardinal_dir = get_cardinal_point(vector_dir)       # N, NNE, NE, etc.

        row["VectorMag"] = round(vector_mag, 3)
        row["VectorDir"] = round(vector_dir, 2)
        row["cardinal_dir"] = cardinal_dir

    except Exception:
        # U or V were missing or invalid → leave derived fields blank
        pass

    return row

def parse_timestamp(raw_ts, assume_tz_name_unused):
    """
    Convert '23:11:01:17:39:22.316' (YY:MM:DD:HH:MM:SS.mmm) to RFC3339 UTC string.
    IMPORTANT (v2): raw_ts is already in UTC. We DO NOT convert timezones.
    
    Returns: RFC3339 'YYYY-MM-DDTHH:MM:SS(.mmm)Z' or None if parsing fails.
    """
    try:
        # Split by ":"
        parts = raw_ts.split(":")
        # Expected 6 parts: [YY, MM, DD, HH, MM, SS.mmm]
        if len(parts) != 6:
            return None

        yy = int(parts[0])
        MM = int(parts[1])
        DD = int(parts[2])
        HH = int(parts[3])
        mm = int(parts[4])

        # Seconds can have milliseconds like "22.316"
        sec_part = parts[5]
        if "." in sec_part:
            sec_str, ms_str = sec_part.split(".", 1)
            SS = int(sec_str)
            # Normalize to exactly 3 digits of millisecond
            ms_str = (ms_str + "000")[:3]
            micro = int(ms_str) * 1000
        else:
            SS = int(sec_part)
            micro = 0

        # Turn 2-digit year into 2000-2099 range
        YYYY = 2000 + yy

        dt_utc = datetime(YYYY, MM, DD, HH, mm, SS, micro, tzinfo=timezone.utc)

        # RFC3339 format. Include milliseconds only if we actually had them.
        if micro:
            # Milliseconds are the first 3 digits of microseconds
            ms = f"{dt_utc.microsecond // 1000:03d}"
            return dt_utc.strftime(f"%Y-%m-%dT%H:%M:%S.{ms}Z")
        else:
            return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None

def convert_file(input_path, output_path=None, assume_tz_name="America/Vancouver", keep_sn=True):

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = Path("data/Anemometer_data_cleaned.csv")

    rows = []
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parsed = parse_line(line, assume_tz_name, keep_sn=False)
            if parsed is not None:
                rows.append(parsed)

    # Decide which columns to write
    columns = ["raw_ts", "ts", "U", "V", "T", "BatteryPct", "BattV", "BattC", "VectorMag", "VectorDir", "cardinal_dir"]

    with open(output_path, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            # Only keep requested columns
            writer.writerow({col: row.get(col, "") for col in columns})

    print(f"Converted {len(rows)} lines. Timestamps formatted to RFC3339.")
    print(f"Input : {input_path}")
    print(f"Output: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Convert anemometer .txt logs to CSV with RFC3339 UTC timestamps (no timezone conversion)."
    )
    parser.add_argument("input", help="Path to input .txt log file")
    parser.add_argument("output", help="Path to output .csv file")
    parser.add_argument(
        "--assume-tz",
        default="UTC",
        help="UNUSED in v2: timestamps are assumed to already be UTC. Kept for consistency.",
    )
    args = parser.parse_args()

    convert_file(args.input, args.output, args.assume_tz)

if __name__ == "__main__":
    main()
