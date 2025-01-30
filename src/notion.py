import time
from datetime import datetime
from typing import Dict, List, Optional

from notion_client import Client
from notion_client.errors import APIResponseError

from book import Book
from logger import logger
from util import calculate_book_str_id, format_reading_time


class NotionManager:
    def __init__(self, notion_token: str, database_id: str):
        self.client = Client(
            auth=notion_token,
        )
        self.database_id = database_id

    def check_and_delete(self, bookId: str) -> None:
        """检查是否已经插入过 如果已经插入了就删除"""
        filter = self._create_filter("BookId", bookId)
        logger.info(
            f"Database info: {self.client.databases.retrieve(self.database_id)}"
        )
        response = self.client.databases.query(
            database_id=self.database_id, filter=filter
        )
        self._delete_existing_entries(response)

    def insert_to_notion(self, book: Book, max_retries: int = 1) -> str:
        """插入到notion with retry logic"""
        logger.info(f"Inserting book: {book.title} with ID: {book.bookId}")

        parent = {"database_id": self.database_id, "type": "database_id"}
        properties = self._create_properties(book)
        icon = {"type": "external", "external": {"url": book.cover}}

        for attempt in range(max_retries):
            try:
                response = self.client.pages.create(
                    parent=parent, icon=icon, properties=properties
                )
                return response["id"]
            except APIResponseError as e:
                if "Conflict" in str(e) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.warning(
                        f"Conflict occurred while saving {book.title}. "
                        f"Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                raise  # Re-raise the exception if we've exhausted retries or it's not a conflict error

    def add_children(self, id: str, children: List[Dict]) -> Optional[List[Dict]]:
        results = []
        for i in range(0, len(children) // 100 + 1):
            response = self.client.blocks.children.append(
                block_id=id, children=children[i * 100 : (i + 1) * 100]
            )
            results.extend(response.get("results"))
        return results if len(results) == len(children) else None

    def add_grandchild(self, grandchild: Dict[int, Dict], results: List[Dict]) -> None:
        for key, value in grandchild.items():
            id = results[key].get("id")
            self.client.blocks.children.append(block_id=id, children=[value])

    def get_latest_sort(self) -> int:
        """获取database中的最新时间"""
        filter = {"property": "Sort", "number": {"is_not_empty": True}}
        sorts = [{"property": "Sort", "direction": "descending"}]
        response = self.client.databases.query(
            database_id=self.database_id, filter=filter, sorts=sorts, page_size=1
        )
        return self._extract_latest_sort(response)

    def _create_filter(self, property_name: str, value: str) -> Dict:
        return {"property": property_name, "rich_text": {"equals": value}}

    def _delete_existing_entries(self, response: Dict) -> None:
        for result in response["results"]:
            self.client.blocks.delete(block_id=result["id"])

    def _create_properties(self, book: Book) -> Dict:
        properties = {
            "BookName": {"title": [{"type": "text", "text": {"content": book.title}}]},
            "BookId": {
                "rich_text": [{"type": "text", "text": {"content": book.bookId}}]
            },
            "ISBN": {"rich_text": [{"type": "text", "text": {"content": book.isbn}}]},
            "URL": {
                "url": f"https://weread.qq.com/web/reader/{calculate_book_str_id(book.bookId)}"
            },
            "Author": {
                "rich_text": [{"type": "text", "text": {"content": book.author}}]
            },
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
            "Category": {
                "select": {"name": book.category if book.category else "未分类"}
            },
        }

        if book.status:
            properties["Status"] = {"select": {"name": book.status}}

        if book.reading_time:
            format_time = format_reading_time(book.reading_time)
            properties["ReadingTime"] = {
                "rich_text": [{"type": "text", "text": {"content": format_time}}]
            }

        if book.finished_date:
            properties["Date"] = {
                "date": {
                    "start": datetime.utcfromtimestamp(book.finished_date).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "time_zone": "Asia/Shanghai",
                }
            }

        return properties

    def _extract_latest_sort(self, response: Dict) -> int:
        if len(response.get("results")) == 1:
            logger.info(
                f"Latest sort: {response.get('results')[0].get('properties').get('Sort').get('number')}"
            )
            return (
                response.get("results")[0].get("properties").get("Sort").get("number")
            )
        return 0
