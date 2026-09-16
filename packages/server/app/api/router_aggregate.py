from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from app.api._parsers import parse_json_dict, parse_json_list
from app.engines.aggregator import aggregate_excel
from app.schemas.aggregate import AggregateConfig
from app.schemas.job import ApiResponse
from app.storage.files import save_result, save_upload

router = APIRouter()


@router.post("/", response_model=ApiResponse)
async def aggregate_files(
    files: list[UploadFile] = File(...),
    mode: str = Form("stack"),
    target_sheet: str | None = Form(None),
    key_columns: str | None = Form(None),
    field_map: str | None = Form(None),
    column_aliases: str | None = Form(None),
    required_columns: str | None = Form(None),
    keep_first_on_dup: bool = Form(True),
):
    """
    多文件汇总接口。
    key_columns / required_columns 可用逗号分隔字符串或 JSON 数组。
    field_map / column_aliases 需要 JSON 对象字符串。
    """
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个 Excel 文件")

    config = AggregateConfig(
        mode=mode,  # type: ignore[arg-type]
        target_sheet=target_sheet,
        key_columns=parse_json_list(key_columns),
        field_map=parse_json_dict(field_map),
        column_aliases=parse_json_dict(column_aliases),
        required_columns=parse_json_list(required_columns),
        keep_first_on_dup=keep_first_on_dup,
    )

    # 保存并去重
    file_infos = []
    seen_sha: set[str] = set()
    duplicate_filenames: list[str] = []

    for file in files:
        if not file.filename or not file.filename.endswith((".xlsx", ".xls", ".xlsm")):
            continue
        file_id, sha256, saved_path = save_upload(file.file, file.filename)
        if sha256 in seen_sha:
            duplicate_filenames.append(file.filename)
            continue
        seen_sha.add(sha256)
        file_infos.append({"path": saved_path, "filename": file.filename, "sha256": sha256})

    if not file_infos:
        raise HTTPException(status_code=400, detail="没有有效的非重复文件")

    try:
        xlsx_bytes = aggregate_excel(file_infos, config)
        result_path = save_result(xlsx_bytes, suffix=".xlsx")
        message = "汇总完成"
        if duplicate_filenames:
            message += f"（已跳过重复文件：{', '.join(duplicate_filenames)}）"
        return ApiResponse(
            success=True,
            message=message,
            download_url=f"/api/aggregate/download?path={result_path}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"汇总失败: {e}") from e


@router.get("/download")
def download_result(path: str):
    from pathlib import Path

    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    content = file_path.read_bytes()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=aggregate_result.xlsx"},
    )
