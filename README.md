# Helios easyControls 3.0 - Home Assistant (alexhaller)

## Description
HACS integration for Helios easyControls 3.0. Communication is working via WebSocket.

Supported Features:
- Sensors for temperature values (indoor, outside, supply, exhaust)
- Sensor for last time of filter change as well as one for the next change
- Sensor for current fan speed
- Sensor for relative humidity
- Sensor for CO2 sensor (if it is available in the KWL)
- Time entity to set the Intensive mode duration (it also shows the current set value)
- Number entity to set the Fan speed for AtHome, Away and Intensive (it also shows the current set value)
- Select entity to change the KWL Mode (it also shows the current set value)
- A switch Entity to turn the KWL ON/OFF

The integration uses the serial number of the device to assign uniq ids to the sensors.

## HACS Installation
- Via HACS custom repo
- The integration could be set up completely from UI. After the repo is under custom_components the integration should be found via HeliosEasyControls3_HA
- It only needs the ip address to find it

