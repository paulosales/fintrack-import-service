from datetime import datetime


def parse_datetime(date_str: str, time_str: str) -> str:
    dt = datetime.strptime(f"{date_str} {time_str}", "%m/%d/%Y %I:%M %p")
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_datetime_br(date_str: str, time_str: str = "12:00 PM") -> str:
    dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %I:%M %p")
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_date_iso(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%Y-%m-%d 00:00:00")
