from typing import Dict, List, Optional

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
        self.session.get(WEREAD_URL)  # Initialize session

    def fetch_book_info(self, book_id: str) -> Optional[Dict]:
        try:
            r = self.session.get(WEREAD_BOOK_INFO, params={"bookId": book_id})
            if not r.ok:
                logger.error(
                    f"Failed to fetch book info for {book_id}: {r.status_code}"
                )
                return None
            return r.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching book info for {book_id}: {e}")
            return None

    def fetch_reviews(self, book_id: str) -> Optional[List[Dict]]:
        try:
            params = dict(bookId=book_id, listType=11, mine=1, syncKey=0)
            r = self.session.get(WEREAD_REVIEW_LIST_URL, params=params)
            if not r.ok:
                logger.error(f"Failed to fetch reviews for {book_id}: {r.status_code}")
                return None
            data = r.json()
            return data.get("reviews", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching reviews for {book_id}: {e}")
            return []

    def fetch_bookmark_list(self, book_id: str) -> Optional[List[Dict]]:
        try:
            params = dict(bookId=book_id)
            r = self.session.get(WEREAD_BOOKMARKLIST_URL, params=params)
            if not r.ok:
                logger.error(
                    f"Failed to fetch bookmarks for {book_id}: {r.status_code}"
                )
                return None
            data = r.json()
            if "updated" not in data:
                logger.warning(f"No 'updated' field in bookmark data for {book_id}")
                return []
            return data.get("updated")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching bookmarks for {book_id}: {e}")
            return []

    def fetch_chapter_info(self, book_id: str) -> Optional[List[Dict]]:
        """Fetches chapter information (list of chapter dicts) for a given book ID."""
        try:
            params = {"bookId": book_id}
            r = self.session.get(WEREAD_CHAPTER_INFO, params=params)
            r.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            data = r.json()
            # According to the user-provided structure, chapters are under the 'chapters' key
            chapters_data = data.get("chapters", [])
            if not isinstance(chapters_data, list):
                logger.error(
                    f"Unexpected format for chapters data for book {book_id}: {chapters_data}"
                )
                return None

            # Return the raw list of chapter dictionaries
            return chapters_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching chapter info for book {book_id}: {e}")
            # Handle potential JSON decoding errors specifically if needed
            try:
                error_data = r.json()
                logger.error(f"Server response: {error_data}")
            except requests.exceptions.JSONDecodeError:
                logger.error(
                    f"Could not decode JSON response. Response text: {r.text[:500]}"
                )  # Log first 500 chars
            return None  # Return None on error to indicate failure

    def fetch_read_info(self, book_id: str) -> Optional[Dict]:
        try:
            params = dict(
                bookId=book_id, readingDetail=1, readingBookIndex=1, finishedDate=1
            )
            r = self.session.get(WEREAD_READ_INFO_URL, params=params)
            if not r.ok:
                logger.error(
                    f"Failed to fetch read info for {book_id}: {r.status_code}"
                )
                return None
            return r.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching read info for {book_id}: {e}")
            return None

    def get_notebooklist(self) -> List[Dict]:
        """获取笔记本列表"""
        try:
            r = self.session.get(WEREAD_NOTEBOOKS_URL)
            if not r.ok:
                logger.error(f"Failed to fetch notebook list: {r.status_code}")
                return []

            data = r.json()
            books = data.get("books", [])

            if not books:
                logger.warning("No books found in notebook list")
                return []

            logger.info(f"Found {len(books)} books in notebook list")
            books.sort(key=lambda x: x["sort"])
            return books
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching notebook list: {e}")
            return []
