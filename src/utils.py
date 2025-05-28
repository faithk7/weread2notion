from __future__ import annotations

import hashlib
import re
from datetime import datetime
from http.cookies import SimpleCookie
from typing import Dict, List, Optional, Tuple, TypeAlias

from pytz import timezone
from requests.cookies import RequestsCookieJar
from requests.utils import cookiejar_from_dict

from logger import logger

CookieDict: TypeAlias = Dict[str, str]


def transform_id(book_id: str) -> Tuple[str, List[str]]:
    """Transform book ID into hexadecimal representation.

    Args:
        book_id: The book identifier string.

    Returns:
        Tuple containing transformation code and list of transformed IDs.

    Raises:
        ValueError: If book_id is empty or invalid.
    """
    if not book_id:
        raise ValueError("Book ID cannot be empty")

    id_length = len(book_id)

    if re.match("^\d*$", book_id):
        hex_parts = [
            format(int(book_id[i : min(i + 9, id_length)]), "x")
            for i in range(0, id_length, 9)
        ]
        return "3", hex_parts

    hex_result = "".join(format(ord(char), "x") for char in book_id)
    return "4", [hex_result]


def calculate_book_str_id(book_id: str) -> str:
    """Calculate a unique string identifier for a book.

    Args:
        book_id: The original book identifier.

    Returns:
        A transformed string identifier.

    Raises:
        ValueError: If book_id is empty or invalid.
    """
    if not book_id:
        raise ValueError("Book ID cannot be empty")

    md5 = hashlib.md5(usedforsecurity=False)
    md5.update(book_id.encode("utf-8"))
    digest = md5.hexdigest()

    result = digest[0:3]
    code, transformed_ids = transform_id(book_id)
    result += code + "2" + digest[-2:]

    for i, transformed_id in enumerate(transformed_ids):
        hex_length_str = format(len(transformed_id), "x").zfill(2)
        result += hex_length_str + transformed_id
        if i < len(transformed_ids) - 1:
            result += "g"

    if len(result) < 20:
        result += digest[0 : 20 - len(result)]

    final_md5 = hashlib.md5(usedforsecurity=False)
    final_md5.update(result.encode("utf-8"))
    result += final_md5.hexdigest()[0:3]

    return result


def parse_cookie_string(cookie_string: str) -> Optional[RequestsCookieJar]:
    """Parse a cookie string into a RequestsCookieJar.

    Args:
        cookie_string: Raw cookie string from browser.

    Returns:
        RequestsCookieJar object or None if parsing fails.

    Raises:
        ValueError: If cookie_string is empty or malformed.
    """
    if not cookie_string:
        raise ValueError("Cookie string cannot be empty")

    try:
        cookie = SimpleCookie()
        cookie.load(cookie_string)
        cookies_dict = {key: morsel.value for key, morsel in cookie.items()}
        return cookiejar_from_dict(cookies_dict, cookiejar=None, overwrite=True)
    except Exception as e:
        logger.error(f"Failed to parse cookie string: {str(e)}")


def format_reading_time(reading_time: int) -> str:
    """Format reading time from seconds to human-readable string.

    Args:
        reading_time: Time in seconds.

    Returns:
        Formatted string with hours and minutes.
    """
    if reading_time < 0:
        raise ValueError("Reading time cannot be negative")

    hours = reading_time // 3600
    minutes = (reading_time % 3600) // 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}时")
    if minutes > 0:
        parts.append(f"{minutes}分")

    return "".join(parts)


def format_timestamp_for_notion(
    timestamp: Optional[int] = None, tz_name: str = "Asia/Shanghai"
) -> Dict:
    """Format a timestamp for Notion's date property.
    If no timestamp is provided, uses current time.

    Args:
        timestamp: Optional Unix timestamp to format. If None, uses current time.
        tz_name: The timezone name to use. Defaults to Asia/Shanghai.

    Returns:
        Dictionary formatted for Notion's date property.
    """
    if timestamp is None:
        date = datetime.now()
    else:
        date = datetime.fromtimestamp(timestamp)

    tz = timezone(tz_name)
    localized_date = date.astimezone(tz)

    return {
        "date": {
            "start": localized_date.strftime("%Y-%m-%d %H:%M:%S"),
            "time_zone": tz_name,
        }
    }
