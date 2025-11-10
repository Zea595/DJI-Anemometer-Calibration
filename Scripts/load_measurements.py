"""
load_measurements.py

Purpose:
--------
This script takes two CSV datasets generated in the drone weather monitoring project:

1) CLEAN_ANEMOMETER.csv   →  Inserts into: public.anemometer_measurements
2) CLEAN_COMBINED.csv     →  Inserts into: public.drone_measurements

This script does *NOT* modify or convert any timestamps.
That is done in convert_anemometer_v2.py

Security:
---------
All INSERT operations use parameterized SQL to prevent SQL injection.

Required Python packages:
-------------
    psycopg2-binary   → Provides the PostgreSQL database driver
    colorama          → Used for colored terminal output
    
Install dependencies:
    pip install psycopg2-binary
    pip install colorama

    If 'pip install' fails on Debian/Debian based distros due to "externally-managed-environment",
    use apt instead:

    sudo apt update
    sudo apt install -y python3-psycopg2 python3-colorama

Usage:
------
Run:
    python3 load_measurements.py

Before running, make sure:
- PostgreSQL is running and accessible
- The database/table structure already exists
- The CSV files are located in the same directory as this script
"""
import csv
import psycopg2
import psycopg2.extras
from colorama import Fore


def empty_to_none(value):
    """
    Convert an empty string to None so PostgreSQL stores it as NULL.
    Example:
        "3.14"   → "3.14" (kept as-is)
        ""       → None   (becomes NULL in the DB)
    """
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def load_anemometer_csv(connection, csv_path, batch_size=1000):
    """
    Inserts data from CLEAN_ANEMOMETER.csv into the 'anemometer_measurements' table.

    Expected CSV Columns (10):
        raw_ts, ts, U, V, T, BatteryPct, BattV, BattC, VectorMag, VectorDir

    Important:
        - ts (RFC3339) is already UTC and is inserted directly.
        - raw_ts is inserted unchanged for reference.
    """

    insert_sql = """
        INSERT INTO public.anemometer_measurements
            (ts_utc, raw_ts, u, v, temperature_c, battery_pct, batt_v, batt_c, vector_mag, vector_dir_deg)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    batch = []
    processed_rows = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            processed_rows += 1 # Counts each processed row

            params = (
                empty_to_none(row.get("ts")),          # Data integrity check on all parameters
                empty_to_none(row.get("raw_ts")),      
                empty_to_none(row.get("U")),
                empty_to_none(row.get("V")),
                empty_to_none(row.get("T")),
                empty_to_none(row.get("BatteryPct")),
                empty_to_none(row.get("BattV")),
                empty_to_none(row.get("BattC")),
                empty_to_none(row.get("VectorMag")),
                empty_to_none(row.get("VectorDir")),
            )

            batch.append(params)

            # Write in batches for speed. 1,000 row batches
            if len(batch) >= batch_size:
                with connection.cursor() as cur:
                    # Arguments needed for .execute_batch are: 
                    # cursor, SQL statement, List (or iterable)
                    psycopg2.extras.execute_batch(cur, insert_sql, batch)
                connection.commit()
                batch = []

            # Prints progress every 5000 rows
            if processed_rows % 5000 == 0:
                print(f"  {Fore.YELLOW}{processed_rows:,}{Fore.RESET} rows processed so far...")

    # Insert any records that didn't reach 1,000
    # ex. From 1,200 records. 200 would be inserted here
    if batch:
        with connection.cursor() as cur:
            psycopg2.extras.execute_batch(cur, insert_sql, batch)
        connection.commit()

    print(f"  Finished Anemometer Insert ({Fore.YELLOW}{processed_rows:,}{Fore.RESET} rows total)")

def load_drone_csv(connection, csv_path, batch_size=1000):
    """
    Inserts data from CLEAN_COMBINED.csv into the drone_measurements table.

    Expected CSV Columns (11):
        CUSTOM.updateTime [local]
        WEATHER.windDirection
        WEATHER.windRelativeDirection
        WEATHER.windSpeed [MPH]
        WEATHER.maxWindSpeed [MPH]
        WEATHER.windStrength
        WEATHER.isFacingWind
        WEATHER.isFlyingIntoWind
        Drone_Time(PST)
        Drone_Time(UTC+RFC3339)
        Drone_Direction

    Important:
        - Both timestamp fields are inserted as is.
        - Text fields remain text.
        - Numeric columns store NULL instead of "" when missing.
    """

    insert_sql = """
        INSERT INTO public.drone_measurements
            (drone_time_utc, drone_time_pst, update_time_local_raw,
             wind_direction, wind_relative_direction,
             wind_speed_mph, max_wind_speed_mph,
             wind_strength, is_facing_wind, is_flying_into_wind,
             drone_direction_deg)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    batch = []
    processed_rows = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            processed_rows += 1

            params = (
                empty_to_none(row.get("Drone_Time(UTC+RFC3339)")),
                empty_to_none(row.get("Drone_Time(PST)")),
                empty_to_none(row.get("CUSTOM.updateTime [local]")),
                empty_to_none(row.get("WEATHER.windDirection")),
                empty_to_none(row.get("WEATHER.windRelativeDirection")),
                empty_to_none(row.get("WEATHER.windSpeed [MPH]")),
                empty_to_none(row.get("WEATHER.maxWindSpeed [MPH]")),
                empty_to_none(row.get("WEATHER.windStrength")),
                empty_to_none(row.get("WEATHER.isFacingWind")),
                empty_to_none(row.get("WEATHER.isFlyingIntoWind")),
                empty_to_none(row.get("Drone_Direction_Deg")),
            )

            batch.append(params)

            if len(batch) >= batch_size:
                with connection.cursor() as cursor:
                    psycopg2.extras.execute_batch(cursor, insert_sql, batch)
                connection.commit()
                batch = []

            if processed_rows % 5000 == 0:
                print(f"  {Fore.YELLOW}{processed_rows:,}{Fore.RESET} rows processed so far...")

    if batch:
        with connection.cursor() as cursor:
            psycopg2.extras.execute_batch(cursor, insert_sql, batch)
        connection.commit()

    print(f"  Finished Drone Insert ({Fore.YELLOW}{processed_rows:,}{Fore.RESET} rows total)")

def main():
    """
    Main entry point.
    Provide database credentials here to use it in the Docker container.
    """
    print("Inserting data into database. Please wait...")
    connection = psycopg2.connect(
        dbname="rpas",
        user="admin",
        password="admin123",
        host="localhost",
        port=5432,
    )

    load_anemometer_csv(connection, "./CLEAN_ANEMOMETER.csv")
    load_drone_csv(connection, "./CLEAN_COMBINED.csv")

    connection.close()
    print(Fore.GREEN + "Data inserted successfully!" + Fore.RESET)


if __name__ == "__main__":
    main()