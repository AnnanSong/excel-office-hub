import io
from pathlib import Path
from typing import Any

import openpyxl
import pandas as pd
from openpyxl.styles import Font, PatternFill

from app.schemas.aggregate import AggregateConfig


def _normalize_header(name: Any) -> str:
    return str(name).strip().replace("\n", " ").replace("\t", " ")


def _resolve_column_map(raw_columns: list[str], config: AggregateConfig) -> dict[str, str]:
    """
    将原始列名映射到标准字段。
    优先级：显式 field_map > 别名表 > 原始列名。
    """
    raw_map = {col: _normalize_header(col) for col in raw_columns}
    resolved: dict[str, str] = {}
    used_targets: set[str] = set()

    # 1. 显式 field_map
    if config.field_map:
        for raw, target in config.field_map.items():
            raw_norm = _normalize_header(raw)
            if raw_norm in raw_map:
                resolved[raw_norm] = target
                used_targets.add(target)

    # 2. 别名表
    if config.column_aliases:
        target_to_aliases: dict[str, list[str]] = {}
        for target, aliases in config.column_aliases.items():
            target_to_aliases[_normalize_header(target)] = [_normalize_header(a) for a in aliases]

        for raw_col, raw_norm in raw_map.items():
            if raw_norm in resolved:
                continue
            for target, aliases in target_to_aliases.items():
                if raw_norm == target or raw_norm in aliases:
                    resolved[raw_norm] = target
                    used_targets.add(target)
                    break

    # 3. 未匹配的保留原始名
    for raw_col, raw_norm in raw_map.items():
        if raw_norm not in resolved:
            resolved[raw_norm] = raw_norm

    return resolved


def _mark_header(ws):
    for cell in ws[1]:
        cell.font = Font(bold=True)


def _highlight_error(ws, row_index: int):
    for cell in ws[row_index]:
        cell.fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")


def aggregate_excel(
    file_infos: list[dict[str, Any]],
    config: AggregateConfig,
) -> bytes:
    """
    多文件汇总器。
    file_infos: [{"path": str, "filename": str, "sha256": str}]
    返回 xlsx 字节，包含 汇总 / 异常记录 / 重复记录。
    """
    if not file_infos:
        raise ValueError("至少需要提供一个文件")

    target_sheet = config.target_sheet
    all_records: list[pd.DataFrame] = []
    anomaly_records: list[dict] = []
    duplicate_key_records: list[dict] = []
    seen_keys: dict[tuple, dict] = {}

    for info in file_infos:
        path = info["path"]
        filename = info["filename"]

        # 读取指定 sheet 或第一个
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        sheet_name = target_sheet if target_sheet and target_sheet in wb.sheetnames else wb.sheetnames[0]
        wb.close()

        df = pd.read_excel(path, sheet_name=sheet_name)
        if df.empty:
            continue

        # 标准化列名
        original_columns = list(df.columns)
        column_map = _resolve_column_map(original_columns, config)
        df.rename(columns=column_map, inplace=True)

        # 记录未映射的原始列（field_map/别名表都未命中且不是原始名自身）
        for raw_col in original_columns:
            raw_norm = _normalize_header(raw_col)
            mapped = column_map.get(raw_norm, raw_norm)
            if config.field_map and raw_norm in config.field_map and mapped != config.field_map[raw_norm]:
                # 被 field_map 指定但列不存在，已在上方处理为未命中
                pass

        # 添加来源信息
        df["_来源文件"] = filename
        df["_来源工作表"] = sheet_name

        # 校验：必需字段缺失
        if config.required_columns:
            for col in config.required_columns:
                if col not in df.columns:
                    anomaly_records.append({
                        "_问题类型": "缺少必需列",
                        "_涉及列": col,
                        "_来源文件": filename,
                        "_来源工作表": sheet_name,
                        "_原始列名": ", ".join(original_columns),
                    })

        # 行级异常：必需字段为空
        if config.required_columns:
            existing_required = [c for c in config.required_columns if c in df.columns]
            for idx, row in df.iterrows():
                for col in existing_required:
                    if pd.isna(row.get(col)) or str(row.get(col)).strip() == "":
                        anomaly_records.append({
                            "_问题类型": "必填字段为空",
                            "_涉及列": col,
                            "_来源文件": filename,
                            "_来源工作表": sheet_name,
                            "_行号": int(idx) + 2,
                            "_值": row.get(col),
                        })

        # 业务主键去重
        if config.key_columns:
            existing_keys = [c for c in config.key_columns if c in df.columns]
            if existing_keys:
                keep_mask = []
                for idx, row in df.iterrows():
                    key_tuple = tuple(str(row.get(k, "")).strip() for k in existing_keys)
                    if key_tuple in seen_keys:
                        dup_record = row.to_dict()
                        dup_record["_去重原因"] = "业务主键重复"
                        dup_record["_保留来源"] = seen_keys[key_tuple]["filename"]
                        duplicate_key_records.append(dup_record)
                        keep_mask.append(False)
                    else:
                        seen_keys[key_tuple] = {"filename": filename, "row": int(idx)}
                        keep_mask.append(True)
                df = df[keep_mask].copy()

        all_records.append(df)

    if not all_records:
        raise ValueError("没有可汇总的数据")

    # 合并
    combined = pd.concat(all_records, ignore_index=True, sort=False)

    # 重新排列列：把来源信息放最后
    meta_cols = ["_来源文件", "_来源工作表"]
    data_cols = [c for c in combined.columns if c not in meta_cols]
    combined = combined[data_cols + [c for c in meta_cols if c in combined.columns]]

    # 构建输出 workbook
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        combined.to_excel(writer, index=False, sheet_name="汇总")
        _mark_header(writer.sheets["汇总"])

        if anomaly_records:
            anomaly_df = pd.DataFrame(anomaly_records)
            anomaly_df.to_excel(writer, index=False, sheet_name="异常记录")
            _mark_header(writer.sheets["异常记录"])
            for r in range(2, len(anomaly_df) + 2):
                _highlight_error(writer.sheets["异常记录"], r)

        if duplicate_key_records:
            dup_df = pd.DataFrame(duplicate_key_records)
            dup_df.to_excel(writer, index=False, sheet_name="重复记录")
            _mark_header(writer.sheets["重复记录"])

    output.seek(0)
    return output.read()
