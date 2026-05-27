import re

##wyciaganie wartosci z pojedynczej linii odebranej z esp
TELEMETRY_REGEX = {
    "counter": re.compile(r"(?:Sent\s+packet:\s*|#)(\d+)"),
    "temp": re.compile(r"Temp:\s*(-?\d+(?:\.\d+)?)"),
    "humi": re.compile(r"Humidity:\s*(-?\d+(?:\.\d+)?)"),
    "pressure": re.compile(r"Pressure:\s*(-?\d+(?:\.\d+)?)"),
}


def parse_telemetry_line(line: str) -> dict[str, int | float | None]:
    counter_match = TELEMETRY_REGEX["counter"].search(line)
    temp_match = TELEMETRY_REGEX["temp"].search(line)
    humi_match = TELEMETRY_REGEX["humi"].search(line)
    pressure_match = TELEMETRY_REGEX["pressure"].search(line)

    return {
        "counter": int(counter_match.group(1)) if counter_match else None,
        "temp": float(temp_match.group(1)) if temp_match else None,
        "humi": float(humi_match.group(1)) if humi_match else None,
        "pressure": float(pressure_match.group(1)) if pressure_match else None,
    }
