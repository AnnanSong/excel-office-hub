import io
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import openpyxl
import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from app.schemas.merge import MergeConfig, NormalizeRules


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #

def _normalize_header(name: Any) -> str:
    return str(name).strip().replace("\n", " ").replace("\t", " ").lower()


def _cell_val(v: Any) -> Any:
    """把 pandas/numpy 标量转换为 openpyxl 可写的基本类型。"""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return float(v)
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if isinstance(v, datetime):
        return v
    return v


def _sanitize_sheet_name(name: str) -> str:
    name = str(name).strip()
    name = re.sub(r'[\\/*?:\[\]]', "_", name)
    if len(name) > 31:
        name = name[:31]
    if not name:
        name = "Sheet"
    return name


def _unique_sheet_name(wb: openpyxl.Workbook, name: str) -> str:
    base = _sanitize_sheet_name(name)
    if base not in wb.sheetnames:
        return base
    i = 2
    while f"{base}_{i}" in wb.sheetnames:
        i += 1
    return f"{base}_{i}"


# --------------------------------------------------------------------------- #
# Sheet 名归一化 (VBA NormalizeSheetName)
# --------------------------------------------------------------------------- #

# 末尾期间后缀：2026.08 / 2026年08月 / 202608 / 2026/8 / 20260831 / 2608 / 2026
# 注意：先匹配更长的形态，最后兜底 4 位 YYMM（如 2608）。
# 末尾期间后缀：2026.08 / 2026年08月 / 202608 / 2026/8 / 20260831 / 2608 / 2026
# 先匹配含分隔符的完整形态，再匹配纯数字形态（如 2608 YYMM、202608、20260831）。
_PERIOD_RE = re.compile(
    r"[\s_\-–－.]*"
    r"("
    r"\d{4}[-/.年]\d{1,2}(?:[-/.月]?\d{1,2})?"  # 2026.08 / 2026年8月 / 2026/8/31
    r"|"
    r"\d{6,8}"                                  # 202608 / 20260831
    r"|"
    r"(?:19|20)\d{2}"                           # 2026
    r"|"
    r"\d{4}"                                    # 2608 等 4 位 YYMM 兜底
    r")"
    r"[\s_\-–－.]*$"
)


def normalize_sheet_name(name: str, rules: NormalizeRules) -> str:
    s = str(name).strip()
    if rules.strip_index:
        # 去开头序号前缀: "2-1." "01." "1、" "1. " "01- "
        s = re.sub(r"^(?:\d+[-–_．.、])+(?:\s*)", "", s)
        s = re.sub(r"^\d+[\.．、]\s*", "", s)
    if rules.strip_period:
        # 期间后缀可能以分隔符开头(2608 / _2608 / -2608 / .2608)，先归一化分隔符再剥离
        s = re.sub(r"[\s_\-–－.]+$", "", s)
        s = _PERIOD_RE.sub("", s)
    if rules.dash_unify:
        s = s.replace("－", rules.unify_char)
        s = s.replace("–", rules.unify_char)
        s = s.replace("_", rules.unify_char)
    s = re.sub(r"\s+", " ", s).strip()
    return s or "(空)"


def is_spacer(name: str, ws: Any = None) -> bool:
    """对应 VBA IsSpacerSheet：跳过占位页。"""
    if ">>>" in str(name):
        return True
    if ws is not None:
        try:
            tc = ws.sheet_properties.tabColor
            if tc is not None and tc.rgb:
                rgb = str(tc.rgb).upper()
                if rgb.endswith("FFFF00") or rgb.endswith("FFF2CC") or rgb.endswith("FFFFCC"):
                    return True
        except Exception:
            pass
    return False


# --------------------------------------------------------------------------- #
# 列名归一化（字段映射 / 别名表）
# --------------------------------------------------------------------------- #

def _resolve_column_map(raw_columns: list[str], config: MergeConfig) -> dict[str, str]:
    """返回 {原始列名: 标准字段名}。"""
    norm_to_orig: dict[str, str] = {}
    for c in raw_columns:
        n = _normalize_header(c)
        if n not in norm_to_orig:
            norm_to_orig[n] = c

    resolved: dict[str, str] = {}  # norm -> 标准字段名(原样保留大小写)

    if config.field_map:
        for raw, target in config.field_map.items():
            rn = _normalize_header(raw)
            if rn in norm_to_orig:
                resolved[rn] = target

    if config.column_aliases:
        for target, aliases in config.column_aliases.items():
            tnorm = _normalize_header(target)
            alias_norms = [_normalize_header(a) for a in aliases]
            for rn, _orig in norm_to_orig.items():
                if rn in resolved:
                    continue
                if rn == tnorm or rn in alias_norms:
                    resolved[rn] = target
                    break

    out: dict[str, str] = {}
    for rn, orig in norm_to_orig.items():
        out[orig] = resolved.get(rn, orig)
    return out


# --------------------------------------------------------------------------- #
# 校验与去重（单行/单文件级）
# --------------------------------------------------------------------------- #

def _validate_and_dedup(
    df: pd.DataFrame,
    filename: str,
    raw_name: str,
    config: MergeConfig,
    anomalies: list[dict],
    dup_records: list[dict],
    seen_keys: dict[tuple, str],
) -> pd.DataFrame:
    # 必填字段校验
    if config.required_columns:
        for col in config.required_columns:
            if col not in df.columns:
                anomalies.append({
                    "问题类型": "缺少必需列",
                    "涉及列": col,
                    "来源文件": filename,
                    "来源工作表": raw_name,
                })
        existing = [c for c in config.required_columns if c in df.columns]
        for idx, row in df.iterrows():
            for col in existing:
                v = row.get(col)
                empty = v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == ""
                if empty:
                    anomalies.append({
                        "问题类型": "必填字段为空",
                        "涉及列": col,
                        "来源文件": filename,
                        "来源工作表": raw_name,
                        "行号": int(idx) + config.header_row + 1,
                        "值": _cell_val(v),
                    })

    # 业务主键去重（跨文件累积 seen_keys）
    if config.key_columns:
        existing_keys = [c for c in config.key_columns if c in df.columns]
        if existing_keys:
            mask: list[bool] = []
            for idx, row in df.iterrows():
                key = tuple(str(row.get(k, "")).strip() for k in existing_keys)
                if key in seen_keys:
                    rec = row.to_dict()
                    rec["_去重原因"] = "业务主键重复"
                    rec["_保留来源"] = seen_keys[key]
                    rec["_当前来源"] = filename
                    dup_records.append(rec)
                    mask.append(False)
                else:
                    seen_keys[key] = filename
                    mask.append(True)
            if mask:
                df = df[mask].copy()
            else:
                df = df.iloc[0:0]

    return df


# --------------------------------------------------------------------------- #
# 结果写入辅助
# --------------------------------------------------------------------------- #

_ERR_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
_MISS_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")


def _add_df_sheet(wb: openpyxl.Workbook, title: str, df: pd.DataFrame) -> openpyxl.worksheet.worksheet.Worksheet:
    name = _unique_sheet_name(wb, title)
    ws = wb.create_sheet(title=name)
    cols = [str(c) for c in df.columns]
    ws.append(cols)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for _, row in df.iterrows():
        ws.append([_cell_val(v) for v in row.tolist()])
    return ws


def _highlight_row(ws, row_index: int):
    for cell in ws[row_index]:
        cell.fill = _ERR_FILL


def _mark_sheet_missing(ws):
    ws.insert_rows(1)
    ws["A1"] = "⚠ 该 Sheet 在汇总数据中缺失（标红提示）"
    ws["A1"].font = Font(bold=True, color="9C0006")
    for cell in ws[1]:
        cell.fill = _MISS_FILL


def _add_report_sheets(wb, anomalies, dup_records, log_rows, missing, config):
    if anomalies:
        df = pd.DataFrame(anomalies)
        ws = _add_df_sheet(wb, "异常记录", df)
        for r in range(2, len(df) + 2):
            _highlight_row(ws, r)
    if dup_records:
        _add_df_sheet(wb, "重复记录", pd.DataFrame(dup_records))
    if config.add_log and log_rows:
        _add_df_sheet(wb, "导入日志", pd.DataFrame(log_rows))
    if missing:
        mdf = pd.DataFrame([{"缺失Sheet(逻辑名)": m, "状态": "未在任何文件中出现"} for m in missing])
        ws = _add_df_sheet(wb, "缺失Sheet报告", mdf)
        for r in range(2, len(mdf) + 2):
            _highlight_row(ws, r)


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #

def merge_excel(
    file_infos: list[dict[str, Any]],
    config: MergeConfig,
) -> tuple[bytes, dict[str, Any]]:
    """
    ExcelMergeSkill 核心。
    file_infos: [{"path","filename","sha256"}]
    返回 (xlsx_bytes, summary_dict)
    """
    if not file_infos:
        raise ValueError("至少需要提供一个文件")

    rules = config.normalize_rules
    normalize_enabled = config.sheet_match == "normalize"
    header_idx = config.header_row - 1

    groups: dict[str, list[tuple[pd.DataFrame, str, str]]] = defaultdict(list)
    first_raw: dict[str, str] = {}
    log_rows: list[dict] = []
    seen_logical: set[str] = set()
    anomalies: list[dict] = []
    dup_records: list[dict] = []

    for info in file_infos:
        path = info["path"]
        filename = info["filename"]
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)

        if config.merge_mode == "files":
            # 旧行为：每个文件取一个 Sheet，全部堆到单一"汇总"组
            if config.target_sheet and config.target_sheet in wb.sheetnames:
                candidates = [config.target_sheet]
            else:
                candidates = [wb.sheetnames[0]] if wb.sheetnames else []
            group_key = "汇总"
        else:
            # 新行为：遍历全部 Sheet，按逻辑名分组（主表-明细分别汇总）
            if config.target_sheet and config.target_sheet in wb.sheetnames:
                candidates = [config.target_sheet]
            else:
                candidates = list(wb.sheetnames)
            group_key = None  # 每 sheet 独立

        for raw_name in candidates:
            ws = wb[raw_name]
            if config.skip_spacers and is_spacer(raw_name, ws):
                log_rows.append({
                    "来源文件": filename, "原始Sheet": raw_name,
                    "逻辑Sheet": "(跳过)", "导入行数": 0, "状态": "跳过(占位页)",
                })
                continue

            logical = normalize_sheet_name(raw_name, rules) if normalize_enabled else raw_name
            key = group_key if group_key is not None else logical
            seen_logical.add(key)
            first_raw.setdefault(key, raw_name)

            try:
                df = pd.read_excel(path, sheet_name=raw_name, header=header_idx)
            except Exception as e:
                log_rows.append({
                    "来源文件": filename, "原始Sheet": raw_name,
                    "逻辑Sheet": logical, "导入行数": 0, "状态": f"读取失败: {e}",
                })
                continue

            if df.empty:
                log_rows.append({
                    "来源文件": filename, "原始Sheet": raw_name,
                    "逻辑Sheet": logical, "导入行数": 0, "状态": "空表",
                })
                continue

            col_map = _resolve_column_map(list(df.columns), config)
            df.rename(columns=col_map, inplace=True)

            groups[key].append((df, filename, raw_name))
            log_rows.append({
                "来源文件": filename, "原始Sheet": raw_name,
                "逻辑Sheet": logical, "导入行数": len(df), "状态": "已导入",
            })
        wb.close()

    if not groups:
        raise ValueError("没有可汇总的数据（请检查表头行或文件内容）")

    # 每组分别：去重 + 合并
    merged: dict[str, pd.DataFrame] = {}
    for key, items in groups.items():
        seen_keys: dict[tuple, str] = {}
        kept: list[pd.DataFrame] = []
        for df, filename, raw_name in items:
            df = _validate_and_dedup(df, filename, raw_name, config, anomalies, dup_records, seen_keys)
            if not df.empty:
                kept.append(df)
        if kept:
            combined = pd.concat(kept, ignore_index=True, sort=False)
            merged[key] = combined

    # 缺失 Sheet 检测
    missing: list[str] = []
    if config.expected_sheets:
        exp_logical = [
            normalize_sheet_name(s, rules) if normalize_enabled else s
            for s in config.expected_sheets
        ]
        for exp in exp_logical:
            if exp not in seen_logical:
                missing.append(exp)

    # 输出
    output = io.BytesIO()
    template_path = config.template_path
    if template_path and Path(template_path).exists():
        wb = openpyxl.load_workbook(template_path)
        tmap: dict[str, list[str]] = {}
        for tname in wb.sheetnames:
            tlogical = normalize_sheet_name(tname, rules) if normalize_enabled else tname
            tmap.setdefault(tlogical, []).append(tname)

        used_logical: set[str] = set()
        for tlogical, tnames in tmap.items():
            ws = wb[tnames[0]]
            header_cells = ws[config.header_row]
            template_cols = [c.value for c in header_cells]
            data = merged.get(tlogical)
            if data is not None and not data.empty:
                start = config.header_row + 1
                for ci, tcol in enumerate(template_cols, start=1):
                    tnorm = _normalize_header(tcol)
                    if tnorm in data.columns:
                        vals = data[tnorm].tolist()
                        for r, v in enumerate(vals):
                            ws.cell(row=start + r, column=ci, value=_cell_val(v))
                used_logical.add(tlogical)
            else:
                _mark_sheet_missing(ws)

        # 模板外额外逻辑组（files 模式只有"汇总"一组，若无匹配则填入首个 sheet）
        for logical, df in merged.items():
            if logical in used_logical:
                continue
            if len(merged) == 1 and len(wb.sheetnames) >= 1:
                ws = wb[wb.sheetnames[0]]
                header_cells = ws[config.header_row]
                template_cols = [c.value for c in header_cells]
                start = config.header_row + 1
                for ci, tcol in enumerate(template_cols, start=1):
                    tnorm = _normalize_header(tcol)
                    if tnorm in df.columns:
                        for r, v in enumerate(df[tnorm].tolist()):
                            ws.cell(row=start + r, column=ci, value=_cell_val(v))
            else:
                _add_df_sheet(wb, _sheet_title(logical, config, first_raw), df)

        _add_report_sheets(wb, anomalies, dup_records, log_rows, missing, config)
        wb.save(output)
    else:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        for logical, df in merged.items():
            _add_df_sheet(wb, _sheet_title(logical, config, first_raw), df)
        _add_report_sheets(wb, anomalies, dup_records, log_rows, missing, config)
        wb.save(output)

    output.seek(0)

    summary = {
        "文件数": len(file_infos),
        "逻辑Sheet数": len(merged),
        "导入日志条数": len(log_rows),
        "异常条数": len(anomalies),
        "重复条数": len(dup_records),
        "缺失Sheet数": len(missing),
        "使用模板": bool(template_path),
    }
    return output.read(), summary


def _sheet_title(logical: str, config: MergeConfig, first_raw: dict[str, str]) -> str:
    if config.output_sheet_naming == "first_raw":
        return first_raw.get(logical, logical)
    return logical
