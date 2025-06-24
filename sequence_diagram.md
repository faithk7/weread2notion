# WeRead2Notion S quence Diagram (时序图)

```mermaid
sequenceDiagram
    participant User
    participant Main
    participant WeReadClient
    participant BookBuilder
    participant NotionDB as NotionDatabaseManager
    participant PageBuilder as PageContentBuilder
    participant NotionAPI as Notion API

    User->>Main: Start application with cookie, token, database_id
    Main->>WeReadClient: Initialize with weread_cookie
    WeReadClient->>WeReadClient: Set cookies from provided string
    WeReadClient->>WeReadClient: _try_connect()
    WeReadClient->>NotionAPI: Test connection with WEREAD_NOTEBOOKS_URL
    NotionAPI-->>WeReadClient: Connection response
    WeReadClient-->>Main: Client initialized and connected

    Main->>NotionDB: Initialize with notion_token and database_id
    Main->>PageBuilder: Initialize PageContentBuilder
    Main->>BookBuilder: Initialize with WeReadClient

    Main->>NotionDB: get_latest_sort()
    NotionDB->>NotionAPI: Query database for latest sort value
    NotionAPI-->>NotionDB: Return sort data
    NotionDB-->>Main: Return latest sort value

    Main->>WeReadClient: get_notebooklist()
    WeReadClient->>NotionAPI: Fetch user's notebook list
    NotionAPI-->>WeReadClient: Return books with notes
    WeReadClient-->>Main: Return filtered book list

    loop For each book in list
        Main->>BookBuilder: build(book_data)
        BookBuilder->>BookBuilder: _create_book_from_json()
        BookBuilder->>BookBuilder: _fetch_all()

        BookBuilder->>WeReadClient: get_bookinfo(bookId)
        WeReadClient->>NotionAPI: Fetch book information
        NotionAPI-->>WeReadClient: Book info response
        WeReadClient-->>BookBuilder: Return book info

        BookBuilder->>WeReadClient: get_bookmarks(bookId)
        WeReadClient->>NotionAPI: Fetch book highlights/bookmarks
        NotionAPI-->>WeReadClient: Bookmarks response
        WeReadClient-->>BookBuilder: Return bookmarks

        BookBuilder->>WeReadClient: get_chapters(bookId)
        WeReadClient->>NotionAPI: Fetch chapter information
        NotionAPI-->>WeReadClient: Chapters response
        WeReadClient-->>BookBuilder: Return chapters

        BookBuilder->>WeReadClient: get_readinfo(bookId)
        WeReadClient->>NotionAPI: Fetch reading progress
        NotionAPI-->>WeReadClient: Read info response
        WeReadClient-->>BookBuilder: Return read info

        BookBuilder->>BookBuilder: Process all fetched data
        BookBuilder-->>Main: Return completed Book object

        Main->>NotionDB: check_and_delete(bookId)
        NotionDB->>NotionAPI: Query for existing book pages
        NotionAPI-->>NotionDB: Existing pages
        NotionDB->>NotionAPI: Delete existing pages if found

        Main->>NotionDB: create_book_page(book)
        NotionDB->>NotionAPI: Create new book page
        NotionAPI-->>NotionDB: Page created with page_id
        NotionDB-->>Main: Return page_id

        Main->>PageBuilder: build_content(book, page_id)
        PageBuilder->>NotionAPI: Add book content blocks
        NotionAPI-->>PageBuilder: Content added
        PageBuilder-->>Main: Content build complete
    end

    Main->>WeReadClient: close()
    WeReadClient->>WeReadClient: Close HTTP session
    Main-->>User: Sync completed successfully
```

## Key Changes After Removing Chrome Refresh:

1. **Simplified Initialization**: WeReadClient now requires a cookie parameter
2. **Direct Cookie Usage**: Uses provided cookie string without browser automation
3. **No Cookie Manager**: Removed Selenium dependency
4. **Streamlined Flow**: More direct process without retry logic