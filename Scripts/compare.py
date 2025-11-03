from datetime import datetime
import argparse
import csv
import math

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

def vector_math(s1,s2):  # s1 = u, s2 = v
    u = s1 #U component
    v = s2 #V component
    
    if u == 0 and v == 0:
        return 0,0  # No wind
    else:
        speed = (u**2 + v**2)**0.5  
        
        direction = (180 / 3.14159) * -1 * (math.atan2(v, u)) + 270  
        
        direction = direction % 360  
        return speed, direction

    pass



class extra_needed_functions:
    @staticmethod
    def txt_to_csv(file_path):
        with open(file_path, "r") as file: # opens the text file
            data = file.readlines()
            with open(file_path + ".csv", "w") as f:
                f.writelines(data) # writes the text file data into a csv file for easier reading
    
    # @staticmethod            
    # def parse_ame_line(text): #changes the datetime format to match the DJI drone data.
    #     if '.' in text["ts"]: # check for milliseconds
    #         dt = datetime.strptime(text["ts"], "%Y-%m-%dT%H:%M:%S.%fZ")
    #     else:
    #         dt = datetime.strptime(text["ts"], "%Y-%m-%dT%H:%M:%SZ")
            
    #     text["ts"] = dt.strftime("%Y-%m-%d:%H:%M:%S") # change the format to match the DJI time format


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
    
    

    # print("ame:", ame[1]) # txt
    # print("dji:", dji[1]) # csv
    
    # print(ame[1]["ts"])
    # print(dji[1]["TimeStamp"])
    # # test_functions(ame)


    # # for line in ame:
    # #     extra_needed_functions.parse_ame_line(line)
        
    # print()
    # print("ame after:", ame[1])
    # print("dji:", dji[1])
    
    # test(ame,dji)
    
    math_data = []
    for ame_line in ame:
        try:
            float(ame_line["U"])
            float(ame_line["V"])
        except (ValueError, TypeError):
            print("Invalid data in line:", ame_line)
            math_data.append((None, None))
            continue
        try:
            math_data.append(vector_math(float(ame_line["U"]), float(ame_line["V"])))
        except ValueError:
            print("Error processing line:", ame_line)

    with open("./Data/Cleaned/vector_output.csv", "w", newline="") as csvfile:
        fieldnames = ["U", "V", "Speed", "Direction"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for i, ame_line in enumerate(ame):
            try:    
                u = float(ame_line["U"])
                v = float(ame_line["V"])
            except (ValueError, TypeError):
                u = ame_line["U"]
                v = ame_line["V"]
                continue
            speed, direction = math_data[i]
            writer.writerow({"U": u, "V": v, "Speed": speed, "Direction": direction})

    pass
    

if __name__ == "__main__":
    
    main()

    
    
    
    

# ask how to get direction from the two vectors (vector math)
# focus on direction of wind / no relative 

### WEATHER.windDirection, WEATHER.windSpeed
