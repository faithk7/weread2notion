from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class Book(BaseModel):
    """书籍信息模"""

    bookId: str = Field(..., description="书籍唯一标识符", min_length=1)
    title: str = Field(..., description="书籍标题", min_length=1)
    author: str = Field(..., description="作者姓名", min_length=1)
    cover: str = Field(..., description="封面图片URL")
    sort: Optional[Union[int, float]] = Field(
        default=None,
        description="排序字段，支持整数、浮点数和None（将转换为float('inf')）",
    )

    isbn: str = Field(default="", description="ISBN号码")
    rating: float = Field(default=0.0, description="评分", ge=0.0, le=10.0)

    status: str = Field(default="", description="阅读状态")
    reading_time: int = Field(default=0, description="阅读时长（分钟）", ge=0)
    finished_date: Optional[int] = Field(default=None, description="完成阅读日期时间戳")
    category: str = Field(default="", description="书籍分类")

    bookmark_list: List[Dict] = Field(default_factory=list, description="书签列表")
    summary: List[Dict] = Field(default_factory=list, description="摘要列表")
    reviews: List[Dict] = Field(default_factory=list, description="书评列表")
    chapters: Dict = Field(default_factory=dict, description="章节信息字典")
    bookmark_count: int = Field(default=0, description="书签数量", ge=0)

    @field_validator("cover")
    @classmethod
    def validate_cover_url(cls, v: str) -> str:
        """验证封面URL格式"""
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("封面URL必须以http://或https://开头")
        return v

    @model_validator(mode="after")
    def validate_bookmark_consistency(self) -> "Book":
        """验证书签数量与书签列表的一致性（跨字段验证）"""
        actual_count = len(self.bookmark_list)
        if self.bookmark_count != actual_count:
            # 自动修正书签数量以匹配实际列表长度
            self.bookmark_count = actual_count
        return self

    class Config:
        """Pydantic配置"""

        allow_population_by_field_name = True
        validate_assignment = True
        use_enum_values = True
