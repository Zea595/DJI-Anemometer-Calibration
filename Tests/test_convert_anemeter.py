"""
Unit + Integration tests for the convert_anemoeter.py - Ibjyot

Will cover the following:
1) timestamp parsing
2) file-level CSV conversion
3) line parsing
"""

import csv
import pytest
from pathlib import Path

# import the functions from the script.

from Scripts.convert_anemometer import parse_timestamp, parse_line, convert_file

# 1. Timestamp Tests

def test_parse_timestamp_with_milliseconds():
    """
    Checks the timestamp to ensure it is converted properly from the raw format:
    YY:MM:DD:HH:MM:SS.mmm
    Expected output: RFC3339 UTC time (e.g., 2023-11-02T00:39:22.316Z)
    """
    got = parse_timestamp("23:11:01:17:39:22.316", "America/Vancouver")

    assert got == "2023-11-02T00:39:22.316Z"

def test_parse_timestamp_rejects_bad_format():
    """
    A malformed timestamp (like 'bad:data:string') should not crash the script.
    The function should handle it and return None.
    """
    assert parse_timestamp("bad:data:string", "America/Vancouver") is None

# test for other timezones

def test_parse_timestamp_other_timezone():
    got = parse_timestamp("23:11:01:17:39:22.316", "UTC")
    # 17:39 local UTC should remain 17:39Z
    assert got == "2023-11-01T17:39:22.316Z"

# empty strings test

def test_parse_timestamp_empty_input():
    assert parse_timestamp("", "America/Vancouver") is None
    
# 2. Import Tests

def test_convert_file_empty_file_errors(tmp_path):
    """
    Empty input should not silently succeed. Expect a controlled failure.
    """
    raw = tmp_path / "empty.txt"
    raw.write_text("", encoding="utf-8")  # same as _write()
    out = tmp_path / "out.csv"

    with pytest.raises(SystemExit):  # expected failure type
        convert_file(raw, out, "America/Vancouver", keep_sn=True)

def test_csv_header_is_correct(tmp_path):
    raw_file = Path("Data/Raw/Anemometer_data_23-11-01-17-39-22.txt")
    out = tmp_path / "header.csv"

    convert_file(raw_file, out, "America/Vancouver", keep_sn=True)

    first_line = out.read_text().splitlines()[0]
    assert first_line == "raw_ts,ts,sn1,sn2,U,V,T,BatteryPct,BattV,BattC"