from typing import Literal

from pydantic import BaseModel, Field


class NormalizeRules(BaseModel):
    """Sheet 名归一化规则（对应 VBA 的 NormalizeSheetName）。"""

    strip_index: bool = Field(
        default=True,
        description="去除开头的序号前缀，如 '2-1.' '01.' '1、' '1. '",
    )
    strip_period: bool = Field(
        default=True,
        description="去除末尾的期间后缀，如 '2608' '20260831' '2026.08' '2026年08月'",
    )
    case_insensitive: bool = Field(
        default=True,
        description="大小写统一（全部转小写）后再匹配",
    )
    dash_unify: bool = Field(
        default=True,
        description="将下划线、全角/半角横杠统一为 unify_char 后再匹配",
    )
    unify_char: str = Field(
        default="-",
        description="dash_unify 时统一使用的分隔符",
    )


class MergeConfig(BaseModel):
    """
    ExcelMergeSkill（多文件汇总增强）配置。
    相比 AggregateConfig，核心新增：
      - merge_mode=sheets 时遍历每个文件的全部 Sheet，按归一化后的逻辑名分组分别汇总
      - sheet_match=normalize 时启用 Sheet 名归一化与 spacer 跳过
      - header_row 可配置（很多模板表头不在第 1 行，常见第 3 行）
      - expected_sheets 用于"缺失 Sheet 标红"
      - template_path 用于"模板填充保格式"
    """

    merge_mode: Literal["files", "sheets"] = Field(
        default="sheets",
        description=(
            "files: 每个文件取一个 Sheet 堆叠(旧行为); "
            "sheets: 遍历每个文件全部 Sheet 按逻辑名分组(主表-明细分别汇总)"
        ),
    )
    sheet_match: Literal["exact", "normalize"] = Field(
        default="normalize",
        description="exact 严格匹配 Sheet 名; normalize 先归一化再匹配",
    )
    normalize_rules: NormalizeRules = Field(default_factory=NormalizeRules)
    skip_spacers: bool = Field(
        default=True,
        description="跳过占位页(名称含 '>>>' 或 Tab 为黄色), 对应 VBA IsSpacerSheet",
    )
    header_row: int = Field(
        default=1,
        ge=1,
        description="表头所在行(1-indexed), 支持模板表头在第 3 行等情形",
    )
    target_sheet: str | None = Field(
        default=None,
        description="仅处理该 Sheet; 留空则处理全部(merge_mode=sheets)或取第一个(files)",
    )
    key_columns: list[str] | None = Field(
        default=None,
        description="业务主键, 用于跨文件去重",
    )
    field_map: dict[str, str] | None = Field(
        default=None,
        description="源列名 -> 标准字段映射",
    )
    column_aliases: dict[str, list[str]] | None = Field(
        default=None,
        description="标准字段的别名表, 用于表头归一化",
    )
    required_columns: list[str] | None = Field(
        default=None,
        description="必需字段, 缺失或为空则进入异常表(阻断类问题)",
    )
    expected_sheets: list[str] | None = Field(
        default=None,
        description="期望出现的 Sheet 名(归一化后比较); 任一文件缺失则标红",
    )
    output_sheet_naming: Literal["logical", "first_raw"] = Field(
        default="logical",
        description="输出结果 Sheet 命名: logical 用归一化名, first_raw 用首次出现的原始名",
    )
    add_log: bool = Field(
        default=True,
        description="生成'导入日志'Sheet, 记录每个文件每个 Sheet 的导入行数与状态",
    )
    template_path: str | None = Field(
        default=None,
        description=(
            "可选汇总模板; 提供后按同名 Sheet 将数据填入模板(保留模板格式), 缺失模板 Sheet 标红"
        ),
    )
    keep_first_on_dup: bool = Field(
        default=True,
        description="主键重复时保留先到的记录",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "merge_mode": "sheets",
                "sheet_match": "normalize",
                "header_row": 3,
                "key_columns": ["工号"],
                "required_columns": ["工号", "姓名", "部门"],
                "expected_sheets": ["工资明细", "研发费用明细"],
            }
        }
    }
