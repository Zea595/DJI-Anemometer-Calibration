from datetime import datetime
import argparse
import csv



def compare_time(DJI,ANE): #if DJI.time == ame.time: pass the speed and direction variables into the vector_math function.

        pass

def get_txt_file(file_path):
    with open(file_path, "r") as file: # assume the files are already cleaned
        data = file.readlines() 
        return data
    
def get_csv_file(self,file_path)
    with open(file_path, "r") as csvfile:
        data = csv.reader(csvfile)
        return dats

def parse_ame_line(self,text): #changes the datetime format to match the DJI drone data.

     pass

def vector_math(self,v1,v2):

     pass

def main():
    compare = Compare()
    
    parser = argparse.ArgumentParser(description="Script for comparing the wind vectors from the DJI drone and a mounted anemometer.")
    
    parser.add_argument("DJI", help="Path to DJI Flight Record")
    parser.add_argument("Anemometer", help="Path to Anemometer Data File")
    
    args = parser.parse_args()
    
    #print(args)
    # print(args.Anemometer)
    # print(args.DJI)
    
    ame = compare.get_txt_file(args.Anemometer)
    dji = compare.get_csv_file(args.DJI)


    print(ame)
   
    pass
    

if __name__ == "__main__":
    main()

    
    
    
    
    
    
    
# ask how to get direction from the two vectors (vector math)
# focus on direction of wind / no relative 

### WEATHER.windDirection, WEATHER.windSpeed
