import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, Tuple

import requests
from notion_client import Client

from book import (
    Book,
    get_bookmark_list,
    get_chapter_info,
    get_children,
    get_notebooklist,
    get_review_list,
)
from constants import WEREAD_URL
from logger import logger
from notion import NotionManager
from util import parse_cookie_string


def parse_arguments() -> Tuple[str, str, str]:
    parser = argparse.ArgumentParser()
    for arg in ["weread_cookie", "notion_token", "database_id"]:
        parser.add_argument(arg)
    options = parser.parse_args()
    return options.weread_cookie, options.notion_token, options.database_id


def process_book(
    book_json: Dict[str, Any],
    latest_sort: int,
    notion_manager: NotionManager,
    session: requests.Session,
) -> None:
    sort = book_json.get("sort")
    if sort <= latest_sort:
        return
    book_json = book_json["book"]
    book = Book(
        book_json.get("bookId"),
        book_json.get("title"),
        book_json.get("author"),
        book_json.get("cover"),
        book_json.get("sort"),
    )

    notion_manager.check_and_delete(book.bookId)
    chapter = get_chapter_info(session, book.bookId)
    bookmark_list = get_bookmark_list(session, book.bookId)
    summary, reviews = get_review_list(session, book.bookId)
    bookmark_list.extend(reviews)

    bookmark_list = sorted(
        bookmark_list,
        key=lambda x: (
            x.get("chapterUid", 1),
            (
                0
                if (x.get("range", "") == "" or x.get("range").split("-")[0] == "")
                else int(x.get("range").split("-")[0])
            ),
        ),
    )
    book.set_bookinfo(session)

    children, grandchild = get_children(chapter, summary, bookmark_list)
    logger.info(
        f"Current book: {book.bookId} - {book.title} - {book.isbn} - bookmark_list: {bookmark_list}"
    )
    id = notion_manager.insert_to_notion(book, session)
    results = notion_manager.add_children(id, children)
    if len(grandchild) > 0 and results is not None:
        notion_manager.add_grandchild(grandchild, results)


if __name__ == "__main__":
    weread_cookie, notion_token, database_id = parse_arguments()

    notion_manager = NotionManager(notion_token, database_id)
    latest_sort = notion_manager.get_latest_sort()

    session = requests.Session()
    session.cookies = parse_cookie_string(weread_cookie)
    session.get(WEREAD_URL)

    client = Client(auth=notion_token, log_level=logging.ERROR)

    # NOTE: this is the starting point of getting all books
    books = get_notebooklist(session)

    assert books is not None, "获取书架和笔记失败"

    time = datetime.now()
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                process_book,
                book_json,
                latest_sort,
                notion_manager,
                session,
            )
            for book_json in books
        ]
        for future in futures:
            future.result()
    logger.info("Total time: %s", datetime.now() - time)
