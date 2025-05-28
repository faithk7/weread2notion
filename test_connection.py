import json
import socket
from typing import Optional

import requests
from requests.adapters import HTTPAdapter

# --- Configuration ---

# Replace with your specific book ID
# The example ID 3300035678 is from your URL
BOOK_ID = "3300035678"

# The API endpoint URL
API_URL = f"https://i.weread.qq.com/book/bookmarklist?bookId={BOOK_ID}"

# Paste your entire cookie string here.
# MAKE SURE these cookies are fresh from a logged-in browser session!
YOUR_WEREAD_COOKIES_STRING = """
pgv_pvid=1770045589982357; iip=0; _qimei_q36=; qq_domain_video_guid_verify=0ee49e4e06b066b5; wr_pf=0; suid=user_0_7e16e0c3f71e1; _qimei_h38=658748b28637b42af7215c8b0300000ae17b14; wr_localvid=0e1327c0814a66bd80e110d; wr_name=QK; wr_gender=1; logTrackKey=91802f9cee054ec0a8e7811b8ad63721; _qimei_uuid42=1911e0a192e100794f0a23ab1b384ce6f0c1572170; wr_avatar=https%3A%2F%2Fthirdwx.qlogo.cn%2Fmmopen%2Fvi_32%2FPiajxSqBRaEI2LiacfFzlrialqLegZujCtQF5NgHxHjDpiaRniaBomT9K1fIFRJWXAvxoTm1LT3n2S2CBCc9Y9ibdUBGmMqcI0LibUHhnF4JbU8aumvnVHplxBOBA%2F132; pac_uid=0_dXHSJB5zr2sDZ; wr_vid=346450904; wr_rt=web%40S5NgrsXbGL5keGwEn10_AL; wr_fp=892190693; _qimei_fingerprint=938d96448ee802afdbf66159ab68b44a; wr_gid=292290693; _clck=xoua66|1|fve|0; wr_skey=6C2QErXg
"""

# Headers to simulate a browser request
HEADERS = {
    "authority": "i.weread.qq.com",
    "method": "GET",
    "path": f"/book/bookmarklist?bookId={BOOK_ID}",
    "scheme": "https",
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "cache-control": "max-age=0",
    # "cookie": Handled separately below
    "dnt": "1",
    "priority": "u=0, i",
    "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    # Consider adding a Referer header if necessary, e.g., "referer": "https://weread.qq.com/"
}


# --- Helper function to parse cookie string into a dictionary ---
def parse_cookie_string(cookie_string: str) -> dict:
    """Parses a raw cookie string into a dictionary."""
    cookies = {}
    if not cookie_string:
        return cookies
    for cookie_pair in cookie_string.strip().split(";"):
        if cookie_pair.strip():
            parts = cookie_pair.strip().split("=", 1)
            if len(parts) == 2:
                key, value = parts
                cookies[key] = value
            elif len(parts) == 1:
                cookies[parts[0]] = ""
    return cookies


# --- Custom HTTP Adapter for Source IP Binding ---


class SourceAddressAdapter(HTTPAdapter):
    def __init__(self, source_address, **kwargs):
        self.source_address = source_address
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        # Pass the source_address to the pool manager
        pool_kwargs["source_address"] = self.source_address
        super().init_poolmanager(connections, maxsize, block, **pool_kwargs)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        # Pass the source_address when creating proxy managers
        proxy_kwargs["source_address"] = self.source_address
        return super().proxy_manager_for(proxy, **proxy_kwargs)


# --- Main Script Logic ---


def get_weread_bookmarks(
    book_id: str, cookie_string: str, source_ip: Optional[str] = None
):
    """
    Fetches bookmark list for a given book ID using provided cookies,
    optionally binding the request to a specific source IP.
    """

    url = f"https://i.weread.qq.com/book/bookmarklist?bookId={book_id}"

    headers = HEADERS.copy()
    headers["path"] = f"/book/bookmarklist?bookId={book_id}"
    headers["authority"] = "i.weread.qq.com"

    cookies_dict = parse_cookie_string(cookie_string)

    # Prepare the local_addr tuple if a source_ip is provided
    local_bind_address = (source_ip, 0) if source_ip else None

    with requests.Session() as session:
        if local_bind_address:
            print(f"Attempting to bind source IP to {local_bind_address[0]}")
            # Create and mount the custom adapter
            adapter = SourceAddressAdapter(local_bind_address)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
        else:
            print("No source IP specified, using default.")

        try:
            print(f"Making request to {url}")

            # Make the GET request
            response = session.get(
                url,
                headers=headers,
                cookies=cookies_dict,
                # Timeout is still a good idea
                timeout=15,  # Increased timeout slightly
            )

            # Check if the request was successful (status code 200)
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Successfully fetched data for book ID {book_id}")
                    return data
                except json.JSONDecodeError:
                    print(f"Error decoding JSON from response for book ID {book_id}.")
                    print(
                        "Response body (first 500 chars):",
                        (
                            response.text[:500] + "..."
                            if len(response.text) > 500
                            else response.text
                        ),
                    )
                    return None
            elif response.status_code in (401, 403):
                print(
                    f"Authentication failed for book ID {book_id}. Status Code: {response.status_code}"
                )
                print(
                    "Response:", response.text
                )  # This will likely contain the {"errcode":..., "errmsg":"登录超时"}
                print(
                    "Likely cause: Cookies are expired or invalid, or potentially an IP mismatch."
                )
                return None
            else:
                print(
                    f"Request failed for book ID {book_id}. Status Code: {response.status_code}"
                )
                print(
                    "Response body (first 500 chars):",
                    (
                        response.text[:500] + "..."
                        if len(response.text) > 500
                        else response.text
                    ),
                )
                return None

        except requests.exceptions.RequestException as e:
            # Check for socket errors specifically related to binding
            if isinstance(
                e.args[0], socket.error
            ) and "Cannot assign requested address" in str(e):
                print(
                    f"Error: Cannot bind to source IP {source_ip}. Is this IP address available on your local machine?"
                )
            else:
                print(
                    f"An error occurred during the request for book ID {book_id}: {e}"
                )
            return None


# --- Execute the script ---
if __name__ == "__main__":
    TARGET_SOURCE_IP = "50.114.155.148"  # Specify the IP address you want to use
    # TARGET_SOURCE_IP = None # Set to None to test without binding

    print(
        f"Attempting to fetch bookmarks for book ID: {BOOK_ID} using source IP {TARGET_SOURCE_IP or 'Default'}"
    )
    bookmark_data = get_weread_bookmarks(
        BOOK_ID, YOUR_WEREAD_COOKIES_STRING, source_ip=TARGET_SOURCE_IP
    )

    if bookmark_data:
        print(f"\n--- Bookmarks for Book ID {BOOK_ID} ---")
        print("Response keys:", bookmark_data.keys())
        # Inspect bookmark_data to find the list of bookmarks, e.g.:
        if (
            "updated" in bookmark_data
        ):  # Updated to check for 'updated' key based on previous context
            print(f"Found {len(bookmark_data['updated'])} bookmarks/updates.")
        # elif 'items' in bookmark_data:
        #     print(f"Found {len(bookmark_data['items'])} bookmarks.")
        else:
            print(
                "Could not find a typical bookmark list key ('updated' or 'items') in the response."
            )
            print(
                "Full response data sample:",
                (
                    json.dumps(bookmark_data, indent=2)[:500] + "..."
                    if len(json.dumps(bookmark_data, indent=2)) > 500
                    else json.dumps(bookmark_data, indent=2)
                ),
            )
        # You might get a different structure depending on the API response for this endpoint

    else:
        print("Failed to retrieve bookmark data.")
