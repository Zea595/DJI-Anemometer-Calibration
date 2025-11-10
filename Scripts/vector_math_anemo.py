from datetime import datetime
import argparse
import csv
import math
import numpy as np



def get_csv_file(file_path):
    with open(file_path, "r") as csvfile:
        filedata = csv.DictReader(csvfile) # reads the csv into a dictionary format

        # Convert the filedata to a list of dictionaries to access the data after the file has been closed
        data = []
        for row in filedata:
            data.append(row)
            
        return data

def vector_math(s1,s2):  # s1 = u, s2 = v
    u = s1 #U component
    v = s2 #V component
    
    if u == 0 and v == 0:
        return 0,0  # No wind
    else:
        speed = np.sqrt(u**2 + v**2) # a^2 + b^2 = c^2 NOTE calculating for c
        
        direction = (-math.degrees(math.atan2(v, u)) + 270) % 360

        return speed, direction




class extra_needed_functions:
    @staticmethod
    def txt_to_csv(file_path):
        with open(file_path, "r") as file: # opens the text file
            data = file.readlines()
            with open(file_path + ".csv", "w") as f:
                f.writelines(data) # writes the text file data into a csv file for easier reading
    
    # @staticmethod NOTE: This function is used to cleanse the datetime format, but since the datetime cleansing has been fixed, it is no longer in use.
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
    
    ame = get_csv_file(args.Anemometer)    
    
    # test(ame,dji)
    
    math_data = []
    for ame_line in ame:
        try: # Check for valid float conversion
            float(ame_line["U"])
            float(ame_line["V"])
        except (ValueError, TypeError):
            print("Invalid data in line:", ame_line)
            math_data.append((None, None))
            continue
        
        # Perform vector math
        math_data.append(vector_math(float(ame_line["U"]), float(ame_line["V"])))
        

    with open("./Data/Cleaned/vector_output.csv", "w", newline="") as csvfile: # Output the results to a new CSV file
        fieldnames = ["U", "V", "Speed", "Direction"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for i, ame_line in enumerate(ame):
            try: # Check for valid float conversion
                u = float(ame_line["U"])
                v = float(ame_line["V"])
            except (ValueError, TypeError): # Handle invalid data
                u = ame_line["U"]
                v = ame_line["V"]
                continue
            speed, direction = math_data[i]
            writer.writerow({"U": u, "V": v, "Speed": speed, "Direction": direction}) 
    pass

if __name__ == "__main__":
    main()
