"""
Goal:
-----
Convert a raw anemometer .txt file into a clean .csv and standardize timestamps to RFC3339 (UTC).

Why this exists:
----------------
The logs look like this (one line per reading):
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
4) Optionally keep two "SN" items (they might be serial numbers or something else). Can drop them later with --drop-sn.

Usage:
------
python3 convert_anemometer_simple.py INPUT.txt OUTPUT.csv [--assume-tz America/Vancouver] [--drop-sn]

Columns written:
----------------
raw_ts, ts, sn1, sn2, U, V, T, BatteryPct, BattV, BattC
(If "--drop-sn" is used, sn1 and sn2 will be omitted.)
"""
import argparse # Handles command-line arguments
import csv
from datetime import datetime, timezone # Builds datetimes
from zoneinfo import ZoneInfo # Handles timezone convertion
import sys

def parse_line(line, assume_tz_name, keep_sn=True):
    """
    Parse one log line.
    Returns a dict with column names and values, or None if the line is empty/invalid.

    We look for items in this order:
      - First item: timestamp (required)
      - Next two items (optional): SN codes like "SN150" "SN151"
      - Then key/value pairs: U, V, T, Battery%, BATTV, BATTC
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
    ts = parse_timestamp(raw_ts, assume_tz_name)

    # Prepare the output row with defaults set to empty strings (Template for one row of the CSV)
    row = {
        "raw_ts": raw_ts,
        "ts": ts if ts is not None else "",
        "sn1": "",
        "sn2": "",
        "U": "",
        "V": "",
        "T": "",
        "BatteryPct": "",
        "BattV": "",
        "BattC": "",
    }

    # 2) Optional SN items (up to 2 items starting with "SN" followed by numbers)
    index = 1
    sn_count = 0
    while index < len(parts) and sn_count < 2:
        item = parts[index]
        if item.upper().startswith("SN") and item[2:].isdigit():
            # Store just the number part (e.g., "SN150" -> 150). If you prefer "SN150", change the next line:
            number_only = int(item[2:])
            if sn_count == 0:
                row["sn1"] = number_only if keep_sn else ""
            else:
                row["sn2"] = number_only if keep_sn else ""
            sn_count += 1
            index += 1
        else:
            break  # Not an SN item

    # 3) Key/value pairs for the rest of the items
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

    return row

def parse_timestamp(raw_ts, assume_tz_name):
    """
    Convert '23:11:01:17:39:22.316' (YY:MM:DD:HH:MM:SS.mmm) to RFC3339 UTC string.
    Returns: (rfc3339_utc_str or None)
    """
    if not raw_ts or not isinstance(raw_ts, str):
        return None
    
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
            # Normalize to exactly 3 digits of milliseconds
            ms_str = (ms_str + "000")[:3]
            micro = int(ms_str) * 1000
        else:
            SS = int(sec_part)
            micro = 0

        # Turn 2-digit year into 2000-2099 range
        YYYY = 2000 + yy

       # Create timezone-aware datetime directly using ZoneInfo
        # Handle potential DST ambiguity with fold parameter
        tz_local = ZoneInfo(assume_tz_name)
        dt_local = datetime(YYYY, MM, DD, HH, mm, SS, micro, tzinfo=tz_local, fold=0)
        
        # Convert to UTC
        dt_utc = dt_local.astimezone(timezone.utc)
        
        # RFC3339 format. Include milliseconds only if we actually had them.
        if micro:
            # Milliseconds are the first 3 digits of microseconds
            ms = f"{dt_utc.microsecond // 1000:03d}"
            return dt_utc.strftime(f"%Y-%m-%dT%H:%M:%S.{ms}Z")
        else:
            return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        
    except Exception as e:
        print(f"DEBUG: parse_timestamp failed on '{raw_ts}': {type(e).__name__}: {e}")
        return None

def convert_file(input_path, output_path, assume_tz_name, keep_sn=True):
    rows = []
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parsed = parse_line(line, assume_tz_name, keep_sn=keep_sn)
            if parsed is not None:
                rows.append(parsed)


    if len(rows) == 0:
        print("Error: No valid data lines found in input file.")
        sys.exit(1)

    # Decide which columns to write
    columns = ["raw_ts", "ts", "U", "V", "T", "BatteryPct", "BattV", "BattC"]
    if keep_sn:
        # Insert sn1, sn2 after ts for readability
        columns = ["raw_ts", "ts", "sn1", "sn2", "U", "V", "T", "BatteryPct", "BattV", "BattC"]

    with open(output_path, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            # Only keep requested columns
            writer.writerow({col: row.get(col, "") for col in columns})

    print(f"Converted {len(rows)} lines.")
    print(f"Input : {input_path}")
    print(f"Output: {output_path}")
    print(f"Timezone assumed: {assume_tz_name} -> converted to UTC (Z) in 'ts' column.")
    if keep_sn:
        print("SN columns kept (sn1, sn2). Use --drop-sn to omit them.")

def main():
    parser = argparse.ArgumentParser(
        description="Convert anemometer .txt logs to CSV with RFC3339 UTC timestamps."
    )
    parser.add_argument("input", help="Path to input .txt log file")
    parser.add_argument("output", help="Path to output .csv file")
    parser.add_argument(
        "--assume-tz",
        default="America/Vancouver",
        help="Timezone for naive timestamps (default: America/Vancouver)",
    )
    parser.add_argument(
        "--drop-sn",
        action="store_true",
        help="If set, omit sn1 and sn2 columns from the output",
    )
    args = parser.parse_args()

    keep_sn = not args.drop_sn

    # Basic sanity check
    try:
        ZoneInfo(args.assume_tz)  # will raise if invalid tz name
    except Exception:
        print("Error: invalid timezone name. Example: America/Vancouver")
        sys.exit(1)

    convert_file(args.input, args.output, args.assume_tz, keep_sn=keep_sn)

if __name__ == "__main__":
    main()
