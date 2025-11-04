import pandas as pd
import numpy as np
import sys
from pathlib import Path




def main():


    # === Configuration ===
    csv_file = Path(sys.argv[1])

    # === Step 1: Read CSV ===
    df = pd.read_csv(csv_file)

    # === Step 2: Compute vector magnitude and direction ===
    # Magnitude (speed): sqrt(U^2 + V^2)
    df["VectorMag"] = np.sqrt(df["U"]**2 + df["V"]**2)

    # Direction (meteorological convention: 0° = North, 90° = East)
    # arctan2 returns radians; convert to degrees and normalize 0–360
    df["VectorDir"] = (np.degrees(np.arctan2(df["V"], df["U"])) + 360) % 360

    # === Step 3: Overwrite the CSV ===
    df.to_csv(csv_file, index=False)



if __name__ == "__main__":
    main()