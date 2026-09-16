from typing import Literal

from pydantic import BaseModel, Field

RuleType = Literal[
    "required",   # 必填：非空
    "type",       # 类型：number / date / text
    "range",      # 范围：min <= x <= max（对数值）或长度范围
    "enum",       # 枚举：值必须在允许列表中
    "pattern",    # 正则匹配
    "compare",    # 列间比较（勾稽），支持 eq / ne / gt / lt / gte / lte / sum_eq
    "threshold",  # 阈值：环比/占比等超限告警
]


class ValidationRule(BaseModel):
    rule_id: str = Field(..., description="规则编号，如 R001")
    name: str = Field(default="", description="规则名称")
    column: str | None = Field(default=None, description="作用列（compare/sum_eq 时可留空）")
    rule_type: RuleType = Field(..., description="规则类型")
    level: Literal["error", "warning"] = Field(
        default="error",
        description="error 阻断级（红），warning 警告级（黄）",
    )
    message: str = Field(default="", description="违规提示；留空则自动生成")

    # 各类型参数
    min: float | None = Field(default=None, description="range 下界 / threshold 阈值")
    max: float | None = Field(default=None, description="range 上界")
    value_type: Literal["number", "date", "text"] = Field(
        default="number", description="type 规则的目标类型"
    )
    allow_negative: bool = Field(
        default=True, description="数值是否允许为负（type=number / range 时生效）"
    )
    allowed: list[str] | None = Field(default=None, description="enum 允许值列表")
    pattern: str | None = Field(default=None, description="pattern 正则表达式")

    # compare 参数
    compare_columns: list[str] | None = Field(
        default=None, description="参与比较的列（sum_eq 用）"
    )
    compare_op: Literal["eq", "ne", "gt", "lt", "gte", "lte", "sum_eq"] = Field(
        default="eq", description="比较运算符；sum_eq 表示「第一列 = 其余列按符号求和」"
    )
    signs: list[float] | None = Field(
        default=None,
        description=(
            "sum_eq 时其余列各自的符号，如 [1, -1] 表示 第一列 = 第二列 - 第三列；"
            "留空默认全为 +1"
        ),
    )
    tolerance: float = Field(default=0.0, ge=0.0, description="比较容差")

    # threshold 参数
    threshold_type: Literal["abs", "pct_change", "ratio"] = Field(
        default="abs", description="阈值类型：绝对值 / 环比变化率 / 占比"
    )
    baseline_column: str | None = Field(
        default=None, description="threshold 的基准列（pct_change/ratio 用）"
    )


class ValidationConfig(BaseModel):
    source_sheet: str | None = Field(default=None, description="校验的工作表名，留空取第一个")
    header_row: int = Field(default=1, ge=1, description="表头所在行（1-indexed）")
    rules: list[ValidationRule] = Field(default_factory=list, description="校验规则列表")
    data_start_row: int | None = Field(
        default=None, description="数据起始行，留空为 header_row + 1"
    )
    max_preview_rows: int = Field(default=500, description="报告中预览的数据行数上限")

    model_config = {
        "json_schema_extra": {
            "example": {
                "header_row": 3,
                "rules": [
                    {
                        "rule_id": "R001",
                        "name": "金额必填",
                        "column": "金额",
                        "rule_type": "required",
                        "level": "error",
                    },
                    {
                        "rule_id": "R002",
                        "name": "金额非负",
                        "column": "金额",
                        "rule_type": "range",
                        "min": 0,
                        "level": "error",
                    },
                    {
                        "rule_id": "R003",
                        "name": "期末勾稽",
                        "rule_type": "compare",
                        "compare_op": "sum_eq",
                        "compare_columns": ["期末", "期初", "本期增加", "本期减少"],
                        "level": "warning",
                    },
                ],
            }
        }
    }
