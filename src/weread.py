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
from utils import parse_cookie_string


class WeReadClient:
    def __init__(self, weread_cookie: str):
        self.session = requests.Session()
        self.session.cookies = parse_cookie_string(weread_cookie)
        self.session.get(WEREAD_URL)  # Initialize session

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

    def fetch_read_info(self, book_id: str) -> Optional[Dict]:
        params = dict(
            bookId=book_id, readingDetail=1, readingBookIndex=1, finishedDate=1
        )
        r = self.session.get(WEREAD_READ_INFO_URL, params=params)
        return r.json() if r.ok else None


def get_notebooklist(session: requests.Session) -> Optional[List[Dict]]:
    """获取笔记本列表"""
    r = session.get(WEREAD_NOTEBOOKS_URL)
    if r.ok:
        data = r.json()
        books = data.get("books")
        print("len(books)", len(books))
        books.sort(key=lambda x: x["sort"])
        return books
    else:
        print(r.text)
    return None
