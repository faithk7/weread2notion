import hashlib
import re
from http.cookies import SimpleCookie
from typing import List, Tuple

from requests.utils import cookiejar_from_dict


def transform_id(book_id: str) -> Tuple[str, List[str]]:
    id_length = len(book_id)

    # Check if the book_id is purely numeric
    if re.match("^\d*$", book_id):
        hex_parts = []
        # Convert each 9-digit segment to hexadecimal
        for i in range(0, id_length, 9):
            segment = book_id[i : min(i + 9, id_length)]
            hex_parts.append(format(int(segment), "x"))
        return "3", hex_parts

    # Convert each character to its hexadecimal representation
    hex_result = "".join(format(ord(char), "x") for char in book_id)
    return "4", [hex_result]


def calculate_book_str_id(book_id: str) -> str:
    # Create an MD5 hash of the book_id
    md5 = hashlib.md5(usedforsecurity=False)
    md5.update(book_id.encode("utf-8"))
    digest = md5.hexdigest()

    # Start the result with the first 3 characters of the digest
    result = digest[0:3]

    # Transform the book_id and append the transformation code and last 2 digest characters
    code, transformed_ids = transform_id(book_id)
    result += code + "2" + digest[-2:]

    # Append each transformed ID with its length in hexadecimal
    for transformed_id in transformed_ids:
        hex_length_str = format(len(transformed_id), "x").zfill(2)
        result += hex_length_str + transformed_id

        # Add a separator if not the last element
        if transformed_id != transformed_ids[-1]:
            result += "g"

    # Ensure the result is at least 20 characters long
    if len(result) < 20:
        result += digest[0 : 20 - len(result)]

    # Append the first 3 characters of a new MD5 hash of the result
    md5 = hashlib.md5(usedforsecurity=False)
    md5.update(result.encode("utf-8"))
    result += md5.hexdigest()[0:3]

    return result


def parse_cookie_string(cookie_string: str):
    cookie = SimpleCookie()
    cookie.load(cookie_string)
    cookies_dict = {}
    cookiejar = None
    for key, morsel in cookie.items():
        cookies_dict[key] = morsel.value
        cookiejar = cookiejar_from_dict(cookies_dict, cookiejar=None, overwrite=True)
    return cookiejar


def get_callout_block(content: str, style: int, colorStyle: int, reviewId: str) -> dict:
    # 根据不同的划线样式设置不同的emoji 直线type=0 背景颜色是1 波浪线是2
    emoji = "🌟"
    if style == 0:
        emoji = "💡"
    elif style == 1:
        emoji = "⭐"
    # 如果reviewId不是空说明是笔记
    if reviewId is not None:
        emoji = "✍️"
    color = "default"
    # 根据划线颜色设置文字的颜色
    if colorStyle == 1:
        color = "red"
    elif colorStyle == 2:
        color = "purple"
    elif colorStyle == 3:
        color = "blue"
    elif colorStyle == 4:
        color = "green"
    elif colorStyle == 5:
        color = "yellow"
    return {
        "type": "callout",
        "callout": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": content,
                    },
                }
            ],
            "icon": {"emoji": emoji},
            "color": color,
        },
    }


def format_reading_time(reading_time: int) -> str:
    """Format reading time from seconds to a string with hours and minutes."""
    format_time = ""
    hour = reading_time // 3600
    if hour > 0:
        format_time += f"{hour}时"
    minutes = reading_time % 3600 // 60
    if minutes > 0:
        format_time += f"{minutes}分"
    return format_time
