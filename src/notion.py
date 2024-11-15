import hashlib
import re
import time
from datetime import datetime

from book import get_heading, get_quote, get_read_info, get_table_of_contents
from util import get_callout


def check(client, database_id, bookId):
    """检查是否已经插入过 如果已经插入了就删除"""
    time.sleep(1)
    filter = {"property": "BookId", "rich_text": {"equals": bookId}}
    response = client.databases.query(database_id=database_id, filter=filter)
    for result in response["results"]:
        time.sleep(1)
        client.blocks.delete(block_id=result["id"])


def insert_to_notion(
    client, database_id, bookName, bookId, cover, sort, author, isbn, rating, session
):
    """插入到notion"""
    time.sleep(1)
    parent = {"database_id": database_id, "type": "database_id"}
    properties = {
        "BookName": {"title": [{"type": "text", "text": {"content": bookName}}]},
        "BookId": {"rich_text": [{"type": "text", "text": {"content": bookId}}]},
        "ISBN": {"rich_text": [{"type": "text", "text": {"content": isbn}}]},
        "URL": {
            "url": f"https://weread.qq.com/web/reader/{calculate_book_str_id(bookId)}"
        },
        "Author": {"rich_text": [{"type": "text", "text": {"content": author}}]},
        "Sort": {"number": sort},
        "Rating": {"number": rating},
        "Cover": {
            "files": [{"type": "external", "name": "Cover", "external": {"url": cover}}]
        },
    }
    read_info = get_read_info(session, bookId=bookId)
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

    icon = {"type": "external", "external": {"url": cover}}
    # notion api 限制100个block
    response = client.pages.create(parent=parent, icon=icon, properties=properties)
    id = response["id"]
    return id


def add_children(client, id, children):
    results = []
    for i in range(0, len(children) // 100 + 1):
        time.sleep(1)  # NOTE: TEMP FIX
        response = client.blocks.children.append(
            block_id=id, children=children[i * 100 : (i + 1) * 100]
        )
        results.extend(response.get("results"))
    return results if len(results) == len(children) else None


def add_grandchild(client, grandchild, results):
    for key, value in grandchild.items():
        time.sleep(1)
        id = results[key].get("id")
        client.blocks.children.append(block_id=id, children=[value])


def get_sort(client, database_id):
    """获取database中的最新时间"""
    filter = {"property": "Sort", "number": {"is_not_empty": True}}
    sorts = [
        {
            "property": "Sort",
            "direction": "descending",
        }
    ]
    response = client.databases.query(
        database_id=database_id, filter=filter, sorts=sorts, page_size=1
    )
    if len(response.get("results")) == 1:
        return response.get("results")[0].get("properties").get("Sort").get("number")
    return 0


def get_children(chapter, summary, bookmark_list):
    children = []
    grandchild = {}

    if chapter is not None:
        # 添加目录
        children.append(get_table_of_contents())
        d = {}
        for data in bookmark_list:
            chapterUid = data.get("chapterUid", 1)
            if chapterUid not in d:
                d[chapterUid] = []
            d[chapterUid].append(data)

        for key, value in d.items():
            if key in chapter:
                # 添加章节
                children.append(
                    get_heading(
                        chapter.get(key).get("level"), chapter.get(key).get("title")
                    )
                )

            for i in value:
                callout = get_callout(
                    i.get("markText"),
                    data.get("style"),
                    i.get("colorStyle"),
                    i.get("reviewId"),
                )
                children.append(callout)

                if i.get("abstract") is not None and i.get("abstract") != "":
                    quote = get_quote(i.get("abstract"))
                    grandchild[len(children) - 1] = quote

    else:
        # 如果没有章节信息
        for data in bookmark_list:
            children.append(
                get_callout(
                    data.get("markText"),
                    data.get("style"),
                    data.get("colorStyle"),
                    data.get("reviewId"),
                )
            )

    if summary is not None and len(summary) > 0:
        children.append(get_heading(1, "点评"))
        for i in summary:
            children.append(
                get_callout(
                    i.get("review").get("content"),
                    i.get("style"),
                    i.get("colorStyle"),
                    i.get("review").get("reviewId"),
                )
            )

    return children, grandchild


def transform_id(book_id):
    id_length = len(book_id)

    if re.match("^\d*$", book_id):
        ary = []
        for i in range(0, id_length, 9):
            ary.append(format(int(book_id[i : min(i + 9, id_length)]), "x"))
        return "3", ary

    result = ""
    for i in range(id_length):
        result += format(ord(book_id[i]), "x")
    return "4", [result]


def calculate_book_str_id(book_id):
    md5 = hashlib.md5(usedforsecurity=False)
    md5.update(book_id.encode("utf-8"))
    digest = md5.hexdigest()
    result = digest[0:3]
    code, transformed_ids = transform_id(book_id)
    result += code + "2" + digest[-2:]

    for i in range(len(transformed_ids)):
        hex_length_str = format(len(transformed_ids[i]), "x")
        if len(hex_length_str) == 1:
            hex_length_str = "0" + hex_length_str

        result += hex_length_str + transformed_ids[i]

        if i < len(transformed_ids) - 1:
            result += "g"

    if len(result) < 20:
        result += digest[0 : 20 - len(result)]

    md5 = hashlib.md5(usedforsecurity=False)
    md5.update(result.encode("utf-8"))
    result += md5.hexdigest()[0:3]
    return result
