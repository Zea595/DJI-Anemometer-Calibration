# DJI Anemometer Calibration Repository

#### This repository will contain the resources and tools needed to process both DJI drone logs and Trisonica Anemometer logs into a common format.

#### Scripts

- **Clean_and_Timestamp.py**
  - PURPOSE: to convert DJI drone flightlog time into RFC3339 format timestamps
  - USAGE: python .Clean_and_Timestamp.py <flightlog.csv>
