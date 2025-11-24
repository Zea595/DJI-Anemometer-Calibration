from pathlib import Path
import pandas as pd
import re, sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Iterable, Union, Optional, List

'''
USAGE: python/python3 .Clean_and_Timestamp.py <PATH_TO_FOLDER>
    > file will be outputted to Data/Cleaned as CLEAN_originalFileName

PURPOSE OF THIS SCRIPT
- DRONE WAS FLOWN IN LOS ANGELES, GPS COORDS LATITUDE:33.8 LONGITUDE:-117

*UPDATE* - *script now combines all raw csv files together and makes it into one list*
- COMBINE DATE COLUMN WITH TIME COLUMN
- Format LOCAL TIME (PST) TO UTC
- OUTPUT to new column called "Drone_Time(UTC+RFC3339)
- OUTPUT to new csv file in Data/Cleaned

'''

def convertToMetersPerSecond(row):
    return float(row["WEATHER.windSpeed [MPH]"]) * 0.44704

# helper function for format_time lambda function
def convert_UTC(row):

    pst_time = row['Drone_Time(PST)']
    format_data = "%Y-%m-%d %I:%M:%S.%f %p"

    date = datetime.strptime(pst_time, format_data)

    date_aware = date.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
    utc_time = date_aware.astimezone(timezone.utc)
    rfc3339_utc = utc_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"  

    return rfc3339_utc

# helper function to parse pst into a real time object
def convert_PST(row):
    pst_raw = row["Drone_Time(PST)"]
    fmt_in = "%Y-%m-%d %I:%M:%S.%f %p"

    dt = datetime.strptime(pst_raw, fmt_in)
    dt = dt.replace(tzinfo=ZoneInfo("America/Los_Angeles"))

    # Write as ISO8601
    return dt.isoformat()       # <-- PERFECT for CSV + Jupyter


# format_time is a helper function to parse the start time string into a datetime object
# df_filtered = the columns we have selected for this experiment
def format_time(df_filtered):

    # TimeStamp column is the final RFC3339 format
    df_filtered['Drone_Time(PST)'] = df_filtered['CUSTOM.date [local]'] + ' ' + df_filtered['CUSTOM.updateTime [local]']
    df_filtered['Drone_Time(UTC+RFC3339)'] = df_filtered.apply(convert_UTC, axis=1)
    df_filtered['Drone_Time(PST)_Clean'] = df_filtered.apply(convert_PST, axis=1)

    # Drop the columns we don't need
    df_filtered.drop('CUSTOM.date [local]', axis=1, inplace=True)
    df_filtered.drop('Drone_Time(PST)', axis=1, inplace=True)
               
    return df_filtered


def combine_csv_in_dir(csv_folder_path: Union[str, Path]) -> pd.DataFrame:
    folder = Path(csv_folder_path)
    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder}")

    csv_files = sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".csv"])
    if not csv_files:
        raise ValueError(f"No CSV files found in {folder}")

    frames = []
    for p in csv_files:
        frames.append(pd.read_csv(p))
    return pd.concat(frames, ignore_index=True, sort=False)


def combine_csv_from_list(paths: Iterable[Union[str, Path]]) -> pd.DataFrame:
    # Accept strings or Paths; filter to .csv case-insensitively
    file_paths: List[Path] = []
    for p in paths:
        pp = Path(p)
        if pp.suffix.lower() == ".csv":
            file_paths.append(pp)

    if not file_paths:
        raise ValueError("No CSV files provided in input_paths.")

    # (optional) enforce existence
    missing = [str(p) for p in file_paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"The following files do not exist: {missing}")

    frames = []
    for p in file_paths:
        frames.append(pd.read_csv(p))
    return pd.concat(frames, ignore_index=True, sort=False)

def convert_cardinal_to_degrees(df, column_name="WEATHER.windDirection"):
    """
    Convert a DataFrame column of cardinal directions (e.g., N, NE, E, SW)
    into meteorological degrees (0° = North, 90° = East, etc.).

    Parameters:
        df (pd.DataFrame): The input DataFrame.
        column_name (str): The name of the column with cardinal directions.

    Returns:
        pd.DataFrame: A copy of the DataFrame with a new column 'DirectionDeg'.
    """

    # Mapping of cardinal directions to degrees
    direction_map = {
        "N": 0,
        "NNE": 22.5, "NE": 45, "ENE": 67.5,
        "E": 90,
        "ESE": 112.5, "SE": 135, "SSE": 157.5,
        "S": 180,
        "SSW": 202.5, "SW": 225, "WSW": 247.5,
        "W": 270,
        "WNW": 292.5, "NW": 315, "NNW": 337.5
    }

    # Normalize input (strip spaces, uppercase)
    df = df.copy()
    df[column_name] = df[column_name].astype(str).str.strip().str.upper()

    # Map directions to degrees, leaving NaN if invalid
    df["Drone_Direction"] = df[column_name].map(direction_map)

    return df


def main(
    input_path: Optional[Union[str, Path]] = None,      # folder path OR single CSV path (legacy)
    input_paths: Optional[Iterable[Union[str, Path]]] = None,  # NEW: multiple CSVs
    output_path: Optional[Union[str, Path]] = None      # NEW: explicit output file
):
    """
    If input_paths is provided, combine those CSVs.
    Else, if input_path is provided:
        - if it's a directory, combine all CSVs inside
        - if it's a file, read that single CSV
    Else, fall back to CLI: python Clean_and_Timestamp.py <PATH>
    """
    # Resolve inputs
    if input_paths is not None:
        df = combine_csv_from_list(input_paths)
        base_for_default_out = Path(list(input_paths)[0]).resolve().parents[2] if len(list(input_paths)) >= 1 else Path(".")
    else:
        if input_path is None:
            if len(sys.argv) < 2:
                raise SystemExit("Usage: python Clean_and_Timestamp.py <PATH_TO_FOLDER_OR_CSV>")
            input_path = sys.argv[1]

        p = Path(input_path).resolve()
        if p.is_dir():
            df = combine_csv_in_dir(p)
            base_for_default_out = p.parents[1] if len(p.parents) >= 2 else p.parent
        elif p.is_file():
            # Keep legacy behavior if a single CSV is passed
            df = pd.read_csv(p)
            base_for_default_out = p.parents[2] if len(p.parents) >= 3 else p.parent
        else:
            raise FileNotFoundError(f"Input path not found: {p}")

    # Compute default output if not given: <repo_root>/Data/Cleaned/CLEAN_COMBINED.csv
    if output_path is None:
        csv_path_output = base_for_default_out / "data" / "CLEAN_COMBINED.csv"
    else:
        csv_path_output = Path(output_path).resolve()

    csv_path_output.parent.mkdir(parents=True, exist_ok=True)

    # Select & transform columns
    relevant_cols = [c for c in df.columns if c.startswith("CUSTOM") or c.startswith("WEATHER")]
    df_filtered = df[relevant_cols]

    # FORMAT TIME
    formatted_time = format_time(df_filtered)
    converted = convert_cardinal_to_degrees(formatted_time)

    # CONVERT TO METERS PER SECOND
    converted['WindSpeed(m/s)'] = converted.apply(convertToMetersPerSecond, axis=1)


    # OUTPUT TO CSV
    output = pd.DataFrame(converted)
    output.to_csv(csv_path_output, index=False)
    return str(csv_path_output)



if __name__ == "__main__":
    main()
