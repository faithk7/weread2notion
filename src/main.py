import argparse
import logging
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, Tuple

from notion_client import Client

from book import Book, BookService, get_children, get_notebooklist
from logger import logger
from notion import NotionManager
from weread import WeReadClient


def parse_arguments() -> Tuple[str, str, str, bool]:
    parser = argparse.ArgumentParser()
    for arg in ["weread_cookie", "notion_token", "database_id"]:
        parser.add_argument(arg)
    parser.add_argument(
        "--dev", action="store_true", help="Run in dev mode with limited books"
    )
    options = parser.parse_args()
    return (
        options.weread_cookie,
        options.notion_token,
        options.database_id,
        options.dev,
    )


def process_book(
    book_json: Dict[str, Any],
    latest_sort: int,
    notion_manager: NotionManager,
    book_service: BookService,
) -> None:
    current_sort = book_json.get("sort")
    if current_sort <= latest_sort:
        return
    book = Book.from_json(book_json)
    book = book_service.load_book_details(book)

    notion_manager.check_and_delete(book.bookId)

    children, grandchild = get_children(book.chapters, book.summary, book.bookmark_list)
    logger.info(
        f"Current book: {book.bookId} - {book.title} - {book.isbn} - bookmark_list: {book.bookmark_list}"
    )
    id = notion_manager.insert_to_notion(book)
    results = notion_manager.add_children(id, children)
    if len(grandchild) > 0 and results is not None:
        notion_manager.add_grandchild(grandchild, results)


if __name__ == "__main__":
    weread_cookie, notion_token, database_id, dev_mode = parse_arguments()

    notion_manager = NotionManager(notion_token, database_id)
    latest_sort = notion_manager.get_latest_sort()

    notion_client = Client(auth=notion_token, log_level=logging.ERROR)
    weread_client = WeReadClient(weread_cookie)
    book_service = BookService(weread_client)

    # NOTE: this is the starting point of getting all books
    books = get_notebooklist(weread_client.session)
    assert books is not None, "获取书架和笔记失败"

    if dev_mode:
        logger.info("Running in dev mode - randomly selecting 30 books")
        books = random.sample(books, min(30, len(books)))
        logger.info(
            f"Randomly selected books: {[{'title': book['book']['title'], 'sort': book['sort']} for book in books]}"
        )

    time = datetime.now()
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                process_book,
                book_json,
                latest_sort,
                notion_manager,
                book_service,
            )
            for book_json in books
        ]
        for future in futures:
            future.result()
    logger.info("Total time: %s", datetime.now() - time)
