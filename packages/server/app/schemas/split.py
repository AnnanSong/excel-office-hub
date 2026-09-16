from typing import Literal

from pydantic import BaseModel, Field


class SplitConfig(BaseModel):
    mode: Literal["by_column", "by_row_count", "by_sheet"] = Field(
        default="by_column",
        description="拆分模式：by_column 按列分组，by_row_count 按行数，by_sheet 按工作表",
    )
    source_sheet: str | None = Field(default=None, description="源工作表名，留空取第一个")
    target_column: str | None = Field(
        default=None,
        description="by_column 模式：按哪一列分组（单列，向后兼容）",
    )
    columns: list[str] | None = Field(
        default=None,
        description="多列组合分组（如 L+AD+H 三列组合）；提供后优先于 target_column",
    )
    column_separator: str = Field(
        default="_",
        description="多列组合时在文件名中连接各列值所用的分隔符",
    )
    row_count: int | None = Field(default=None, description="by_row_count 模式：每个文件多少行（不含表头）")
    keep_columns: list[str] | None = Field(default=None, description="仅保留指定列，留空保留全部")
    naming_template: str = Field(
        default="{value}",
        description="输出文件名模板，支持 {value} / {index} / {sheet} / {count}（该组数据行数，即 X 笔）",
    )
    header_row: int = Field(
        default=1,
        ge=1,
        description="表头所在行（1-indexed），数据从其下一行开始",
    )
    skip_empty: bool = Field(
        default=True,
        description="分组键为空的行不单独成文件（跳过并计入统计）",
    )
    add_source_info: bool = Field(
        default=True,
        description="是否添加来源信息列（仅在未保留格式时生效）",
    )
    preserve_format: bool = Field(
        default=True,
        description="保留原工作表格式（字体/边框/底色/列宽/合并单元格）。通过复制原 Sheet 实现",
    )
    preserve_merged: bool = Field(
        default=True,
        description="preserve_format 时是否保留合并单元格（仅含表头区域的合并会被保留）",
    )
    freeze_header: bool = Field(
        default=False,
        description="拆分后是否冻结表头行",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "mode": "by_column",
                "columns": ["部门", "项目", "岗位"],
                "naming_template": "{value}_{count}笔",
                "header_row": 3,
            }
        }
    }
