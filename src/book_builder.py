import logging
from typing import Dict, List, Optional

from book import Book  # Import Book from src/book.py
from weread import WeReadClient

logger = logging.getLogger(__name__)


class BookBuilder:
    def __init__(self, client: WeReadClient):
        # Initialize only with the client
        self.client = client
        # Internal state for fetched data, reset per build
        self._info: Optional[Dict] = None
        self._reviews_raw: Optional[List[Dict]] = None
        self._bookmarks_raw: Optional[List[Dict]] = None
        self._chapters_raw: Optional[List[Dict]] = None
        self._read_info: Optional[Dict] = None
        # The book object being built, specific to a single build call
        self.book: Optional[Book] = None

    def build(self, data: dict) -> Optional[Book]:
        """Constructs the book object with fetched data."""
        # Reset internal state for this build
        self._info = None
        self._reviews_raw = None
        self._bookmarks_raw = None
        self._chapters_raw = None
        self._read_info = None

        # Create the base book object for this build
        self.book = self._create_book_from_json(data)
        if not self.book or not self.book.bookId:
            logger.error("Failed to create base book object from data.")
            return None

        # Fetch and process data for this book
        try:
            self.fetch_all()
            self._process_book_info()
            self._process_reviews()
            self._process_bookmarks()
            self._process_chapters()
            self._process_read_info()
            final_book = self.book
        except Exception as e:
            logger.error(
                f"Error building book {self.book.bookId if self.book else 'unknown'}: {e}"
            )
            final_book = None  # Ensure we don't return a partially built book on error
        finally:
            # Clean up the book instance for this build cycle
            self.book = None

        return final_book

    def _create_book_from_json(self, data: dict) -> Optional[Book]:
        """Creates a base Book object from JSON data."""
        book_data = data.get("book", data)  # Handle both nested and flat JSON
        bookId = book_data.get("bookId")
        if not bookId:
            logger.error("Missing bookId in input data")
            return None

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
            bookId=bookId,
            title=book_data.get("title"),
            author=book_data.get("author"),
            cover=book_data.get("cover"),
            sort=book_data.get("sort"),
            category=category,
        )

    def fetch_book_info(self) -> "BookBuilder":
        if self.book and self.book.bookId:
            self._info = self.client.get_bookinfo(self.book.bookId)
        return self

    def fetch_reviews(self) -> "BookBuilder":
        if self.book and self.book.bookId:
            # TODO: check where went wrong with reviews fetching
            # self._reviews_raw = self.client.get_reviews(self.book.bookId)
            pass  # Keep commented out until fixed
        return self

    def fetch_bookmarks(self) -> "BookBuilder":
        if self.book and self.book.bookId:
            self._bookmarks_raw = self.client.get_bookmarks(self.book.bookId)
        return self

    def fetch_chapters(self) -> "BookBuilder":
        if self.book and self.book.bookId:
            self._chapters_raw = self.client.get_chapters(self.book.bookId)
        return self

    def fetch_read_info(self) -> "BookBuilder":
        if self.book and self.book.bookId:
            self._read_info = self.client.get_readinfo(self.book.bookId)
        return self

    def fetch_all(self) -> "BookBuilder":
        # Ensure book exists before fetching
        if not self.book or not self.book.bookId:
            logger.error("Cannot fetch data without a valid book instance.")
            return self
        self.fetch_book_info()
        self.fetch_reviews()
        self.fetch_bookmarks()
        self.fetch_chapters()
        self.fetch_read_info()
        return self

    def _process_book_info(self):
        if self.book and self._info:
            self.book.isbn = self._info.get("isbn", "")
            self.book.rating = self._info.get("newRating", 0) / 1000

    def _process_reviews(self):
        if self.book and self._reviews_raw:
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
        if self.book and self._bookmarks_raw:
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
        if self.book and self._chapters_raw:
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
        if self.book and self._read_info:
            data = self._read_info
            marked_status = data.get("markedStatus", 0)
            self.book.status = "读完" if marked_status == 4 else "在读"
            self.book.reading_time = data.get("readingTime", 0)
            self.book.finished_date = data.get("finishedDate")
