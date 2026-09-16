from typing import Literal

from pydantic import BaseModel, Field


class AggregateConfig(BaseModel):
    mode: Literal["stack", "consolidate"] = Field(
        default="stack",
        description="汇总模式：stack 纵向堆叠，consolidate 按关键字段关联",
    )
    target_sheet: str | None = Field(
        default=None,
        description="读取每个文件的哪个工作表，留空取第一个",
    )
    key_columns: list[str] | None = Field(
        default=None,
        description="业务主键，用于去重与多表关联",
    )
    field_map: dict[str, str] | None = Field(
        default=None,
        description="源列名 -> 标准字段映射",
    )
    column_aliases: dict[str, list[str]] | None = Field(
        default=None,
        description="标准字段的别名表，用于表头归一化",
    )
    required_columns: list[str] | None = Field(
        default=None,
        description="必需字段，缺失则进入异常表",
    )
    keep_first_on_dup: bool = Field(
        default=True,
        description="主键重复时保留先到的记录",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "mode": "stack",
                "key_columns": ["工号"],
                "required_columns": ["工号", "姓名", "部门"],
            }
        }
