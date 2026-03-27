def dataToCelsius(data: bytearray, offsetPosition: int) -> float:
    """Convert raw data to Celsius temperature."""
    temperature = data[offsetPosition * 2] * 256 + data[offsetPosition * 2 + 1]
    temperature = temperature / 100 - 273.15
    temperature = round(temperature, 1)
    return temperature
