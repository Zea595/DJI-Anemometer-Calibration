from datetime import datetime
import argparse
import csv

import test



def get_csv_file(file_path):
    with open(file_path, "r") as csvfile:
        filedata = csv.DictReader(csvfile) # reads the csv into a dictionary format

        # Convert the filedata to a list of dictionaries to access the data after the file has been closed
        data = []
        for row in filedata:
            data.append(row)
            
        return data


def compare_time(DJI,ANE): #if DJI.time == ame.time: pass the speed and direction variables into the vector_math function.
    
    

    pass

def vector_math(v1,v2):

    pass



class extra_needed_functions:
    @staticmethod
    def txt_to_csv(file_path):
        with open(file_path, "r") as file: # opens the text file
            data = file.readlines()
            with open(file_path + ".csv", "w") as f:
                f.writelines(data) # writes the text file data into a csv file for easier reading
    
    @staticmethod            
    def parse_ame_line(text): #changes the datetime format to match the DJI drone data.
        if '.' in text["ts"]: # check for milliseconds
            dt = datetime.strptime(text["ts"], "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            dt = datetime.strptime(text["ts"], "%Y-%m-%dT%H:%M:%SZ")
            
        text["ts"] = dt.strftime("%Y-%m-%d:%H:%M:%S") # change the format to match the DJI time format


def test(ame,dji):
    matches = []
    for ame_line in ame:
        for dji_line in dji:
            if ame_line["ts"] == dji_line["TimeStamp"]:
                print("Match found:")
                print("Anemometer:", ame_line)
                print("DJI:", dji_line)
                matches.append((ame_line, dji_line))
        print("Completed checking ame line:", ame_line["ts"])
    print(matches)
            
def main():
    parser = argparse.ArgumentParser(description="Script for comparing the wind vectors from the DJI drone and a mounted anemometer.")
    
    parser.add_argument("DJI", help="Path to DJI Flight Record")
    parser.add_argument("Anemometer", help="Path to Anemometer Data File")
    
    args = parser.parse_args()
    
    #print(args)
    # print(args.Anemometer)
    # print(args.DJI)

    ame = get_csv_file(args.Anemometer)
    dji = get_csv_file(args.DJI)

    print("ame:", ame[1]) # txt
    print("dji:", dji[1]) # csv
    # test_functions(ame)


    for line in ame:
        extra_needed_functions.parse_ame_line(line)
        
    print()
    print("ame after:", ame[1])
    print("dji:", dji[1])
    
    test(ame,dji)
    
    pass
    

if __name__ == "__main__":
    
    main()

    
    
    
    

# ask how to get direction from the two vectors (vector math)
# focus on direction of wind / no relative 

### WEATHER.windDirection, WEATHER.windSpeed
