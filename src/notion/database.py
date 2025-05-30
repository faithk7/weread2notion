import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from notion_client import Client
from notion_client.errors import APIResponseError

from book import Book
from logger import logger
from notion.blocks import BlockDict
from notion.page import BookPage


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
                    logger.error(f"Error in function {func.__name__}: {e}")
                    raise
            return None

        return wrapper

    return decorator


class NotionDatabaseManager:
    """Handles all database-related operations in Notion"""

    def __init__(self, client: Client, database_id: str):
        self.client = client
        self.database_id = database_id

    def create_book_page(self, book: Book) -> Optional[str]:
        """Creates a new page for a book in the database"""
        logger.info(f"Creating page for book: {book.title} with ID: {book.bookId}")
        book_page = BookPage(book)
        properties = book_page.build_notion_property()
        icon = {"type": "external", "external": {"url": book.cover}}

        return self._create_page(properties, icon)

    def check_and_delete(self, bookId: str) -> None:
        """检查是否已经插入过 如果已经插入了就删除"""
        filter = self._create_filter("BookId", bookId)

        def query_op():
            return self.client.databases.query(
                database_id=self.database_id, filter=filter
            )

        response = self._make_request(query_op)
        if response:
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
        return self._extract_latest_sort(response) if response else 0

    def _extract_latest_sort(self, response: Dict) -> int:
        if response and len(response.get("results", [])) == 1:
            sort_property = response["results"][0].get("properties", {}).get("Sort", {})
            latest_sort = sort_property.get("number", 0)
            logger.info(f"Latest sort found: {latest_sort}")
            return latest_sort
        logger.info("No previous sort value found in Notion database.")
        return 0

    def _create_page(self, properties: Dict, icon: Dict) -> Optional[str]:
        parent = {"database_id": self.database_id, "type": "database_id"}

        def create_op():
            return self.client.pages.create(
                parent=parent, icon=icon, properties=properties
            )

        response = self._make_request(create_op)
        return response["id"] if response else None

    def _create_filter(self, property_name: str, value: str) -> Dict:
        return {"property": property_name, "rich_text": {"equals": value}}

    def _delete_existing_entries(self, response: Dict) -> None:
        count = 0
        for result in response.get("results", []):
            block_id = result.get("id")
            if block_id:

                def delete_op(block_id=block_id):
                    return self.client.blocks.delete(block_id=block_id)

                if self._make_request(delete_op):
                    count += 1
        if count > 0:
            logger.info(f"Deleted {count} existing Notion page(s).")

    def add_children(
        self, page_id: str, children: List[BlockDict]
    ) -> Optional[List[Dict]]:
        results = []
        chunk_size = 50

        for i in range(0, len(children), chunk_size):
            chunk = children[i : i + chunk_size]

            def append_op(chunk=chunk):
                return self.client.blocks.children.append(
                    block_id=page_id, children=chunk
                )

            if i > 0:
                time.sleep(0.5)

            response = self._make_request(append_op)
            if response and "results" in response:
                results.extend(response["results"])
            elif not response:
                logger.error(
                    f"Failed to add child chunk for page {page_id}. No response."
                )
                return None

        if (
            len(results) > 0
            and len(results) % chunk_size == 0
            or len(results) == len(children)
        ):
            return results
        elif len(children) == 0:
            return []
        else:
            logger.warning(
                f"Potentially incomplete children addition for page {page_id}. Expected {len(children)}, got {len(results)} results."
            )
            return None

    def add_grandchildren(
        self, parent_blocks: List[Dict], grandchildren: Dict[int, BlockDict]
    ) -> None:
        for block_index, block_content in grandchildren.items():
            if block_index >= len(parent_blocks):
                logger.warning(
                    f"Grandchild index {block_index} out of bounds for parent_blocks list."
                )
                continue
            block_id = parent_blocks[block_index].get("id")
            if not block_id:
                logger.warning(
                    f"Parent block at index {block_index} has no ID for grandchild addition."
                )
                continue

            def append_op(block_id=block_id, block_content=block_content):
                return self.client.blocks.children.append(
                    block_id=block_id, children=[block_content]
                )

            self._make_request(append_op)

    @retry()
    def _make_request(self, operation: Callable[[], Any]) -> Any:
        """Generic method to make Notion API requests with retry logic"""
        try:
            return operation()
        except APIResponseError as e:
            logger.error(f"Notion API Error during operation {operation.__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during operation {operation.__name__}: {e}")
            return None
