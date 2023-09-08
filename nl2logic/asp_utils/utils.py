import re
from ..config import nl2logic_config as config

UNIT_FACTOR = {
    # Numeric units
    "%" : 1000,
    # Time units (second)
    "초": 1,
    "분": 60,
    "시간": 60*60,
    "일": 60*60*24,
    "주": 60*60*24*7,
    "개월": 60*60*24*30,
    "년": 60*60*24*365,
    # Distance units (mm)
    "m": 1000,
    "km": 1000000,
    # Weight units (g)
    "g": 1,
    "kg": 1000,
    # etc.
    "차로": 1,
    "차선": 1,
    "원": 1,
    "도": 1000,
}

SCASP_PATH = config.scasp_path

def convert_numeric_string_to_int(input_string):
    pattern = r'^([-+]?\d{1,3}(?:,\d{3})*(\.\d+)?)|^([-+]?\d+(\.\d*)?)'
    match = re.match(pattern, input_string)
    
    if match:
        num_str = match.group()
        unit = input_string.replace(num_str, "")
        num = float(num_str.replace(",",""))
        if unit in UNIT_FACTOR:
            # print(num, unit)
            return int(num * UNIT_FACTOR[unit])
        else:
            return input_string
    else:
        return input_string