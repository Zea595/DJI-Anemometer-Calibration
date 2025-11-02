from pathlib import Path
import pandas as pd
import re, sys
from datetime import datetime, timedelta

'''
PURPOSE OF THIS SCRIPT
- parse out the WEATHER columns
- parse out the time from the file's title
- parse out the CUSTOM columns

With all of the above:
- RECONSTRUCT the timestamp into clock time (format of the anemometer)
- new timestamp will be in RFC3339 timestamp format: YYYY-MM-DDT00:00:00Z


HOW TO USE:
python .Clean_and_Timestamp.py <file_path>

'''

# format_time is a helper function to parse the start time string into a datetime object
# df_filtered = the columns we have selected for this experiment

# RETURNS: the timestamp in string format in RFC3339 format
def format_time(df_filtered, start_time):
    
    start_time_object = datetime.strptime(start_time, '%H:%M:%S')

    df_filtered['df_offset_time'] = df_filtered['OSD.flyTime [s]'].apply(
        lambda s: (start_time_object + timedelta(seconds=float(s))).strftime("%H:%M:%S")
    ) 

    # TimeStamp column is the final RFC3339 format
    df_filtered['TimeStamp'] = df_filtered['CUSTOM.date [local]'] + ":" + df_filtered['df_offset_time']

    # Drop the columns we don't need
    df_filtered.drop('df_offset_time', axis=1, inplace=True)
    df_filtered.drop('CUSTOM.date [local]', axis=1, inplace=True)
    df_filtered.drop('OSD.flyTime [s]', axis=1, inplace=True)                     
    return df_filtered



def main():

    script_path = Path(__file__).resolve()

    filepath = Path(sys.argv[1])
    filename = filepath.name

    csv_path_output = script_path.parent.parent / 'Data' / 'Cleaned' / f'CLEAN_{filename}'

    # Read the CSV
    df = pd.read_csv(filepath)

    # Filter columns that start with "CUSTOM" (CUSTOM includes the date) or "WEATHER" 
    relevant_cols = [c for c in df.columns if c.startswith('WEATHER') or c == 'OSD.flyTime [s]' or c == 'CUSTOM.date [local]']

    # Keep only those columns
    df_filtered = df[relevant_cols]

    # parse the starting time from filename:
    match = re.findall(r'\[(\d{2}-\d{2}-\d{2})\]', filename)
    if match:
        start_time = match[0].replace('-', ':')
        formatted_time = format_time(df_filtered, start_time)

        output = pd.DataFrame(formatted_time)
        output.to_csv(csv_path_output, index=False)
    else:
        print("Cannot find timestamp in file title.")


if __name__ == "__main__":
    main()
