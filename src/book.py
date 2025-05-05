from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Book:
    bookId: str
    title: str
    author: str
    cover: str
    sort: int
    isbn: str = field(default="")
    rating: float = field(default=0.0)

    status: str = field(default="")
    reading_time: int = field(default=0)
    finished_date: Optional[int] = field(default=None)
    category: str = field(default="")

    bookmark_list: List[Dict] = field(default_factory=list)
    summary: List[Dict] = field(default_factory=list)
    reviews: List[Dict] = field(default_factory=list)
    chapters: Dict = field(default_factory=dict)
    bookmark_count: int = field(default=0)
