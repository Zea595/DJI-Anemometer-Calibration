import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os, glob
from datetime import datetime

# ======================================================
# CONFIGURATION
# ======================================================
DATA_DIR = "/data"
CLEANED_DIR = os.path.join(DATA_DIR, "Cleaned")
PLOT_DIR = "/app/static/plots"


# ======================================================
# AUTO-DETECT FILES
# ======================================================
def get_latest(patterns, required=True):
    """Return the newest file matching any of the patterns (list or string)."""
    if isinstance(patterns, str):
        patterns = [patterns]

    matches = []
    for pattern in patterns:
        matches.extend(glob.glob(pattern))

    if not matches:
        if required:
            raise FileNotFoundError(f"No files found matching any of: {patterns}")
        return None

    return max(matches, key=os.path.getmtime)


# ======================================================
# LOAD DATA
# ======================================================
def load_data():
    drone_path = get_latest([
        os.path.join(CLEANED_DIR, "CLEAN_*.csv"),
        os.path.join(DATA_DIR, "CLEAN_*.csv"),
    ])
    anemo_path = get_latest(os.path.join(DATA_DIR, "Anemometer_data_*.csv"))

    print(f"[INFO] Using Drone CSV: {drone_path}")
    print(f"[INFO] Using Anemometer CSV: {anemo_path}")

    drone = pd.read_csv(drone_path, low_memory=False)
    anemo = pd.read_csv(anemo_path, low_memory=False)

    # Normalize timestamps
    drone["Drone_Time(UTC+RFC3339)"] = pd.to_datetime(
        drone["Drone_Time(UTC+RFC3339)"], utc=True, errors="coerce"
    )
    drone["Drone_Time(PST)_Clean"] = pd.to_datetime(drone["Drone_Time(PST)_Clean"], errors="coerce")
    drone["Drone_Time(PST)_Clean"] = drone["Drone_Time(PST)_Clean"].dt.tz_convert(None)

    anemo["ts"] = pd.to_datetime(anemo["ts"], utc=True, errors="coerce")
    

    # Drop invalid timestamps
    drone = drone.dropna(subset=["Drone_Time(UTC+RFC3339)"])
    anemo = anemo.dropna(subset=["ts"])

    # Ensure numeric conversion for all relevant columns
    numeric_cols = [
        "VectorMag", "VectorDir", "U", "V",
        "BatteryPct", "BattV", "BattC",
        "WindSpeed(m/s)", "WEATHER.windDirection"
    ]
    for df_name, df in [("Drone", drone), ("Anemometer", anemo)]:
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    # Debug info for ranges
    # print("\n[DEBUG] Drone time range:")
    # print(" ", drone["Drone_Time(UTC+RFC3339)"].min(), "→", drone["Drone_Time(UTC+RFC3339)"].max())
    # print("[DEBUG] Anemometer time range:")
    # print(" ", anemo["ts"].min(), "→", anemo["ts"].max())

    return drone, anemo, drone_path


# ======================================================
# COMPARE WIND DATA
# ======================================================
def compare_vectors(drone, anemo, tolerance_seconds=10, direction_tolerance=15):
    """
    Compare wind data between drone and anemometer.
    Tolerance defaults to ±5 minutes to catch minor clock offsets.
    """
    print(f"[INFO] Merging datasets with ±{tolerance_seconds}s tolerance...")

    # Time-based merge
    merged = pd.merge_asof(
        drone.sort_values("Drone_Time(UTC+RFC3339)"),
        anemo.sort_values("ts"),
        left_on="Drone_Time(UTC+RFC3339)",
        right_on="ts",
        direction="nearest",
        tolerance=pd.Timedelta(seconds=tolerance_seconds),
    )

    # derive local time from UTC
    merged["Drone_Time_PST_for_plot"] = (
        merged["Drone_Time(UTC+RFC3339)"]
        .dt.tz_convert("America/Los_Angeles")  # convert UTC -> PST/PDT
        .dt.tz_localize(None)                  # drop tzinfo but keep local clock time
    )

    # Drop rows where direction difference > tolerance
    merged = merged[
        merged.apply(
            lambda r: min(
                abs(r["VectorDir"] - r["Drone_Direction"]),
                360 - abs(r["VectorDir"] - r["Drone_Direction"])
            ) <= direction_tolerance,
            axis=1,
        )
    ].reset_index(drop=True)

    if "VectorMag" not in merged.columns or "WindSpeed(m/s)" not in merged.columns:
        raise KeyError("[ERROR] Missing one or more required columns: 'VectorMag', 'WindSpeed(m/s)'")

    # Convert again to be sure (handles merge dtype promotion)
    for col in ["VectorMag", "VectorDir", "WindSpeed(m/s)", "WEATHER.windDirection"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")

    merged = merged.dropna(subset=["VectorMag", "WindSpeed(m/s)"], how="any")

    print(f"[INFO] Matched {len(merged)} rows after merge.")
    if len(merged) == 0:
        print("[WARN] No overlapping timestamps found — check timezone or timestamp offset.")
        return merged

    # Compute metrics
    merged["speed_diff"] = merged["WindSpeed(m/s)"] - merged["VectorMag"]
    merged["speed_pct_diff"] = (
        (merged["speed_diff"].abs() / merged["VectorMag"].replace(0, np.nan)) * 100
    )
    merged["dir_diff"] = (
        (merged["WEATHER.windDirection"] - merged["VectorDir"]).abs() % 360
    )

    return merged


# ======================================================
# PLOTTING
# ======================================================
def generate_plots():
    drone, anemo, used_path = load_data()
    merged = compare_vectors(drone, anemo)

    os.makedirs(PLOT_DIR, exist_ok=True)

    if merged.empty:
        print("[ERROR] No merged data available — skipping plot generation.")
        return used_path

    # ---------------------------------
    # BASIC STATS FOR % SPEED DIFFERENCE
    # ---------------------------------
    # Ensure column exists and drop NaNs just in case
    if "speed_pct_diff" in merged.columns:
        spd = merged["speed_pct_diff"].dropna()

        if not spd.empty:
            mean_diff = spd.mean()
            median_diff = spd.median()
            # mode() can return multiple values; take the first if it exists
            mode_series = spd.mode()
            mode_diff = mode_series.iloc[0] if not mode_series.empty else None

            print("[STATS] Speed % difference:")
            print(f"  Mean   : {mean_diff:.2f}%")
            print(f"  Median : {median_diff:.2f}%")
            if mode_diff is not None:
                print(f"  Mode   : {mode_diff:.2f}%")
            else:
                print("  Mode   : (no unique mode)")
        else:
            mean_diff = median_diff = mode_diff = None
            print("[STATS] speed_pct_diff column exists but is empty after dropping NaNs.")
    else:
        mean_diff = median_diff = mode_diff = None
        print("[STATS] speed_pct_diff column not found in merged data.")

    # --- 1. Wind Speed Comparison ---
    plt.figure(figsize=(10, 5))
    plt.scatter(
        merged["Drone_Time_PST_for_plot"],
        merged["WindSpeed(m/s)"],
        label="Drone Wind Speed (m/s)",
        s=2,           # marker size
        color="tab:blue",
    )
    plt.scatter(
        merged["Drone_Time_PST_for_plot"],
        merged["VectorMag"],
        label="Anemometer Wind Speed (m/s)",
        s=2,
        color="tab:orange",
    )
        # Limit X-axis to min/max range rather than showing every timestamp
    plt.gca().set_xlim(
        merged["Drone_Time_PST_for_plot"].min(),
        merged["Drone_Time_PST_for_plot"].max()
    )

    plt.legend()
    plt.xlabel("Timestamp (PST)")
    plt.ylabel("Speed (m/s)")
    plt.title("Wind Speed Comparison: Drone vs Anemometer (±5s timestamp tolerance, ±10 degrees)")
    plt.tight_layout()
    plt.savefig(f"{PLOT_DIR}/wind_comparison.png", dpi=150)
    plt.close()

    # --- 2. Percentage Difference ---
    plt.figure(figsize=(10, 5))
    plt.scatter(
        merged["Drone_Time_PST_for_plot"],
        merged["speed_pct_diff"],
        color="orange",
        s=2,
    )
    plt.xlabel("Timestamp (UTC)")
    plt.ylabel("Speed Difference (%)")
    plt.title("Percentage Difference in Wind Speed (Drone vs Anemometer)")
    plt.axhline(0, color="gray", linestyle="--", linewidth=1)

    # --- 4. Drone vs Anemometer Direction Scatter Plot ---
    plt.figure(figsize=(10, 5))

    # Scatter plot
    plt.scatter(
        merged["VectorDir"],           # Anemometer direction
        merged["Drone_Direction"], # Drone direction
        s=1,
        alpha=0.6,
        color="royalblue",
        label="Samples"
    )

        # Limit X-axis to min/max range rather than showing every timestamp


    # Set cardinal direction ticks for the drone (Y-axis)
    cardinal_degrees = [0, 45, 90, 135, 180, 225, 270, 315]
    cardinal_labels  = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

    plt.yticks(cardinal_degrees, cardinal_labels)
    plt.ylim(0, 360)   # keep proper range


    # 1:1 perfect accuracy line
    plt.plot([0, 360], [0, 360], 'k--', label="Perfect agreement")

    # ±15° tolerance band
    plt.plot([0, 360], [15, 375], 'r--', alpha=0.7, label="±15° tolerance")
    plt.plot([0, 360], [-15, 345], 'r--', alpha=0.7)

    plt.xlim(0, 360)
    plt.ylim(0, 360)
    plt.xlabel("Anemometer Direction (°)")
    plt.ylabel("Drone Direction (°)")
    plt.title("Drone vs Anemometer Wind Direction Comparison")

    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{PLOT_DIR}/direction_accuracy_scatter.png", dpi=150)
    plt.close()



    # Add stats as text box on the plot if we have them
    stats_lines = []
    if mean_diff is not None:
        stats_lines.append(f"Mean:   {mean_diff:.2f}%")
        stats_lines.append(f"Median: {median_diff:.2f}%")
        if mode_diff is not None:
            stats_lines.append(f"Mode:   {mode_diff:.2f}%")
    if stats_lines:
        stats_text = "\n".join(stats_lines)
        # In axes coordinates (0.02 from left, 0.98 from top)
        plt.gca().text(
            0.02,
            0.98,
            stats_text,
            transform=plt.gca().transAxes,
            fontsize=9,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.7),
        )

    plt.tight_layout()
    plt.savefig(f"{PLOT_DIR}/speed_difference.png", dpi=150)
    plt.close()

    # --- 3. Direction Difference ---
    plt.figure(figsize=(10, 5))
    plt.scatter(
        merged["Drone_Time_PST_for_plot"],
        merged["dir_diff"],
        color="purple",
        s=10,
    )

        # Limit X-axis to min/max range rather than showing every timestamp
    plt.gca().set_xlim(
        merged["Drone_Time_PST_for_plot"].min(),
        merged["Drone_Time_PST_for_plot"].max()
    )

    plt.xlabel("Timestamp (PST)")
    plt.ylabel("Direction Difference (°)")
    plt.title("Wind Direction Difference (Drone vs Anemometer)")
    plt.axhline(0, color="gray", linestyle="--", linewidth=1)
    plt.tight_layout()
    plt.savefig(f"{PLOT_DIR}/direction_difference.png", dpi=150)
    plt.close()

    print(f"[INFO] Saved plots to {PLOT_DIR}/")
    return used_path




# ======================================================
# CLI ENTRYPOINT
# ======================================================
if __name__ == "__main__":
    used = generate_plots()
    print(f"✅ Analytics generated using {used}")
