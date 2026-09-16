import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Response

from app.engines.splitter import split_excel
from app.schemas.job import ApiResponse
from app.schemas.split import SplitConfig
from app.storage.files import save_result, save_upload

router = APIRouter()


@router.post("/", response_model=ApiResponse)
async def split_file(
    file: UploadFile = File(...),
    mode: str = Form("by_column"),
    source_sheet: str | None = Form(None),
    target_column: str | None = Form(None),
    columns: str | None = Form(None),
    column_separator: str = Form("_"),
    row_count: int | None = Form(None),
    keep_columns: str | None = Form(None),
    naming_template: str = Form("{value}"),
    header_row: int = Form(1),
    skip_empty: bool = Form(True),
    add_source_info: bool = Form(True),
    preserve_format: bool = Form(True),
    preserve_merged: bool = Form(True),
    freeze_header: bool = Form(False),
):
    """
    通用 Excel 拆分接口。
    - keep_columns / columns 以逗号分隔，如 "部门,岗位"。
    - columns 支持列名或 Excel 列字母（如 L,AD,H），用于多列组合拆分。
    - naming_template 支持 {value} / {index} / {sheet} / {count}（笔数）。
    """
    if not file.filename or not file.filename.endswith((".xlsx", ".xls", ".xlsm")):
        raise HTTPException(status_code=400, detail="请上传 Excel 文件")

    def _split_list(v: str | None):
        """兼容三种写法：JSON 数组 ["a","b"]、逗号分隔 "a,b"、单个值 "a"。"""
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

    config = SplitConfig(
        mode=mode,  # type: ignore[arg-type]
        source_sheet=source_sheet or None,
        target_column=target_column or None,
        columns=_split_list(columns),
        column_separator=column_separator or "_",
        row_count=row_count,
        keep_columns=_split_list(keep_columns),
        naming_template=naming_template,
        header_row=header_row,
        skip_empty=skip_empty,
        add_source_info=add_source_info,
        preserve_format=preserve_format,
        preserve_merged=preserve_merged,
        freeze_header=freeze_header,
    )

    try:
        file_id, _, saved_path = save_upload(file.file, file.filename)
        zip_bytes = split_excel(saved_path, config)
        result_path = save_result(zip_bytes, suffix=".zip")
        return ApiResponse(
            success=True,
            message="拆分完成",
            download_url=f"/api/split/download?path={result_path}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"拆分失败: {e}") from e


@router.get("/download")
def download_result(path: str):
    from pathlib import Path

    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    content = file_path.read_bytes()
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=split_result.zip"},
    )
