from fastapi import APIRouter, Form, HTTPException, Response

from app.engines.create_sheets import create_sheets
from app.schemas.create_sheets import CreateSheetsConfig
from app.schemas.job import ApiResponse
from app.storage.files import save_result

router = APIRouter()


def _parse_names(names: str) -> list[str]:
    """支持逗号分隔或换行分隔。"""
    result = []
    for line in names.replace(",", "\n").split("\n"):
        line = line.strip()
        if line:
            result.append(line)
    return result


def _parse_headers(headers: str | None) -> list[str] | None:
    if not headers:
        return None
    return [h.strip() for h in headers.replace(",", "\n").split("\n") if h.strip()]


@router.post("/", response_model=ApiResponse)
async def create_sheets_endpoint(
    names: str = Form(...),
    headers: str | None = Form(None),
):
    """
    批量创建指定名称工作表。
    names 支持逗号或换行分隔；headers 为默认表头，同样支持逗号或换行分隔。
    """
    name_list = _parse_names(names)
    if not name_list:
        raise HTTPException(status_code=400, detail="请提供至少一个工作表名称")

    config = CreateSheetsConfig(names=name_list, headers=_parse_headers(headers))

    try:
        xlsx_bytes = create_sheets(config)
        result_path = save_result(xlsx_bytes, suffix=".xlsx")
        return ApiResponse(
            success=True,
            message=f"已创建 {len(name_list)} 个工作表",
            download_url=f"/api/create-sheets/download?path={result_path}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {e}") from e


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
        headers={"Content-Disposition": f"attachment; filename=created_sheets.xlsx"},
    )
