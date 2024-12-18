from typing import Dict, List, Optional, Tuple

import requests

from constants import (
    WEREAD_BOOK_INFO,
    WEREAD_BOOKMARKLIST_URL,
    WEREAD_CHAPTER_INFO,
    WEREAD_NOTEBOOKS_URL,
    WEREAD_READ_INFO_URL,
    WEREAD_REVIEW_LIST_URL,
)
from logger import logger
from util import get_callout_block


class Book:
    def __init__(self, bookId: str, title: str, author: str, cover: str, sort: int):
        self.bookId = bookId

        self.title = title
        self.author = author
        self.cover = cover
        self.sort = sort

        self.isbn = ""
        self.rating = 0.0

        self.bookmark_list = []
        self.summary = []
        self.reviews = []
        self.chapters = {}

    def set_bookinfo(self, session: requests.Session):
        data = self._fetch_book_info(session)
        if data:
            self._update_book_info(data)

    def _fetch_book_info(self, session: requests.Session) -> Optional[Dict]:
        r = session.get(WEREAD_BOOK_INFO, params={"bookId": self.bookId})
        if r.ok:
            return r.json()
        return None

    def _update_book_info(self, data: Dict):
        self.isbn = data["isbn"]
        self.rating = data["newRating"] / 1000

    def set_summary(self, session: requests.Session):
        reviews = self._fetch_reviews(session)
        if reviews:
            self._process_reviews(reviews)

    def _fetch_reviews(self, session: requests.Session) -> Optional[List[Dict]]:
        params = dict(bookId=self.bookId, listType=11, mine=1, syncKey=0)
        r = session.get(WEREAD_REVIEW_LIST_URL, params=params)
        if r.ok:
            return r.json().get("reviews")
        return None

    def _process_reviews(self, reviews: List[Dict]):
        self.summary = list(filter(lambda x: x.get("review").get("type") == 4, reviews))
        self.reviews = list(filter(lambda x: x.get("review").get("type") == 1, reviews))
        self.reviews = list(map(lambda x: x.get("review"), self.reviews))
        self.reviews = list(
            map(lambda x: {**x, "markText": x.pop("content")}, self.reviews)
        )

    def set_bookmark_list(self, session: requests.Session):
        updated = self._fetch_bookmark_list(session)
        if updated is not None:
            self._update_bookmark_list(updated)
        else:
            self.bookmark_list = None

    def _fetch_bookmark_list(self, session: requests.Session) -> Optional[List[Dict]]:
        params = dict(bookId=self.bookId)
        r = session.get(WEREAD_BOOKMARKLIST_URL, params=params)
        if r.ok:
            return r.json().get("updated")
        return None

    def _update_bookmark_list(self, updated: List[Dict]):
        logger.info(f"Updated bookmark list: {updated}")
        self.bookmark_list = sorted(
            updated,
            key=lambda x: (
                x.get("chapterUid", 1),
                int(x.get("range").split("-")[0]),
            ),
        )

    def set_chapters(self, session: requests.Session):
        data = self._fetch_chapter_info(session)
        if data:
            self._update_chapters(data)
        else:
            self.chapters = None

    def _fetch_chapter_info(self, session: requests.Session) -> Optional[List[Dict]]:
        body = {"bookIds": [self.bookId], "synckeys": [0], "teenmode": 0}
        r = session.post(WEREAD_CHAPTER_INFO, json=body)
        if r.ok:
            return r.json().get("data", [])
        return None

    def _update_chapters(self, data: List[Dict]):
        if len(data) == 1 and "updated" in data[0]:
            update = data[0]["updated"]
            self.chapters = {item["chapterUid"]: item for item in update}


def get_bookmark_list(session: requests.Session, bookId: str) -> Optional[List[Dict]]:
    """获取我的划线
    Returns:
        List[Dict]: 本书的划线列表
    """

    params = dict(bookId=bookId)
    r = session.get(WEREAD_BOOKMARKLIST_URL, params=params)

    if r.ok:
        updated = r.json().get("updated")
        logger.info(f"Updated bookmark list: {updated}")

        updated = sorted(
            updated,
            key=lambda x: (x.get("chapterUid", 1), int(x.get("range").split("-")[0])),
        )
        return r.json()["updated"]
    return None


def get_read_info(session: requests.Session, bookId: str) -> Optional[Dict]:
    params = dict(bookId=bookId, readingDetail=1, readingBookIndex=1, finishedDate=1)
    r = session.get(WEREAD_READ_INFO_URL, params=params)
    if r.ok:
        return r.json()
    return None


def get_bookinfo(session: requests.Session, bookId: str) -> Tuple[str, float]:
    """获取书的详情"""
    params = dict(bookId=bookId)
    r = session.get(WEREAD_BOOK_INFO, params=params)
    isbn = ""
    newRating = 0.0
    if r.ok:
        data = r.json()
        isbn = data["isbn"]
        newRating = data["newRating"] / 1000
    return (isbn, newRating)


def get_notebooklist(session: requests.Session) -> Optional[List[Dict]]:
    """获取笔记本列表"""
    r = session.get(WEREAD_NOTEBOOKS_URL)
    if r.ok:
        data = r.json()
        books = data.get("books")
        print("len(books)", len(books))
        print("books", books[:5])
        books.sort(key=lambda x: x["sort"])
        return books
    else:
        print(r.text)
    return None


def get_chapter_info(
    session: requests.Session, bookId: str
) -> Optional[Dict[int, Dict]]:
    """获取章节信息"""
    body = {"bookIds": [bookId], "synckeys": [0], "teenmode": 0}
    r = session.post(WEREAD_CHAPTER_INFO, json=body)
    if (
        r.ok
        and "data" in r.json()
        and len(r.json()["data"]) == 1
        and "updated" in r.json()["data"][0]
    ):
        update = r.json()["data"][0]["updated"]
        return {item["chapterUid"]: item for item in update}
    return None


def get_review_list(
    session: requests.Session, bookId: str
) -> Tuple[List[Dict], List[Dict]]:
    """获取笔记"""
    params = dict(bookId=bookId, listType=11, mine=1, syncKey=0)
    r = session.get(WEREAD_REVIEW_LIST_URL, params=params)
    reviews = r.json().get("reviews")
    summary = list(filter(lambda x: x.get("review").get("type") == 4, reviews))
    reviews = list(filter(lambda x: x.get("review").get("type") == 1, reviews))
    reviews = list(map(lambda x: x.get("review"), reviews))
    reviews = list(map(lambda x: {**x, "markText": x.pop("content")}, reviews))
    return (summary, reviews)


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
