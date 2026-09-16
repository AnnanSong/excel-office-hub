from typing import Literal

from pydantic import BaseModel, Field


class CompareConfig(BaseModel):
    """
    ConfigurableKeyBasedCompareSkill（数据比对）配置。

    核心思路：按关键字段（key_columns）而非行号匹配两版数据，
    因此行顺序变化不影响比对结果（对应测试案例 T006）。
    """

    key_columns: list[str] = Field(
        ...,
        description="关键字段，按此匹配两版记录；行顺序变化不影响比对",
    )
    compare_columns: list[str] | None = Field(
        default=None,
        description="需要比对差异的字段；留空表示除关键字段外全部比对",
    )
    source_sheet: str | None = Field(
        default=None,
        description="相对比的工作表名，留空各自取第一个",
    )
    old_sheet: str | None = Field(default=None, description="旧版工作表名，留空取第一个")
    new_sheet: str | None = Field(default=None, description="新版工作表名，留空取第一个")
    header_row: int = Field(default=1, ge=1, description="表头所在行（1-indexed）")

    ignore_whitespace: bool = Field(default=True, description="比较时忽略首尾空格")
    ignore_case: bool = Field(default=False, description="比较时忽略大小写")
    numeric_tolerance: float = Field(
        default=0.0,
        ge=0.0,
        description="数值容差：两数之差绝对值 <= 容差视为相等（0 表示精确比较）",
    )

    output_mode: Literal["summary", "full"] = Field(
        default="summary",
        description="summary 仅输出差异；full 额外输出并排全量对比表",
    )
    include_unchanged: bool = Field(
        default=False,
        description="full 模式下是否也列出未变化记录",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "key_columns": ["往来单位"],
                "compare_columns": ["期初", "本期增加", "本期减少", "期末"],
                "header_row": 1,
            }
        }
    }
