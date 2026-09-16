import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from app.engines.validate import validate_excel
from app.schemas.job import ApiResponse
from app.schemas.validate import ValidationConfig, ValidationRule
from app.storage.files import save_result, save_upload

router = APIRouter()


def _parse_rules(value: str) -> list[ValidationRule]:
    """解析规则 JSON：支持数组、或 {"rules": [...]} 对象。"""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"规则不是合法 JSON: {e}") from e

    raw_rules = parsed.get("rules") if isinstance(parsed, dict) else parsed
    if not isinstance(raw_rules, list) or not raw_rules:
        raise HTTPException(status_code=400, detail="请至少提供一条校验规则")

    rules = []
    for i, r in enumerate(raw_rules, start=1):
        if not isinstance(r, dict):
            raise HTTPException(status_code=400, detail=f"第 {i} 条规则格式错误")
        r.setdefault("rule_id", f"R{i:03d}")
        try:
            rules.append(ValidationRule(**r))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"第 {i} 条规则参数错误: {e}") from e
    return rules


@router.post("/", response_model=ApiResponse)
async def validate_file(
    file: UploadFile = File(...),
    rules: str = Form(...),
    source_sheet: str | None = Form(None),
    header_row: int = Form(1),
    data_start_row: int | None = Form(None),
):
    """
    数据校验接口。
    rules 为规则数组 JSON，如：
    [{"rule_id":"R001","column":"金额","rule_type":"required","level":"error"}]
    """
    if not file.filename or not file.filename.endswith((".xlsx", ".xls", ".xlsm")):
        raise HTTPException(status_code=400, detail="请上传 Excel 文件")

    rule_list = _parse_rules(rules)
    config = ValidationConfig(
        source_sheet=source_sheet or None,
        header_row=header_row,
        rules=rule_list,
        data_start_row=data_start_row,
    )

    try:
        _fid, _sha, saved_path = save_upload(file.file, file.filename)
        xlsx_bytes, summary = validate_excel(saved_path, config)
        result_path = save_result(xlsx_bytes, suffix=".xlsx")
        msg = (
            f"校验完成：错误 {summary['错误']} 处，警告 {summary['警告']} 处"
            f"（共 {summary['规则数']} 条规则，{summary['数据行数']} 行数据）"
        )
        if summary["列结构问题"]:
            msg += f"；另有 {summary['列结构问题']} 个列不存在问题"
        if summary["错误"] == 0:
            msg = "✅ " + msg + "，未发现阻断性问题"
        return ApiResponse(
            success=True,
            message=msg,
            download_url=f"/api/validate/download?path={result_path}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"校验失败: {e}") from e


@router.get("/download")
def download_result(path: str):
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    content = file_path.read_bytes()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=validate_report.xlsx"},
    )
