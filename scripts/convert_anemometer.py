"""
Goal:
-----
Convert a raw anemometer .txt file into a clean .csv and standardize timestamps to RFC3339 (UTC).

Example input line:
    23:11:01:17:39:22.316 SN150 SN151 U -00.90 V -00.21 T 19.78 Battery% 100 BATTV 4.16 BATTC 0.000

Output columns:
    raw_ts, ts, sn1, sn2, U, V, T, BatteryPct, BattV, BattC, VectorMag, VectorDir
"""
import csv
import math
from datetime import datetime, timezone
import sys
import os
from pathlib import Path
import numpy as np


# ======================================================
# PARSE ONE LINE
# ======================================================
def parse_line(line, assume_tz_name, keep_sn=True):
    line = line.strip()
    if not line:
        return None

    parts = line.split()
    if not parts:
        return None

    raw_ts = parts[0]
    ts = parse_timestamp(raw_ts)  # <-- timezone fix applied here

    row = {
        "raw_ts": raw_ts,
        "ts": ts if ts else "",
        "sn1": "",
        "sn2": "",
        "U": "",
        "V": "",
        "T": "",
        "BatteryPct": "",
        "BattV": "",
        "BattC": "",
    }

    # Parse up to two SN fields
    index = 1
    sn_count = 0
    while index < len(parts) and sn_count < 2:
        item = parts[index]
        if item.upper().startswith("SN") and item[2:].isdigit():
            number_only = int(item[2:])
            if sn_count == 0:
                row["sn1"] = number_only if keep_sn else ""
            else:
                row["sn2"] = number_only if keep_sn else ""
            sn_count += 1
            index += 1
        else:
            break

    # Parse U/V/T and battery readings
    known_keys = {
        "U": "U",
        "V": "V",
        "T": "T",
        "Battery%": "BatteryPct",
        "BATTV": "BattV",
        "BATTC": "BattC",
    }

    current_key = None
    while index < len(parts):
        item = parts[index]
        if item in known_keys:
            current_key = known_keys[item]
            index += 1
            continue
        if current_key:
            try:
                value = float(item)
            except ValueError:
                value = ""
            row[current_key] = value
            current_key = None
        index += 1

    return row


# ======================================================
# PARSE TIMESTAMP (YY:MM:DD:HH:MM:SS.mmm → RFC3339)
# ======================================================
def parse_timestamp(raw_ts):
    """Assumes timestamps are already local/UTC — no timezone offset applied."""
    try:
        parts = raw_ts.split(":")
        if len(parts) != 6:
            return None

        yy, MM, DD, HH, mm = map(int, parts[:5])
        sec_part = parts[5]

        if "." in sec_part:
            sec_str, ms_str = sec_part.split(".", 1)
            SS = int(sec_str)
            ms_str = (ms_str + "000")[:3]
            micro = int(ms_str) * 1000
        else:
            SS, micro = int(sec_part), 0

        YYYY = 2000 + yy
        dt_utc = datetime(YYYY, MM, DD, HH, mm, SS, micro, tzinfo=timezone.utc)

        ms = f".{dt_utc.microsecond // 1000:03d}" if micro else ""
        return dt_utc.strftime(f"%Y-%m-%dT%H:%M:%S{ms}Z")
    except Exception:
        return None


# ======================================================
# MAIN CONVERTER
# ======================================================
def convert_file(input_path, output_path=None, assume_tz_name="America/Vancouver", keep_sn=True):
    """
    Converts a raw .txt file → /data/Anemometer_data_<basename>.csv
    Always returns the final output path.
    """

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = Path("data/Anemometer_data_cleaned.csv")

    rows = []
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parsed = parse_line(line, assume_tz_name, keep_sn=keep_sn)
            if parsed:
                rows.append(parsed)

    # Compute derived wind vector values
    for row in rows:
        try:
            u = float(row["U"])
            v = float(row["V"])
            if u == 0 and v == 0:
                speed = 0
                direction = 0
            else:
                speed = np.sqrt(u**2 + v**2) # a^2 + b^2 = c^2 NOTE calculating for c
                
                direction = (math.degrees(math.atan2(v,u)) + 360) % 360

            row["VectorMag"] = speed
            row["VectorDir"] = direction

        except Exception:
            mag, deg = "", ""



    # Write CSV
    columns = [
        "raw_ts", "ts", "sn1", "sn2",
        "U", "V", "T", "BatteryPct", "BattV", "BattC",
        "VectorMag", "VectorDir",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})

    print(f"[INFO] Converted {len(rows)} lines.")
    print(f"[INFO] Saved anemometer CSV to {output_path}")
    print("[INFO] Timestamps treated as already UTC (no offset applied).")
    return output_path


# ======================================================
# CLI ENTRY
# ======================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Convert anemometer .txt → CSV with UTC timestamps.")
    parser.add_argument("input", help="Path to input .txt log file")
    parser.add_argument("--drop-sn", action="store_true", help="Omit sn1 and sn2 columns")
    args = parser.parse_args()

    keep_sn = not args.drop_sn
    convert_file(args.input, None, keep_sn=keep_sn)


if __name__ == "__main__":
    main()
