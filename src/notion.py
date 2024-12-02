import time
from datetime import datetime
from typing import Dict, List, Optional

import requests
from notion_client import Client

from book import Book, get_read_info
from logger import logger
from util import calculate_book_str_id


class NotionManager:
    def __init__(self, notion_token: str, database_id: str):
        self.client = Client(auth=notion_token)
        self.database_id = database_id

    def check_and_delete(self, book_id: str) -> None:
        """检查是否已经插入过 如果已经插入了就删除"""
        time.sleep(1)
        filter = {"property": "book_id", "rich_text": {"equals": book_id}}
        response = self.client.databases.query(
            database_id=self.database_id, filter=filter
        )
        for result in response["results"]:
            time.sleep(1)
            self.client.blocks.delete(block_id=result["id"])

    def insert_to_notion(self, book: Book, session: requests.Session) -> str:
        """插入到notion"""
        time.sleep(1)

        logger.info(f"Inserting book: {book.title} with ID: {book.book_id}")

        parent = {"database_id": self.database_id, "type": "database_id"}
        properties = {
            "BookName": {"title": [{"type": "text", "text": {"content": book.title}}]},
            "book_id": {
                "rich_text": [{"type": "text", "text": {"content": book.book_id}}]
            },
            "ISBN": {"rich_text": [{"type": "text", "text": {"content": book.isbn}}]},
            "URL": {
                "url": f"https://weread.qq.com/web/reader/{calculate_book_str_id(book.book_id)}"
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
        }
        read_info = get_read_info(session, book_id=book.book_id)
        if read_info is not None:
            markedStatus = read_info.get("markedStatus", 0)
            readingTime = read_info.get("readingTime", 0)
            format_time = ""
            hour = readingTime // 3600
            if hour > 0:
                format_time += f"{hour}时"
            minutes = readingTime % 3600 // 60
            if minutes > 0:
                format_time += f"{minutes}分"
            properties["Status"] = {
                "select": {"name": "读完" if markedStatus == 4 else "在读"}
            }
            properties["ReadingTime"] = {
                "rich_text": [{"type": "text", "text": {"content": format_time}}]
            }
            if "finishedDate" in read_info:
                properties["Date"] = {
                    "date": {
                        "start": datetime.utcfromtimestamp(
                            read_info.get("finishedDate")
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                        "time_zone": "Asia/Shanghai",
                    }
                }

        icon = {"type": "external", "external": {"url": book.cover}}
        # notion api 限制100个block
        response = self.client.pages.create(
            parent=parent, icon=icon, properties=properties
        )
        id = response["id"]
        return id

    def add_children(self, id: str, children: List[Dict]) -> Optional[List[Dict]]:
        results = []

        for i in range(0, len(children) // 100 + 1):
            time.sleep(1)  # NOTE: TEMP FIX
            response = self.client.blocks.children.append(
                block_id=id, children=children[i * 100 : (i + 1) * 100]
            )
            results.extend(response.get("results"))

        return results if len(results) == len(children) else None

    def add_grandchild(self, grandchild: Dict[int, Dict], results: List[Dict]) -> None:
        for key, value in grandchild.items():
            time.sleep(1)
            id = results[key].get("id")
            self.client.blocks.children.append(block_id=id, children=[value])

    def get_sort(self) -> int:
        """获取database中的最新时间"""
        filter = {"property": "Sort", "number": {"is_not_empty": True}}
        sorts = [
            {
                "property": "Sort",
                "direction": "descending",
            }
        ]
        response = self.client.databases.query(
            database_id=self.database_id, filter=filter, sorts=sorts, page_size=1
        )
        if len(response.get("results")) == 1:
            logger.info(
                f"Latest sort: {response.get('results')[0].get('properties').get('Sort').get('number')}"
            )
            return (
                response.get("results")[0].get("properties").get("Sort").get("number")
            )

        return 0
