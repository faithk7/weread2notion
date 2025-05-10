import argparse
import functools
import random
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from notion_client import Client

from book import Book
from book_builder import BookBuilder
from logger import logger
from notion.block_manager import NotionBlockManager
from notion.database import NotionDatabaseManager
from notion.page_builder import PageContentBuilder
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


def process_books(
    books_json_list: List[Dict[str, Any]],
    latest_sort: int,
    book_processor: Callable[[Book], Optional[str]],
    builder: BookBuilder,
) -> None:
    """Process a list of books and sync them to Notion"""
    for book_json in books_json_list:
        try:
            current_sort = book_json.get("sort")
            if current_sort <= latest_sort:
                logger.info(f"Skipping book with sort {current_sort} <= {latest_sort}")
                continue

            book = builder.build(book_json)

            if not book:
                logger.error(
                    f"Failed to build book object for: {book_json.get('book', {}).get('title')}"
                )
                continue

            logger.info(f"Processing book: {book.bookId} - {book.title} - {book.isbn}")

            page_id = book_processor(book)
            if page_id:
                logger.info(f"Successfully processed book: {book.title}")
            else:
                logger.error(f"Failed to process book: {book.title}")

        except Exception as e:
            logger.error(
                f"Unhandled error processing book data {book_json.get('book', {}).get('title')}: {e}"
            )


def process_book(
    book: Book,
    database_manager: NotionDatabaseManager,
    block_manager: NotionBlockManager,
    content_builder: PageContentBuilder,
) -> Optional[str]:
    """Process a single book by creating a Notion page and adding content."""
    try:
        # Check and delete existing entry
        database_manager.check_and_delete(book.bookId)

        # Create the page
        page_id = database_manager.create_book_page(book)
        if not page_id:
            logger.error(f"Failed to create Notion page for book: {book.title}")
            return None

        # Build the content using the book object
        children, grandchild = content_builder.build_book_content(book)

        # Add the content only after we create the page
        if children:
            results = block_manager.add_children(page_id, children)
            if results and grandchild:
                block_manager.add_grandchildren(results, grandchild)
        else:
            logger.info(f"No content (children) generated for book: {book.title}")

        return page_id
    except Exception as e:
        logger.error(f"Error processing book {book.title}: {e}")
        return None


def main() -> None:
    weread_cookie, notion_token, database_id, dev_mode = parse_arguments()

    # Initialize services directly
    client = Client(auth=notion_token)
    database_manager = NotionDatabaseManager(client, database_id)
    block_manager = NotionBlockManager(client)
    content_builder = PageContentBuilder()

    weread_client = WeReadClient(weread_cookie)
    book_builder = BookBuilder(weread_client)

    # Get latest sort value from Notion using database_manager directly
    latest_sort = database_manager.get_latest_sort()
    logger.info(f"Latest sort value from Notion: {latest_sort}")

    books_json_list = weread_client.get_notebooklist()
    if not books_json_list:
        logger.error("Failed to get books from WeRead")
        return

    if dev_mode:
        logger.info("Running in dev mode - randomly selecting 30 books")
        books_json_list = books_json_list[-5:] + random.sample(
            books_json_list, min(30, len(books_json_list))
        )
        logger.info(
            f"Selected books: {[{'title': book['book']['title'], 'sort': book['sort']} for book in books_json_list]}"
        )

    start_time = datetime.now()
    # Create a bound version of process_book with managers pre-filled
    bound_process_book = functools.partial(
        process_book,
        database_manager=database_manager,
        block_manager=block_manager,
        content_builder=content_builder,
    )

    process_books(books_json_list, latest_sort, bound_process_book, book_builder)
    logger.info(f"Total processing time: {datetime.now() - start_time}")


if __name__ == "__main__":
    main()
