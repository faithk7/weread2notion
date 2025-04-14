from dataclasses import dataclass, field
from typing import Dict, List, Optional

import requests

from constants import WEREAD_NOTEBOOKS_URL
from weread import WeReadClient


@dataclass
class Book:
    bookId: str
    title: str
    author: str
    cover: str
    sort: int
    isbn: str = field(default="")
    rating: float = field(default=0.0)
    status: str = field(default="")
    reading_time: int = field(default=0)
    finished_date: Optional[int] = field(default=None)
    category: str = field(default="")
    bookmark_list: List[Dict] = field(default_factory=list)
    summary: List[Dict] = field(default_factory=list)
    reviews: List[Dict] = field(default_factory=list)
    chapters: Dict = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict) -> "Book":
        book_data = data.get("book", data)  # Handle both nested and flat JSON

        # Extract category from categories array with a default value
        categories = book_data.get("categories", [])
        category = (
            categories[0].get(
                "title", "未分类"
            )  # Use "未分类" as default if title is missing
            if categories
            else "未分类"  # Use "未分类" if no categories
        )

        return cls(
            bookId=book_data.get("bookId"),
            title=book_data.get("title"),
            author=book_data.get("author"),
            cover=book_data.get("cover"),
            sort=book_data.get("sort"),
            category=category,
        )

    def update_book_info(self, data: Dict):
        self.isbn = data["isbn"]
        self.rating = data["newRating"] / 1000

    def process_reviews(self, reviews: List[Dict]):
        self.summary = list(filter(lambda x: x.get("review").get("type") == 4, reviews))
        self.reviews = list(filter(lambda x: x.get("review").get("type") == 1, reviews))
        self.reviews = list(map(lambda x: x.get("review"), self.reviews))
        self.reviews = list(
            map(lambda x: {**x, "markText": x.pop("content")}, self.reviews)
        )

    def update_bookmark_list(self, updated: List[Dict]):
        self.bookmark_list = sorted(
            updated,
            key=lambda x: (
                x.get("chapterUid", 1),
                int(
                    x.get("range", "0-0").split("-")[0]
                ),  # be defensive, if range is empty, use 0-0
            ),
        )

    def update_chapters(self, data: List[Dict]):
        if len(data) == 1 and "updated" in data[0]:
            update = data[0]["updated"]
            self.chapters = {item["chapterUid"]: item for item in update}

    def update_read_info(self, data: Dict):
        """Updates reading status and time from API data"""
        marked_status = data.get("markedStatus", 0)
        self.status = "读完" if marked_status == 4 else "在读"
        self.reading_time = data.get("readingTime", 0)
        self.finished_date = data.get("finishedDate")


class BookService:
    def __init__(self, client: WeReadClient):
        self.client = client

    def load_book_details(self, book: Book) -> Book:
        """Loads all book details from the API"""
        # Load book info
        if info := self.client.fetch_book_info(book.bookId):
            book.update_book_info(info)

        # Load reviews and summary
        if reviews := self.client.fetch_reviews(book.bookId):
            book.process_reviews(reviews)

        # Load bookmarks
        if bookmarks := self.client.fetch_bookmark_list(book.bookId):
            book.update_bookmark_list(bookmarks)

        # Load chapters
        if chapters := self.client.fetch_chapter_info(book.bookId):
            book.update_chapters(chapters)

        # Load read info
        if read_info := self.client.fetch_read_info(book.bookId):
            book.update_read_info(read_info)

        return book


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
