import time
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict

from notion_client import Client
from notion_client.errors import APIResponseError
from pytz import timezone

from book import Book
from logger import logger
from utils import (
    calculate_book_str_id,
    format_reading_time,
    format_timestamp_for_notion,
)


def retry(max_retries: int = 2, initial_delay: float = 1.0):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for _ in range(max_retries):
                try:
                    time.sleep(delay)  # Always wait before making a request
                    return func(*args, **kwargs)
                except APIResponseError as e:
                    logger.error(f"Error: {e}")
                    raise
            return None

        return wrapper

    return decorator


class NotionDatabaseManager:
    """Handles all database-related operations in Notion"""

    def __init__(self, client: Client, database_id: str):
        self.client = client
        self.database_id = database_id

    def create_book_page(self, book: Book) -> str:
        """Creates a new page for a book in the database"""
        logger.info(f"Creating page for book: {book.title} with ID: {book.bookId}")

        properties = build_properties(book)
        icon = {"type": "external", "external": {"url": book.cover}}

        return self._create_page(properties, icon)

    def check_and_delete(self, bookId: str) -> None:
        """检查是否已经插入过 如果已经插入了就删除"""
        filter = self._create_filter("BookId", bookId)

        def retrieve_op():
            return self.client.databases.retrieve(self.database_id)

        def query_op():
            return self.client.databases.query(
                database_id=self.database_id, filter=filter
            )

        logger.info(f"Database info: {self._make_request(retrieve_op)}")
        response = self._make_request(query_op)
        self._delete_existing_entries(response)

    def get_latest_sort(self) -> int:
        """获取database中的最新时间"""
        filter = {"property": "Sort", "number": {"is_not_empty": True}}
        sorts = [{"property": "Sort", "direction": "descending"}]

        def query_op():
            return self.client.databases.query(
                database_id=self.database_id, filter=filter, sorts=sorts, page_size=1
            )

        response = self._make_request(query_op)
        return self._extract_latest_sort(response)

    def _extract_latest_sort(self, response: Dict) -> int:
        if len(response.get("results")) == 1:
            logger.info(
                f"Latest sort: {response.get('results')[0].get('properties').get('Sort').get('number')}"
            )
            return (
                response.get("results")[0].get("properties").get("Sort").get("number")
            )
        return 0

    def _create_page(self, properties: Dict, icon: Dict) -> str:
        parent = {"database_id": self.database_id, "type": "database_id"}

        def create_op():
            return self.client.pages.create(
                parent=parent, icon=icon, properties=properties
            )

        response = self._make_request(create_op)
        return response["id"]

    def _create_filter(self, property_name: str, value: str) -> Dict:
        return {"property": property_name, "rich_text": {"equals": value}}

    def _delete_existing_entries(self, response: Dict) -> None:
        for result in response["results"]:

            def delete_op(block_id=result["id"]):  # Bind block_id to closure
                return self.client.blocks.delete(block_id=block_id)

            self._make_request(delete_op)

    @retry()
    def _make_request(self, operation: Callable[[], Any]) -> Any:
        """Generic method to make Notion API requests with retry logic"""
        return operation()


def build_properties(book: Book) -> Dict:
    """Creates a dictionary of Notion properties from a book"""
    properties = {
        "BookName": {"title": [{"type": "text", "text": {"content": book.title}}]},
        "BookId": {"rich_text": [{"type": "text", "text": {"content": book.bookId}}]},
        "ISBN": {"rich_text": [{"type": "text", "text": {"content": book.isbn}}]},
        "URL": {
            "url": f"https://weread.qq.com/web/reader/{calculate_book_str_id(book.bookId)}"
        },
        "Author": {"rich_text": [{"type": "text", "text": {"content": book.author}}]},
        "Sort": {"number": book.sort},
        "Rating": {"number": book.rating},
        "Cover": {
            "files": [
                {
                    "type": "external",
                    "name": "Cover",
                    "external": {"url": book.cover},
                }
            ]
        },
        "Category": {"select": {"name": book.category if book.category else "未分类"}},
    }

    # Try to add UpdatedTime if the property exists in the database
    try:
        properties["UpdatedTime"] = format_timestamp_for_notion()
    except Exception as e:
        logger.warning(f"Could not add UpdatedTime property: {e}")

    if book.status:
        properties["Status"] = {"select": {"name": book.status}}

    if book.reading_time:
        format_time = format_reading_time(book.reading_time)
        properties["ReadingTime"] = {
            "rich_text": [{"type": "text", "text": {"content": format_time}}]
        }

    if book.finished_date:
        properties["FinishedDate"] = format_timestamp_for_notion(book.finished_date)

    return properties
