from pydantic import BaseModel, Field


class CreateSheetsConfig(BaseModel):
    names: list[str] = Field(..., description="工作表名称列表")
    headers: list[str] | None = Field(
        default=None,
        description="每个工作表默认表头，留空则为空表",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "names": ["1月", "2月", "3月"],
                "headers": ["日期", "项目", "金额"],
            }
        }
