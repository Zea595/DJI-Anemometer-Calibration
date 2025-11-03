from pathlib import Path
import pandas as pd
import re, sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo





def main():

    script_path = Path(__file__).resolve()

    filepath = Path(sys.argv[1])
    filename = filepath.name

    csv_path_output = script_path.parent.parent / 'Data' / 'Cleaned' / f'CLEAN_{filename}'

    # Read the CSV
    df = pd.read_csv(filepath)

    # Filter columns that start with "CUSTOM" (CUSTOM includes the date) or "WEATHER" 
    relevant_cols = [c for c in df.columns if c.startswith('CUSTOM') or c.startswith('WEATHER')]

    # Keep only those columns
    df_filtered = df[relevant_cols]

    formatted_time = format_time(df_filtered)
    output = pd.DataFrame(formatted_time)
    output.to_csv(csv_path_output, index=False)



if __name__ == "__main__":
    main()