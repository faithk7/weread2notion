import argparse
import random
from datetime import datetime
from typing import Any, Dict, List, Tuple

from book_builder import BookBuilder
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


def process_books(
    books_json_list: List[Dict[str, Any]],
    latest_sort: int,
    notion_manager: NotionManager,
    weread_client: WeReadClient,
) -> None:
    """Process a list of books and sync them to Notion"""
    for book_json in books_json_list:
        try:
            current_sort = book_json.get("sort")
            if current_sort <= latest_sort:
                logger.info(f"Skipping book with sort {current_sort} <= {latest_sort}")
                continue

            builder = BookBuilder(weread_client, book_json)
            book = builder.fetch_all().build()

            logger.info(f"Processing book: {book.bookId} - {book.title} - {book.isbn}")

            page_id = notion_manager.process_book(book)
            if page_id:
                logger.info(f"Successfully processed book: {book.title}")
            else:
                logger.error(f"Failed to process book: {book.title}")

        except Exception as e:
            logger.error(
                f"Error processing book {book_json.get('book', {}).get('title')}: {e}"
            )


def main() -> None:
    # Parse command line arguments
    weread_cookie, notion_token, database_id, dev_mode = parse_arguments()

    # Initialize services
    notion_manager = NotionManager.create(notion_token, database_id)
    weread_client = WeReadClient(weread_cookie)

    # Get latest sort value from Notion
    latest_sort = notion_manager.get_latest_sort()
    logger.info(f"Latest sort value from Notion: {latest_sort}")

    # Get books from WeRead
    books_json_list = weread_client.get_notebooklist()
    if not books_json_list:
        logger.error("Failed to get books from WeRead")
        return

    # Handle dev mode
    if dev_mode:
        logger.info("Running in dev mode - randomly selecting 30 books")
        books_json_list = random.sample(books_json_list, min(30, len(books_json_list)))
        logger.info(
            f"Selected books: {[{'title': book['book']['title'], 'sort': book['sort']} for book in books_json_list]}"
        )

    # Process books
    start_time = datetime.now()
    process_books(books_json_list, latest_sort, notion_manager, weread_client)
    logger.info(f"Total processing time: {datetime.now() - start_time}")


if __name__ == "__main__":
    main()
