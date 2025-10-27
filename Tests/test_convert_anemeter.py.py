"""
Unit + Integration tests for the convert_anemoeter.py - Ibjyot

Will cover the following:
1) timestamp parsing
2) file-level CSV conversion
3) line parsing
"""

import csv 

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