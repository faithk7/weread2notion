from abc import ABC, abstractmethod
from typing import Dict

from book import Book

# Import necessary utility functions used by _build_notion_property
from utils import (
    calculate_book_str_id,
    format_reading_time,
    format_timestamp_for_notion,
)


class Page(ABC):
    @abstractmethod
    def build_notion_property(self) -> Dict:
        """Abstract method to build the Notion page properties dictionary."""
        pass


class BookPage(Page):
    def __init__(self, book: Book):
        self.book = book

    def build_notion_property(self) -> Dict:
        """Builds and returns the Notion properties dictionary for the book."""
        return self._build_notion_property()

    def _build_notion_property(self) -> Dict:
        """Creates a dictionary of Notion properties from the book instance."""
        return {
            "BookName": {
                "title": [{"type": "text", "text": {"content": self.book.title}}]
            },
            "BookId": {
                "rich_text": [{"type": "text", "text": {"content": self.book.bookId}}]
            },
            "ISBN": {
                "rich_text": [{"type": "text", "text": {"content": self.book.isbn}}]
            },
            "URL": {
                "url": f"https://weread.qq.com/web/reader/{calculate_book_str_id(self.book.bookId)}"
            },
            "Author": {
                "rich_text": [{"type": "text", "text": {"content": self.book.author}}]
            },
            "Sort": {"number": self.book.sort},
            "Rating": {"number": self.book.rating},
            "Cover": {
                "files": [
                    {
                        "type": "external",
                        "name": "Cover",
                        "external": {"url": self.book.cover},
                    }
                ]
            },
            "Category": {
                "select": {
                    "name": self.book.category if self.book.category else "未分类"
                }
            },
            "Status": {
                "select": {"name": self.book.status if self.book.status else ""}
            },
            "ReadingTime": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": (
                                format_reading_time(self.book.reading_time)
                                if self.book.reading_time
                                else ""
                            )
                        },
                    }
                ]
            },
            "FinishedDate": (
                format_timestamp_for_notion(self.book.finished_date)
                if self.book.finished_date
                else {"date": None}
            ),
            "UpdatedTime": format_timestamp_for_notion(),
        }
