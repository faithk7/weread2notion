import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeAlias

from notion_client import Client
from notion_client.errors import APIResponseError

from book import Book
from logger import logger
from util import calculate_book_str_id, format_reading_time

# Constants for styling
STYLE_EMOJIS = {
    0: "💡",  # Direct line
    1: "⭐",  # Background color
    2: "🌟",  # Wavy line
    None: "✍️",  # Note
}

COLOR_STYLES = {
    1: "red",
    2: "purple",
    3: "blue",
    4: "green",
    5: "yellow",
    None: "default",
}

CalloutBlock: TypeAlias = Dict[str, any]


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


class NotionManager:
    def __init__(self, notion_token: str, database_id: str):
        self.client = Client(
            auth=notion_token,
        )
        self.database_id = database_id

    @retry()
    def _make_request(self, operation: Callable[[], Any]) -> Any:
        """Generic method to make Notion API requests with retry logic"""
        return operation()

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

    def insert_to_notion(self, book: Book, max_retries: int = 1) -> str:
        """插入到notion with retry logic"""
        logger.info(f"Inserting book: {book.title} with ID: {book.bookId}")

        parent = {"database_id": self.database_id, "type": "database_id"}
        properties = self._create_properties(book)
        icon = {"type": "external", "external": {"url": book.cover}}

        def create_op():
            return self.client.pages.create(
                parent=parent, icon=icon, properties=properties
            )

        response = self._make_request(create_op)
        return response["id"]

    def add_children(self, id: str, children: List[Dict]) -> Optional[List[Dict]]:
        results = []
        for i in range(0, len(children) // 100 + 1):
            chunk = children[i * 100 : (i + 1) * 100]

            def append_op(chunk=chunk):  # Bind chunk to closure
                return self.client.blocks.children.append(block_id=id, children=chunk)

            response = self._make_request(append_op)
            results.extend(response.get("results"))
        return results if len(results) == len(children) else None

    def add_grandchild(self, grandchild: Dict[int, Dict], results: List[Dict]) -> None:
        for key, value in grandchild.items():
            block_id = results[key].get("id")

            def append_op(block_id=block_id, value=value):  # Bind variables to closure
                return self.client.blocks.children.append(
                    block_id=block_id, children=[value]
                )

            self._make_request(append_op)

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

    def _create_filter(self, property_name: str, value: str) -> Dict:
        return {"property": property_name, "rich_text": {"equals": value}}

    def _delete_existing_entries(self, response: Dict) -> None:
        for result in response["results"]:

            def delete_op(block_id=result["id"]):  # Bind block_id to closure
                return self.client.blocks.delete(block_id=block_id)

            self._make_request(delete_op)

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


def get_callout_block(
    content: str,
    style: Optional[int],
    color_style: Optional[int],
    review_id: Optional[str],
) -> CalloutBlock:
    """Create a callout block with specified styling.

    Args:
        content: The text content of the callout.
        style: Style indicator (0=line, 1=background, 2=wavy).
        color_style: Color indicator (1-5 for different colors).
        review_id: Review identifier, if this is a note.

    Returns:
        Dictionary containing the callout block configuration.
    """
    emoji = STYLE_EMOJIS.get(None if review_id is not None else style, "🌟")
    color = COLOR_STYLES.get(color_style, "default")

    return {
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": content}}],
            "icon": {"emoji": emoji},
            "color": color,
        },
    }
