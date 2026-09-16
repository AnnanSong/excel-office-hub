import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from app.engines.compare import compare_excel
from app.schemas.compare import CompareConfig
from app.schemas.job import ApiResponse
from app.storage.files import save_result, save_upload

router = APIRouter()


def _split_list(v: str | None) -> list[str] | None:
    """兼容 JSON 数组 / 逗号分隔 / 单个值。"""
    if not v:
        return None
    s = v.strip()
    if s.startswith("["):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            pass
    return [c.strip() for c in s.split(",") if c.strip()]


@router.post("/", response_model=ApiResponse)
async def compare_files(
    old_file: UploadFile = File(...),
    new_file: UploadFile = File(...),
    key_columns: str = Form(...),
    compare_columns: str | None = Form(None),
    source_sheet: str | None = Form(None),
    old_sheet: str | None = Form(None),
    new_sheet: str | None = Form(None),
    header_row: int = Form(1),
    ignore_whitespace: bool = Form(True),
    ignore_case: bool = Form(False),
    numeric_tolerance: float = Form(0.0),
    output_mode: str = Form("summary"),
    include_unchanged: bool = Form(False),
):
    """
    数据比对接口：按关键字段匹配旧版/新版两版数据，输出新增/删除/修改差异。
    key_columns / compare_columns 支持逗号分隔或 JSON 数组。
    """
    for f, label in ((old_file, "旧版"), (new_file, "新版")):
        if not f.filename or not f.filename.endswith((".xlsx", ".xls", ".xlsm")):
            raise HTTPException(status_code=400, detail=f"请上传{label} Excel 文件")

    key_list = _split_list(key_columns)
    if not key_list:
        raise HTTPException(status_code=400, detail="请指定关键字段（key_columns）")

    config = CompareConfig(
        key_columns=key_list,
        compare_columns=_split_list(compare_columns),
        source_sheet=source_sheet or None,
        old_sheet=old_sheet or None,
        new_sheet=new_sheet or None,
        header_row=header_row,
        ignore_whitespace=ignore_whitespace,
        ignore_case=ignore_case,
        numeric_tolerance=numeric_tolerance,
        output_mode=output_mode,  # type: ignore[arg-type]
        include_unchanged=include_unchanged,
    )

    try:
        _fid1, _sha1, old_path = save_upload(old_file.file, old_file.filename)
        _fid2, _sha2, new_path = save_upload(new_file.file, new_file.filename)
        xlsx_bytes, summary = compare_excel(old_path, new_path, config)
        result_path = save_result(xlsx_bytes, suffix=".xlsx")
        msg = (
            f"比对完成：新增 {summary['新增']} 条，删除 {summary['删除']} 条，"
            f"修改 {summary['修改字段数']} 处"
            f"（旧版 {summary['旧版行数']} 行 / 新版 {summary['新版行数']} 行）"
        )
        if summary["旧版重复key"] or summary["新版重复key"]:
            old_dup = summary["旧版重复key"]
            new_dup = summary["新版重复key"]
            msg += f"；注意存在重复关键字段（旧 {old_dup} / 新 {new_dup}）"
        return ApiResponse(
            success=True,
            message=msg,
            download_url=f"/api/compare/download?path={result_path}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"比对失败: {e}") from e


@router.get("/download")
def download_result(path: str):
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    content = file_path.read_bytes()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=compare_result.xlsx"},
    )
