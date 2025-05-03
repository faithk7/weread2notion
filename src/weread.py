from typing import Any, Dict, List, Optional

import requests

from constants import (
    WEREAD_BOOK_INFO,
    WEREAD_BOOKMARKLIST_URL,
    WEREAD_CHAPTER_INFO,
    WEREAD_NOTEBOOKS_URL,
    WEREAD_READ_INFO_URL,
    WEREAD_REVIEW_LIST_URL,
    WEREAD_URL,
)
from logger import logger
from utils import parse_cookie_string


class WeReadClient:
    def __init__(self, weread_cookie: str):
        self.session = requests.Session()
        self.session.cookies = parse_cookie_string(weread_cookie)
        self.is_valid = False
        self.connect()
        assert (
            self.is_valid
        ), "WeRead client initialization failed. Check cookie validity."

    def connect(self) -> None:
        """Attempts to connect to WeRead and validate the session/cookie."""
        try:
            # Use _fetch for the connection test
            response_data = self._fetch(
                WEREAD_NOTEBOOKS_URL, log_prefix="connection test"
            )
            if response_data is not None:
                self.is_valid = True
                logger.info("WeRead client connected successfully.")
            else:
                self.is_valid = False
                # Specific error logged in _fetch
        except (
            Exception
        ) as e:  # Catch potential unexpected errors during connect logic itself
            self.is_valid = False
            logger.error(f"An unexpected error occurred during WeRead connection: {e}")

    def _fetch(
        self,
        url: str,
        params: Optional[Dict] = None,
        method: str = "GET",
        log_prefix: str = "request",
        expected_keys: Optional[List[str]] = None,
    ) -> Optional[Any]:
        """Performs an HTTP request and handles common errors."""
        try:
            response = self.session.request(method, url, params=params, timeout=10)
            response_json = response.json()
            # Optional basic validation for expected keys
            if expected_keys:
                if not all(key in response_json for key in expected_keys):
                    logger.warning(
                        f"Missing expected keys {expected_keys} in {log_prefix} response from {url}"
                    )
                    # Decide if this should be a hard failure or just a warning
                    # return None # Uncomment if missing keys should cause failure
            return response_json
        except requests.exceptions.Timeout:
            logger.error(f"Failed to fetch {log_prefix}: Request timed out.")
            return None
        except requests.exceptions.JSONDecodeError:
            logger.error(
                f"Failed to fetch {log_prefix}: Could not decode JSON response. Response: {response.text[:500]}"
            )
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {log_prefix}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {log_prefix}: {e}")
            return None

    def get_bookinfo(self, book_id: str) -> Optional[Dict]:
        return self._fetch(
            WEREAD_BOOK_INFO,
            params={"bookId": book_id},
            log_prefix=f"book info for {book_id}",
        )

    def fetch_reviews(self, book_id: str) -> List[Dict]:
        data = self._fetch(
            WEREAD_REVIEW_LIST_URL,
            params=dict(bookId=book_id, listType=11, mine=1, syncKey=0),
            log_prefix=f"reviews for {book_id}",
        )
        return data.get("reviews", []) if data else []

    def fetch_bookmark_list(self, book_id: str) -> List[Dict]:
        data = self._fetch(
            WEREAD_BOOKMARKLIST_URL,
            params=dict(bookId=book_id),
            log_prefix=f"bookmarks for {book_id}",
        )
        if not data:
            return []

        # The original logic checked for 'updated' key presence specifically
        if "updated" not in data:
            logger.warning(f"No 'updated' field in bookmark data for {book_id}")
            return (
                []
            )  # Return empty list if 'updated' key is missing, consistent with original logic

        return data.get("updated", [])  # Safely get 'updated', defaulting to []

    def fetch_chapter_info(self, book_id: str) -> Optional[List[Dict]]:
        """Fetches chapter information (list of chapter dicts) for a given book ID."""
        data = self._fetch(
            WEREAD_CHAPTER_INFO,
            params={"bookId": book_id},
            log_prefix=f"chapter info for book {book_id}",
            expected_keys=["chapters"],  # Expect 'chapters' key
        )

        if data is None:
            return None  # Error handled by _fetch

        chapters_data = data.get("chapters", [])
        if not isinstance(chapters_data, list):
            logger.error(
                f"Unexpected format for chapters data for book {book_id}: {chapters_data}"
            )
            return None

        return chapters_data

    def fetch_read_info(self, book_id: str) -> Optional[Dict]:
        return self._fetch(
            WEREAD_READ_INFO_URL,
            params=dict(
                bookId=book_id, readingDetail=1, readingBookIndex=1, finishedDate=1
            ),
            log_prefix=f"read info for {book_id}",
        )

    def get_notebooklist(self) -> List[Dict]:
        """获取笔记本列表"""
        data = self._fetch(WEREAD_NOTEBOOKS_URL, log_prefix="notebook list")
        if not data:
            return []

        books = data.get("books", [])
        if not books:
            logger.warning("No books found in notebook list")
            return []

        logger.info(f"Found {len(books)} books in notebook list")
        # Sort by the 'sort' key, default to a large number if missing to place them last
        books.sort(key=lambda x: x.get("sort", float("inf")))
        return books
