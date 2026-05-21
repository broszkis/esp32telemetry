import re


TELEMETRY_REGEX = {
    # Obsługuje np.:
    # "Sent packet: 15"
    # "Received! #15 | Temp: ..."
    # "#15 | Temp: ..."
    "counter": re.compile(r"(?:Sent\s+packet:\s*|#)(\d+)"),
    "temp": re.compile(r"Temp:\s*(-?\d+(?:\.\d+)?)"),
    "humi": re.compile(r"Humidity:\s*(-?\d+(?:\.\d+)?)"),
    "pressure": re.compile(r"Pressure:\s*(-?\d+(?:\.\d+)?)")
}


def parse_telemetry_line(line):
    c_match = TELEMETRY_REGEX["counter"].search(line)
    t_match = TELEMETRY_REGEX["temp"].search(line)
    h_match = TELEMETRY_REGEX["humi"].search(line)
    p_match = TELEMETRY_REGEX["pressure"].search(line)

    return {
        "counter": int(c_match.group(1)) if c_match else None,
        "temp": float(t_match.group(1)) if t_match else None,
        "humi": float(h_match.group(1)) if h_match else None,
        "pressure": float(p_match.group(1)) if p_match else None
    }
