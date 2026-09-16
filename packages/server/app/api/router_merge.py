from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from app.api._parsers import parse_json_dict, parse_json_list, parse_json_model
from app.engines.merge import merge_excel
from app.schemas.job import ApiResponse
from app.schemas.merge import MergeConfig, NormalizeRules
from app.storage.files import save_result, save_upload

router = APIRouter()


@router.post("/", response_model=ApiResponse)
async def merge_files(
    files: list[UploadFile] = File(...),
    merge_mode: str = Form("sheets"),
    sheet_match: str = Form("normalize"),
    skip_spacers: bool = Form(True),
    header_row: int = Form(1),
    target_sheet: str | None = Form(None),
    key_columns: str | None = Form(None),
    field_map: str | None = Form(None),
    column_aliases: str | None = Form(None),
    required_columns: str | None = Form(None),
    expected_sheets: str | None = Form(None),
    output_sheet_naming: str = Form("logical"),
    add_log: bool = Form(True),
    normalize_rules: str | None = Form(None),
    template: UploadFile | None = File(None),
):
    """
    ExcelMergeSkill：多文件汇总增强。
    相比 /api/aggregate，新增 Sheet 名归一化、spacer 跳过、主表-明细分组、缺失 Sheet 标红、
    导入日志、模板填充保格式。参数多用 JSON 字符串传递复杂结构。
    """
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个 Excel 文件")

    template_path: str | None = None
    if template and template.filename and template.filename.endswith((".xlsx", ".xls", ".xlsm")):
        _fid, _sha, template_path = save_upload(template.file, template.filename)

    config = MergeConfig(
        merge_mode=merge_mode,  # type: ignore[arg-type]
        sheet_match=sheet_match,  # type: ignore[arg-type]
        normalize_rules=parse_json_model(normalize_rules, NormalizeRules),
        skip_spacers=skip_spacers,
        header_row=header_row,
        target_sheet=target_sheet,
        key_columns=parse_json_list(key_columns),
        field_map=parse_json_dict(field_map),
        column_aliases=parse_json_dict(column_aliases),
        required_columns=parse_json_list(required_columns),
        expected_sheets=parse_json_list(expected_sheets),
        output_sheet_naming=output_sheet_naming,  # type: ignore[arg-type]
        add_log=add_log,
        template_path=template_path,
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
        xlsx_bytes, summary = merge_excel(file_infos, config)
        result_path = save_result(xlsx_bytes, suffix=".xlsx")
        msg = (
            f"汇总完成：{summary['文件数']} 个文件，"
            f"{summary['逻辑Sheet数']} 个逻辑 Sheet，"
            f"导入 {summary['导入日志条数']} 条记录"
        )
        if summary["异常条数"]:
            msg += f"，异常 {summary['异常条数']} 条"
        if summary["重复条数"]:
            msg += f"，去重 {summary['重复条数']} 条"
        if summary["缺失Sheet数"]:
            msg += f"，缺失 Sheet {summary['缺失Sheet数']} 个"
        if duplicate_filenames:
            msg += f"（已跳过重复：{', '.join(duplicate_filenames)}）"
        return ApiResponse(
            success=True,
            message=msg,
            download_url=f"/api/merge/download?path={result_path}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"汇总失败: {e}") from e


@router.get("/download")
def download_result(path: str):
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    content = file_path.read_bytes()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=merge_result.xlsx"},
    )
