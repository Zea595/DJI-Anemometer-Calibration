from pathlib import Path
import sys
from typing import Iterable, Union, Optional, List

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd


"""
USAGE
-----
    python / python3 Clean_and_Timestamp.py <PATH_TO_FOLDER_OR_CSV>

- If a folder is provided: all CSVs in the folder are combined.
- If a single CSV file is provided: only that file is processed.
- If `input_paths` is passed programmatically to `main()`: those CSVs are combined.

The output file is written to:

    <base_root>/data/CLEAN_COMBINED.csv

PURPOSE
-------
This script processes raw DJI drone CSV logs and:

1. Combines multiple raw CSV files into a single DataFrame:
   - Either from a directory of CSVs
   - Or a list of explicit CSV paths
   - Or a single CSV path

2. Constructs local drone time (PST) from:
   - "CUSTOM.date [local]"
   - "CUSTOM.updateTime [local]"

3. Converts that local PST time into:
   - "Drone_Time(UTC+RFC3339)"  (UTC RFC3339, with 'Z')
   - "Drone_Time(PST)_Clean"   (ISO8601 with America/Los_Angeles timezone)

4. Converts the cardinal wind direction ("WEATHER.windDirection") to a
   flipped degree direction ("Drone_Direction").

5. Converts wind speed from mph to m/s into "WindSpeed(m/s)".

6. Writes a cleaned CSV with these transformations to:
   - data/CLEAN_COMBINED.csv (under a derived base directory)
"""


# =====================================================================
# Wind speed conversion helpers
# =====================================================================

def convertToMetersPerSecond(row: pd.Series) -> float:
    """
    Convert wind speed from mph to m/s for a row.

    Parameters
    ----------
    row : pd.Series
        A row that must contain "WEATHER.windSpeed [MPH]".

    Returns
    -------
    float
        Wind speed in m/s.
    """
    return float(row["WEATHER.windSpeed [MPH]"]) * 0.44704


# =====================================================================
# Time conversion helpers (PST → UTC / RFC3339)
# =====================================================================

def convert_UTC(row: pd.Series) -> str:
    """
    Convert a row's local PST drone time string into UTC RFC3339.

    Input column:
        row['Drone_Time(PST)'] must be a string of the form:
            "%Y-%m-%d %I:%M:%S.%f %p"

    Steps:
        - Parse naive datetime in America/Los_Angeles
        - Convert to UTC
        - Format as RFC3339 with milliseconds + trailing 'Z'

    Returns
    -------
    str
        A string like "2023-11-01T21:37:31.560Z".
    """
    pst_time = row["Drone_Time(PST)"]
    fmt = "%Y-%m-%d %I:%M:%S.%f %p"

    # Parse naive datetime
    dt_local = datetime.strptime(pst_time, fmt)

    # Attach PST timezone
    dt_aware = dt_local.replace(tzinfo=ZoneInfo("America/Los_Angeles"))

    # Convert to UTC
    dt_utc = dt_aware.astimezone(timezone.utc)

    # Format as RFC3339 with 3 decimal places
    rfc3339_utc = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return rfc3339_utc


def convert_PST(row: pd.Series) -> str:
    """
    Convert a row's local PST drone time string into an ISO8601 string
    with America/Los_Angeles timezone.

    Input column:
        row["Drone_Time(PST)"] must be a string of the form:
            "%Y-%m-%d %I:%M:%S.%f %p"

    Returns
    -------
    str
        ISO8601 string (e.g. "2023-11-01T14:37:31.560000-07:00")
    """
    pst_raw = row["Drone_Time(PST)"]
    fmt_in = "%Y-%m-%d %I:%M:%S.%f %p"

    dt = datetime.strptime(pst_raw, fmt_in)
    dt = dt.replace(tzinfo=ZoneInfo("America/Los_Angeles"))

    # ISO8601 string with timezone offset
    return dt.isoformat()


def format_time(df_filtered: pd.DataFrame) -> pd.DataFrame:
    """
    Combine local date and time columns into a single PST timestamp and derive:
        - "Drone_Time(UTC+RFC3339)"
        - "Drone_Time(PST)_Clean"

    Input columns required:
        - 'CUSTOM.date [local]'
        - 'CUSTOM.updateTime [local]'

    Side effects:
        - Adds:
            'Drone_Time(PST)'
            'Drone_Time(UTC+RFC3339)'
            'Drone_Time(PST)_Clean'
        - Drops:
            'CUSTOM.date [local]'
            'Drone_Time(PST)'

    Parameters
    ----------
    df_filtered : pd.DataFrame
        DataFrame containing at least the CUSTOM date/time columns.

    Returns
    -------
    pd.DataFrame
        Transformed DataFrame with time-related columns added/dropped.
    """
    # Construct combined local time string, e.g. "2023-11-01 11:24:29.64 AM"
    df_filtered["Drone_Time(PST)"] = (
        df_filtered["CUSTOM.date [local]"] + " " +
        df_filtered["CUSTOM.updateTime [local]"]
    )

    # Convert to RFC3339 UTC and cleaned PST ISO8601
    df_filtered["Drone_Time(UTC+RFC3339)"] = df_filtered.apply(convert_UTC, axis=1)
    df_filtered["Drone_Time(PST)_Clean"] = df_filtered.apply(convert_PST, axis=1)

    # Remove now-redundant columns
    df_filtered.drop("CUSTOM.date [local]", axis=1, inplace=True)
    df_filtered.drop("Drone_Time(PST)", axis=1, inplace=True)

    return df_filtered


# =====================================================================
# CSV combination helpers
# =====================================================================

def combine_csv_in_dir(csv_folder_path: Union[str, Path]) -> pd.DataFrame:
    """
    Combine all CSV files in a given directory into a single DataFrame.

    Parameters
    ----------
    csv_folder_path : str or Path
        Path to a directory containing CSV files.

    Returns
    -------
    pd.DataFrame
        Combined DataFrame of all CSV content.

    Raises
    ------
    ValueError
        If the path is not a directory or no CSV files are found.
    """
    folder = Path(csv_folder_path)
    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder}")

    csv_files = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() == ".csv"
    )

    if not csv_files:
        raise ValueError(f"No CSV files found in {folder}")

    frames = [pd.read_csv(p) for p in csv_files]
    return pd.concat(frames, ignore_index=True, sort=False)


def combine_csv_from_list(paths: Iterable[Union[str, Path]]) -> pd.DataFrame:
    """
    Combine CSV files from an iterable of paths into a single DataFrame.

    Parameters
    ----------
    paths : Iterable[str or Path]
        Paths to CSV files. Non-CSV paths are ignored.

    Returns
    -------
    pd.DataFrame
        Combined DataFrame of all CSV content from the given paths.

    Raises
    ------
    ValueError
        If no CSV files are provided.
    FileNotFoundError
        If any of the supplied CSV paths does not exist.
    """
    file_paths: List[Path] = []

    # Filter only ".csv" files (case-insensitive)
    for p in paths:
        pp = Path(p)
        if pp.suffix.lower() == ".csv":
            file_paths.append(pp)

    if not file_paths:
        raise ValueError("No CSV files provided in input_paths.")

    # Enforce existence
    missing = [str(p) for p in file_paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"The following files do not exist: {missing}")

    frames = [pd.read_csv(p) for p in file_paths]
    return pd.concat(frames, ignore_index=True, sort=False)


# =====================================================================
# Direction conversion (cardinal → degrees, flipped)
# =====================================================================

def convert_cardinal_to_degrees(
    df: pd.DataFrame,
    column_name: str = "WEATHER.windDirection"
) -> pd.DataFrame:
    """
    Convert a cardinal wind direction column (N, NE, E, SW, etc.) into
    a flipped degree direction (meteorological style, offset by 180°).

    The result is stored in a new column:
        "Drone_Direction"

    Mapping is:
        N  ->  0°
        E  -> 90°
        S  -> 180°
        W  -> 270°
        etc.
    Then flipped by 180°: Drone_Direction = (deg + 180) % 360.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing the cardinal direction column.
    column_name : str, default "WEATHER.windDirection"
        Name of the column with cardinal directions.

    Returns
    -------
    pd.DataFrame
        Copy of the DataFrame with a new "Drone_Direction" column.
    """
    # Base mapping: cardinal -> degrees
    direction_map = {
        "N": 0,
        "NNE": 22.5, "NE": 45, "ENE": 67.5,
        "E": 90,
        "ESE": 112.5, "SE": 135, "SSE": 157.5,
        "S": 180,
        "SSW": 202.5, "SW": 225, "WSW": 247.5,
        "W": 270,
        "WNW": 292.5, "NW": 315, "NNW": 337.5,
    }

    # Flip by 180° (e.g., direction of drone vs direction of wind)
    flipped_map = {k: (deg + 180) % 360 for k, deg in direction_map.items()}

    df = df.copy()

    # Normalize values for mapping
    df[column_name] = (
        df[column_name]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Map to degrees; invalid values become NaN
    df["Drone_Direction"] = df[column_name].map(flipped_map)

    return df


# =====================================================================
# Main processing pipeline
# =====================================================================

def main(
    input_path: Optional[Union[str, Path]] = None,
    input_paths: Optional[Iterable[Union[str, Path]]] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """
    Main entry point for cleaning and timestamping drone CSV data.

    You can call this in three ways:

    1. Command line:
        python Clean_and_Timestamp.py <PATH_TO_FOLDER_OR_CSV>

       - If the path is a directory:
            - All CSV files under that directory are combined.
       - If the path is a single CSV:
            - Only that CSV is read.

    2. Programmatically with `input_paths`:
        main(input_paths=[...])
       - Multiple CSV files are combined.

    3. Programmatically with `input_path`:
        main(input_path="path/to/folder/or/file.csv")

    Output location:
    ----------------
    If `output_path` is not provided, the script derives a base directory
    and writes to:

        <base_root>/data/CLEAN_COMBINED.csv

    where base_root is:
        - For `input_paths`: two levels up from the first path,
        - For a directory input_path: one level above the parent of that dir,
        - For a single CSV input_path: two levels above that CSV.

    Returns
    -------
    str
        Absolute path to the written CSV.
    """
    # -------------------------------------------------------------
    # 1. Resolve input DataFrame
    # -------------------------------------------------------------
    if input_paths is not None:
        # Combine explicit list of CSV paths
        df = combine_csv_from_list(input_paths)
        ip_list = list(input_paths)
        base_for_default_out = (
            Path(ip_list[0]).resolve().parents[2]
            if len(ip_list) >= 1
            else Path(".")
        )
    else:
        # If not provided, fall back to CLI argument
        if input_path is None:
            if len(sys.argv) < 2:
                raise SystemExit(
                    "Usage: python Clean_and_Timestamp.py <PATH_TO_FOLDER_OR_CSV>"
                )
            input_path = sys.argv[1]

        p = Path(input_path).resolve()

        if p.is_dir():
            # Combine all CSVs in this directory
            df = combine_csv_in_dir(p)
            # Heuristic for a "repo root"-like base directory
            base_for_default_out = p.parents[1] if len(p.parents) >= 2 else p.parent

        elif p.is_file():
            # Legacy behavior: single CSV path
            df = pd.read_csv(p)
            base_for_default_out = (
                p.parents[2] if len(p.parents) >= 3 else p.parent
            )
        else:
            raise FileNotFoundError(f"Input path not found: {p}")

    # -------------------------------------------------------------
    # 2. Determine output path
    # -------------------------------------------------------------
    if output_path is None:
        # Default: <base>/data/CLEAN_COMBINED.csv
        csv_path_output = base_for_default_out / "data" / "CLEAN_COMBINED.csv"
    else:
        csv_path_output = Path(output_path).resolve()

    csv_path_output.parent.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------
    # 3. Filter to relevant columns and perform transformations
    # -------------------------------------------------------------
    relevant_cols = [
        c
        for c in df.columns
        if c.startswith("CUSTOM")
        or c.startswith("WEATHER")
        or c.startswith("DETAILS.aircraftSerial")
    ]
    df_filtered = df[relevant_cols]

    # Parse and enrich time columns
    formatted_time = format_time(df_filtered)

    # Convert cardinal directions → flipped degrees, into "Drone_Direction"
    converted = convert_cardinal_to_degrees(formatted_time)

    # Convert wind speed from mph to m/s into "WindSpeed(m/s)"
    converted["WindSpeed(m/s)"] = converted.apply(
        convertToMetersPerSecond, axis=1
    )

    # -------------------------------------------------------------
    # 4. Write output CSV
    # -------------------------------------------------------------
    output_df = pd.DataFrame(converted)
    output_df.to_csv(csv_path_output, index=False)

    return str(csv_path_output)


# =====================================================================
# CLI entrypoint
# =====================================================================

if __name__ == "__main__":
    # Run using command line arguments if not used as a library
    out = main()
    print(f"Cleaned CSV written to: {out}")
