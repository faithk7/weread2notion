from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import requests

from constants import WEREAD_NOTEBOOKS_URL
from logger import logger
from util import get_callout_block
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
    bookmark_list: List[Dict] = field(default_factory=list)
    summary: List[Dict] = field(default_factory=list)
    reviews: List[Dict] = field(default_factory=list)
    chapters: Dict = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict) -> "Book":
        book_data = data.get("book", data)  # Handle both nested and flat JSON
        return cls(
            bookId=book_data.get("bookId"),
            title=book_data.get("title"),
            author=book_data.get("author"),
            cover=book_data.get("cover"),
            sort=book_data.get("sort"),
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


def get_table_of_contents() -> Dict:
    """获取目录"""
    return {"type": "table_of_contents", "table_of_contents": {"color": "default"}}


def get_heading(level: int, content: str) -> Dict:
    if level == 1:
        heading = "heading_1"
    elif level == 2:
        heading = "heading_2"
    else:
        heading = "heading_3"
    return {
        "type": heading,
        heading: {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": content,
                    },
                }
            ],
            "color": "default",
            "is_toggleable": False,
        },
    }


def get_quote(content: str) -> Dict:
    return {
        "type": "quote",
        "quote": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": content},
                }
            ],
            "color": "default",
        },
    }


def get_children(
    chapter: Optional[Dict[int, Dict]], summary: List[Dict], bookmark_list: List[Dict]
) -> Tuple[List[Dict], Dict[int, Dict]]:
    children = []
    grandchild = {}

    if chapter is not None:
        children.append(get_table_of_contents())
        d = _group_bookmarks_by_chapter(bookmark_list)

        for key, value in d.items():
            if key in chapter:
                children.append(_add_chapter_heading(chapter, key))

            for i in value:
                callout = _create_callout(i)
                children.append(callout)

                if i.get("abstract"):
                    quote = get_quote(i.get("abstract"))
                    grandchild[len(children) - 1] = quote
    else:
        for data in bookmark_list:
            children.append(_create_callout(data))

    if summary:
        children.append(get_heading(1, "点评"))
        for i in summary:
            children.append(_create_summary_callout(i))

    logger.info(f"Children: {children}")
    logger.info(f"Grandchild: {grandchild}")
    return children, grandchild


def _group_bookmarks_by_chapter(bookmark_list: List[Dict]) -> Dict[int, List[Dict]]:
    d = {}
    for data in bookmark_list:
        chapterUid = data.get("chapterUid", 1)
        if chapterUid not in d:
            d[chapterUid] = []
        d[chapterUid].append(data)
    return d


def _add_chapter_heading(chapter: Dict[int, Dict], key: int) -> Dict:
    return get_heading(chapter[key].get("level"), chapter[key].get("title"))


def _create_callout(data: Dict) -> Dict:
    return get_callout_block(
        data.get("markText"),
        data.get("style"),
        data.get("colorStyle"),
        data.get("reviewId"),
    )


def _create_summary_callout(review: Dict) -> Dict:
    return get_callout_block(
        review.get("review").get("content"),
        review.get("style"),
        review.get("colorStyle"),
        review.get("review").get("reviewId"),
    )
