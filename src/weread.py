from typing import Dict, List, Optional

import requests

from constants import (
    WEREAD_BOOK_INFO,
    WEREAD_BOOKMARKLIST_URL,
    WEREAD_CHAPTER_INFO,
    WEREAD_REVIEW_LIST_URL,
)


class WeReadClient:
    def __init__(self, session: requests.Session):
        self.session = session

    def fetch_book_info(self, book_id: str) -> Optional[Dict]:
        r = self.session.get(WEREAD_BOOK_INFO, params={"bookId": book_id})
        return r.json() if r.ok else None

    def fetch_reviews(self, book_id: str) -> Optional[List[Dict]]:
        params = dict(bookId=book_id, listType=11, mine=1, syncKey=0)
        r = self.session.get(WEREAD_REVIEW_LIST_URL, params=params)
        return r.json().get("reviews") if r.ok else None

    def fetch_bookmark_list(self, book_id: str) -> Optional[List[Dict]]:
        params = dict(bookId=book_id)
        r = self.session.get(WEREAD_BOOKMARKLIST_URL, params=params)
        return r.json().get("updated") if r.ok else None

    def fetch_chapter_info(self, book_id: str) -> Optional[List[Dict]]:
        body = {"bookIds": [book_id], "synckeys": [0], "teenmode": 0}
        r = self.session.post(WEREAD_CHAPTER_INFO, json=body)
        return r.json().get("data", []) if r.ok else None
