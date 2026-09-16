import io
import re
import zipfile
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from app.schemas.split import SplitConfig

# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #

def _sanitize_filename(name) -> str:
    """将字符串转换为安全文件名。"""
    name = str(name).strip().replace(" ", "_")
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "unnamed"


def _apply_basic_header_style(ws, header_row: int = 1):
    for cell in ws[header_row]:
        cell.font = Font(bold=True)


# --------------------------------------------------------------------------- #
# 表头解析：定位表头行与列名
# --------------------------------------------------------------------------- #

def _read_header(path: Path, sheet_name: str, header_row: int) -> list[str]:
    """读取指定行的表头，返回列名列表（保持原始顺序与文本）。"""
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb[sheet_name]
    header = []
    for cell in ws[header_row]:
        v = cell.value
        header.append("" if v is None else str(v).strip())
    wb.close()
    return header


def _col_letter_to_index(letter: str) -> int:
    """Excel 列字母转 1-based 索引：A->1, H->8, AD->30。"""
    letter = str(letter).strip().upper()
    idx = 0
    for ch in letter:
        if "A" <= ch <= "Z":
            idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx


def _resolve_columns(spec_columns: list[str], header: list[str]) -> list[int]:
    """
    把列标识解析为 1-based 列索引。
    支持：列名（含重名取首个）、Excel 列字母（L/AD/H）。
    """
    resolved: list[int] = []
    for spec in spec_columns:
        spec = str(spec).strip()
        idx = None
        # 1) 按列名匹配
        if spec in header:
            idx = header.index(spec) + 1
        else:
            # 2) 按列字母匹配（纯字母且不超过最大列）
            if re.fullmatch(r"[A-Za-z]{1,3}", spec):
                cand = _col_letter_to_index(spec)
                if 1 <= cand <= max(len(header), 1):
                    idx = cand
        if idx is None:
            avail = ", ".join(c for c in header if c)
            raise ValueError(f"拆分列不存在: {spec}（可用列名: {avail}）")
        resolved.append(idx)
    return resolved


# --------------------------------------------------------------------------- #
# 格式保留：基于原 sheet 复制 + 删除不匹配行
# --------------------------------------------------------------------------- #

def _copy_range_with_style(
    src_ws,
    dst_wb,
    src_indices: list[int],
    dst_sheet_name: str,
    max_col: int,
    max_row: int,
):
    """部分预留：当前实现改用 _sheet_for_group。"""
    raise NotImplementedError


def _build_sheet_from_source(
    src_wb,
    src_ws,
    keep_rows: list[int],
    header_rows: list[int],
    dst_sheet_name: str,
    config: SplitConfig,
):
    """
    基于原工作表复制一份，仅保留表头行与 keep_rows 数据行，保留全部格式。
    返回新的 workbook。
    """
    new_wb = openpyxl.Workbook()
    new_wb.remove(new_wb.active)
    dst_ws = new_wb.create_sheet(title=dst_sheet_name[:31])

    keep_set = set(keep_rows)

    # 逐行复制（含样式），按 keep_rows 决定是否保留
    new_r = 0
    for r in range(1, src_ws.max_row + 1):
        is_header = r in header_rows
        is_data_kept = r in keep_set
        if not is_header and not is_data_kept:
            continue
        new_r += 1
        for c in range(1, src_ws.max_column + 1):
            src_cell = src_ws.cell(row=r, column=c)
            dst_cell = dst_ws.cell(row=new_r, column=c, value=src_cell.value)
            _copy_cell_style(src_cell, dst_cell)
        # 行高
        if r in src_ws.row_dimensions and src_ws.row_dimensions[r].height:
            dst_ws.row_dimensions[new_r].height = src_ws.row_dimensions[r].height

    # 列宽
    if config.preserve_format:
        for c in range(1, src_ws.max_column + 1):
            letter = get_column_letter(c)
            if letter in src_ws.column_dimensions:
                dim = src_ws.column_dimensions[letter]
                if dim.width:
                    dst_ws.column_dimensions[letter].width = dim.width

    # 合并单元格（仅在保留行范围内的）
    if config.preserve_format and config.preserve_merged:
        row_map = {}
        new_r = 0
        for r in range(1, src_ws.max_row + 1):
            if r in header_rows or r in keep_set:
                new_r += 1
                row_map[r] = new_r
        for mrange in list(src_ws.merged_cells.ranges):
            if mrange.min_row in row_map and mrange.max_row in row_map:
                dst_ws.merge_cells(
                    start_row=row_map[mrange.min_row],
                    end_row=row_map[mrange.max_row],
                    start_column=mrange.min_col,
                    end_column=mrange.max_col,
                )

    # 冻结表头
    if config.freeze_header:
        dst_ws.freeze_panes = f"A{config.header_row + 1}"

    return new_wb


def _copy_cell_style(src_cell, dst_cell):
    """复制单元格的全部样式（字体/填充/边框/对齐/数字格式）。"""
    if not src_cell.has_style:
        return
    from copy import copy

    dst_cell.font = copy(src_cell.font)
    dst_cell.fill = copy(src_cell.fill)
    dst_cell.border = copy(src_cell.border)
    dst_cell.alignment = copy(src_cell.alignment)
    dst_cell.number_format = src_cell.number_format
    dst_cell.protection = copy(src_cell.protection)


# --------------------------------------------------------------------------- #
# 数据读取
# --------------------------------------------------------------------------- #

def _read_dataframe(path: Path, sheet_name: str, header_row: int, keep_columns) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name, header=header_row - 1)
    df.columns = [str(c).strip() for c in df.columns]
    if keep_columns:
        keep = [c for c in keep_columns if c in df.columns]
        if keep:
            df = df[keep]
    return df


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #

def split_excel(input_path: str | Path, config: SplitConfig) -> bytes:
    """
    通用 Excel 拆分器，返回 ZIP 字节。
    支持 by_column（单列/多列组合）、by_row_count、by_sheet。
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"文件不存在: {input_path}")

    source_sheet = config.source_sheet
    if source_sheet is None:
        wb = openpyxl.load_workbook(input_path, data_only=True, read_only=True)
        source_sheet = wb.sheetnames[0]
        wb.close()

    if config.mode == "by_sheet":
        return _split_by_sheet(input_path, config)

    if config.mode == "by_row_count":
        return _split_by_row_count(input_path, config, source_sheet)

    return _split_by_column(input_path, config, source_sheet)


# --------------------------------------------------------------------------- #
# by_column：单列 / 多列组合
# --------------------------------------------------------------------------- #

def _split_by_column(input_path: Path, config: SplitConfig, source_sheet: str) -> bytes:
    header = _read_header(input_path, source_sheet, config.header_row)
    if not any(header):
        raise ValueError(f"工作表「{source_sheet}」第 {config.header_row} 行未找到表头")

    # 确定分组列
    spec_cols = config.columns or ([config.target_column] if config.target_column else None)
    if not spec_cols:
        raise ValueError("请指定拆分列（columns 或 target_column）")
    group_indices = _resolve_columns(spec_cols, header)
    group_names = [header[i - 1] for i in group_indices]

    df = _read_dataframe(input_path, source_sheet, config.header_row, config.keep_columns)

    # 检查分组列是否存在
    for name in group_names:
        if name not in df.columns:
            raise ValueError(f"拆分列不存在: {name}")

    # 构造分组键
    def make_key(row):
        return tuple(str(row.get(n, "")).strip() for n in group_names)

    # 用于展示的名称
    def make_label(key_tuple):
        return config.column_separator.join(k if k else "(空)" for k in key_tuple)

    # 分组（保持出现顺序）
    order: list[tuple] = []
    buckets: dict[tuple, list[int]] = {}
    skipped_empty = 0
    for idx, row in df.iterrows():
        key = make_key(row)
        if config.skip_empty and all(k == "" or k.lower() == "nan" for k in key):
            skipped_empty += 1
            continue
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        # Excel 行号：表头行 + 1 + 数据序号（idx 从0开始）
        buckets[key].append(config.header_row + 1 + int(idx))

    if not buckets:
        raise ValueError("没有可分组的有效数据（可能全部为空值且已启用跳过空值）")

    wb_src = openpyxl.load_workbook(input_path)  # 保留样式需可写模式
    header_rows = list(range(1, config.header_row + 1))

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, key in enumerate(order, start=1):
            rows = buckets[key]
            label = make_label(key)
            safe_value = _sanitize_filename(label)
            file_name = config.naming_template.format(
                value=safe_value, index=idx, sheet=source_sheet, count=len(rows)
            )
            if not file_name.endswith(".xlsx"):
                file_name += ".xlsx"

            if config.preserve_format:
                out_wb = _build_sheet_from_source(
                    wb_src, wb_src[source_sheet], rows, header_rows,
                    dst_sheet_name=source_sheet, config=config,
                )
                out_buf = io.BytesIO()
                out_wb.save(out_buf)
                out_wb.close()
                zf.writestr(file_name, out_buf.getvalue())
            else:
                sub = df.loc[[
                    r for r in df.index
                    if config.header_row + 1 + int(r) in set(rows)
                ]]
                if config.add_source_info:
                    sub = sub.copy()
                    sub["_来源文件"] = input_path.name
                    sub["_来源工作表"] = source_sheet
                zf.writestr(
                    file_name,
                    _dataframe_to_excel_bytes(sub, source_sheet, config.header_row),
                )

    wb_src.close()
    buffer.seek(0)
    return buffer.read()


# --------------------------------------------------------------------------- #
# by_row_count
# --------------------------------------------------------------------------- #

def _split_by_row_count(input_path: Path, config: SplitConfig, source_sheet: str) -> bytes:
    df = _read_dataframe(input_path, source_sheet, config.header_row, config.keep_columns)
    chunk_size = config.row_count or 100
    total = len(df)

    wb_src = openpyxl.load_workbook(input_path)
    header_rows = list(range(1, config.header_row + 1))

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, start in enumerate(range(0, total, chunk_size), start=1):
            end = min(start + chunk_size, total)
            first_excel = config.header_row + 1 + start
            last_excel = config.header_row + end
            rows = list(range(first_excel, last_excel + 1))
            file_name = config.naming_template.format(
                value=f"{start+1}-{end}", index=idx, sheet=source_sheet, count=len(rows)
            )
            if not file_name.endswith(".xlsx"):
                file_name += ".xlsx"

            if config.preserve_format:
                out_wb = _build_sheet_from_source(
                    wb_src, wb_src[source_sheet], rows, header_rows,
                    dst_sheet_name=source_sheet, config=config,
                )
                out_buf = io.BytesIO()
                out_wb.save(out_buf)
                out_wb.close()
                zf.writestr(file_name, out_buf.getvalue())
            else:
                sub = df.iloc[start:end]
                if config.add_source_info:
                    sub = sub.copy()
                    sub["_来源文件"] = input_path.name
                    sub["_来源工作表"] = source_sheet
                zf.writestr(
                    file_name,
                    _dataframe_to_excel_bytes(sub, source_sheet, config.header_row),
                )

    wb_src.close()
    buffer.seek(0)
    return buffer.read()


# --------------------------------------------------------------------------- #
# by_sheet
# --------------------------------------------------------------------------- #

def _split_by_sheet(input_path: Path, config: SplitConfig) -> bytes:
    wb = openpyxl.load_workbook(input_path)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, sheet_name in enumerate(wb.sheetnames, start=1):
            src_ws = wb[sheet_name]
            new_wb = openpyxl.Workbook()
            new_wb.remove(new_wb.active)
            new_ws = new_wb.create_sheet(title=sheet_name[:31])
            _copy_sheet_full(src_ws, new_ws, config)

            file_name = config.naming_template.format(
                value=_sanitize_filename(sheet_name),
                index=idx,
                sheet=sheet_name,
                count=src_ws.max_row,
            )
            if not file_name.endswith(".xlsx"):
                file_name += ".xlsx"

            out_buf = io.BytesIO()
            new_wb.save(out_buf)
            new_wb.close()
            zf.writestr(file_name, out_buf.getvalue())
    wb.close()
    buffer.seek(0)
    return buffer.read()


def _copy_sheet_full(src_ws, dst_ws, config: SplitConfig):
    """整表复制，保留格式。"""
    for r in range(1, src_ws.max_row + 1):
        for c in range(1, src_ws.max_column + 1):
            src_cell = src_ws.cell(row=r, column=c)
            dst_cell = dst_ws.cell(row=r, column=c, value=src_cell.value)
            if config.preserve_format:
                _copy_cell_style(src_cell, dst_cell)
        if r in src_ws.row_dimensions and src_ws.row_dimensions[r].height:
            dst_ws.row_dimensions[r].height = src_ws.row_dimensions[r].height
    if config.preserve_format:
        for c in range(1, src_ws.max_column + 1):
            letter = get_column_letter(c)
            if letter in src_ws.column_dimensions and src_ws.column_dimensions[letter].width:
                dst_ws.column_dimensions[letter].width = src_ws.column_dimensions[letter].width
        if config.preserve_merged:
            for mrange in list(src_ws.merged_cells.ranges):
                dst_ws.merge_cells(
                    start_row=mrange.min_row, end_row=mrange.max_row,
                    start_column=mrange.min_col, end_column=mrange.max_col,
                )


# --------------------------------------------------------------------------- #
# 兜底：pandas 输出（不保留格式）
# --------------------------------------------------------------------------- #

def _dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str, header_row: int = 1) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31], startrow=header_row - 1)
        ws = writer.sheets[sheet_name[:31]]
        _apply_basic_header_style(ws, header_row)
    buffer.seek(0)
    return buffer.read()
