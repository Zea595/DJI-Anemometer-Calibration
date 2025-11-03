from pathlib import Path
import pandas as pd
import re, sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

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

# format_time is a helper function to parse the start time string into a datetime object
# df_filtered = the columns we have selected for this experiment

def convert_UTC(row):

    pst_time = row['Drone_Time(PST)']
    format_data = "%Y-%m-%d %I:%M:%S.%f %p"

    date = datetime.strptime(pst_time, format_data)
    date_aware = date.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
    utc_time = date_aware.astimezone(timezone.utc)
    rfc3339_utc = utc_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"  

    return rfc3339_utc

def format_time(df_filtered):

    # TimeStamp column is the final RFC3339 format
    df_filtered['Drone_Time(PST)'] = df_filtered['CUSTOM.date [local]'] + ' ' + df_filtered['CUSTOM.updateTime [local]']
    df_filtered['Drone_Time(UTC+RFC3339)'] = df_filtered.apply(convert_UTC, axis=1)

    # Drop the columns we don't need
    df_filtered.drop('CUSTOM.date [local]', axis=1, inplace=True)
               
    return df_filtered

def combineCSVInDir(csv_folder_path):
    # Use .iterdir() to iterate through files in the directory
    csv_files = [f for f in Path(csv_folder_path).iterdir() if f.suffix == '.csv']

    all_dataframes = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        all_dataframes.append(df)

    combined_df = pd.concat(all_dataframes, ignore_index=True)
    return combined_df



def main():

    script_path = Path(__file__).resolve()

    filepath = Path(sys.argv[1])
    # filename = filepath.name

    # csv_path_output = script_path.parent.parent / 'Data' / 'Cleaned' / f'CLEAN_{filename}'
    csv_path_output = script_path.parent.parent / 'Data' / 'Cleaned' / f'CLEAN_COMBINED.csv'

    # Read the CSV
    # df = pd.read_csv(filepath)
    df = combineCSVInDir(filepath)

    # Filter columns that start with "CUSTOM" (CUSTOM includes the date) or "WEATHER" 
    relevant_cols = [c for c in df.columns if c.startswith('CUSTOM') or c.startswith('WEATHER')]

    # Keep only those columns
    df_filtered = df[relevant_cols]

    formatted_time = format_time(df_filtered)
    output = pd.DataFrame(formatted_time)
    output.to_csv(csv_path_output, index=False)



if __name__ == "__main__":
    main()
