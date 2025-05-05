import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from weread import WeReadClient

logger = logging.getLogger(__name__)


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
    bookmark_count: int = field(default=0)


class BookBuilder:
    def __init__(self, client: WeReadClient, data: dict):
        self.client = client
        self.book = self._create_book_from_json(data)
        self._info: Optional[Dict] = None
        self._reviews_raw: Optional[List[Dict]] = None
        self._bookmarks_raw: Optional[List[Dict]] = None
        self._chapters_raw: Optional[List[Dict]] = None
        self._read_info: Optional[Dict] = None

    @staticmethod
    def _create_book_from_json(data: dict) -> "Book":
        """Creates a base Book object from JSON data."""
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

        return Book(
            bookId=book_data.get("bookId"),
            title=book_data.get("title"),
            author=book_data.get("author"),
            cover=book_data.get("cover"),
            sort=book_data.get("sort"),
            category=category,
        )

    def fetch_book_info(self) -> "BookBuilder":
        self._info = self.client.get_bookinfo(self.book.bookId)
        return self

    def fetch_reviews(self) -> "BookBuilder":
        # TODO: check where went wrong with reviews fetching
        # self._reviews_raw = self.client.get_reviews(self.book.bookId)
        pass  # Keep commented out until fixed
        return self

    def fetch_bookmarks(self) -> "BookBuilder":
        self._bookmarks_raw = self.client.get_bookmarks(self.book.bookId)
        return self

    def fetch_chapters(self) -> "BookBuilder":
        self._chapters_raw = self.client.get_chapters(self.book.bookId)
        return self

    def fetch_read_info(self) -> "BookBuilder":
        self._read_info = self.client.get_readinfo(self.book.bookId)
        return self

    def fetch_all(self) -> "BookBuilder":
        self.fetch_book_info()
        self.fetch_reviews()
        self.fetch_bookmarks()
        self.fetch_chapters()
        self.fetch_read_info()
        return self

    def _process_book_info(self):
        if self._info:
            self.book.isbn = self._info.get("isbn", "")
            self.book.rating = self._info.get("newRating", 0) / 1000

    def _process_reviews(self):
        if self._reviews_raw:
            reviews_list = self._reviews_raw
            self.book.summary = list(
                filter(lambda x: x.get("review", {}).get("type") == 4, reviews_list)
            )
            self.book.reviews = list(
                filter(lambda x: x.get("review", {}).get("type") == 1, reviews_list)
            )
            self.book.reviews = list(map(lambda x: x.get("review"), self.book.reviews))
            self.book.reviews = list(
                map(
                    lambda x: {**x, "markText": x.pop("content", "")}, self.book.reviews
                )
            )

    def _process_bookmarks(self):
        if self._bookmarks_raw:
            updated = self._bookmarks_raw
            self.book.bookmark_list = sorted(
                updated,
                key=lambda x: (
                    x.get("chapterUid", 1),
                    int(x.get("range", "0-0").split("-")[0]),
                ),
            )
            self.book.bookmark_count = len(self.book.bookmark_list)

    def _process_chapters(self):
        if self._chapters_raw:
            chapters_list = self._chapters_raw
            self.book.chapters = {
                chapter.get("chapterUid"): chapter
                for chapter in chapters_list
                if chapter.get("chapterUid") is not None
            }
            if not self.book.chapters:
                logger.warning(
                    f"No valid chapter data found for book {self.book.bookId}."
                )

    def _process_read_info(self):
        if self._read_info:
            data = self._read_info
            marked_status = data.get("markedStatus", 0)
            self.book.status = "读完" if marked_status == 4 else "在读"
            self.book.reading_time = data.get("readingTime", 0)
            self.book.finished_date = data.get("finishedDate")

    def build(self) -> Book:
        """Constructs the book object with fetched data."""
        self._process_book_info()
        self._process_reviews()
        self._process_bookmarks()
        self._process_chapters()
        self._process_read_info()
        return self.book
