"""API 层通用的表单参数解析工具。"""

import json

from fastapi import HTTPException


def parse_json_list(value: str | None) -> list[str] | None:
    """把前端传来的列表参数解析成 list[str]。

    兼容三种写法：
    - JSON 数组：'["部门","岗位"]'
    - 逗号分隔：'部门,岗位'
    - 单值：'部门'
    """
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [x.strip() for x in value.split(",") if x.strip()]
    if isinstance(parsed, list):
        return [str(x) for x in parsed]
    return [str(parsed)]


def parse_json_dict(value: str | None) -> dict | None:
    """把前端传来的 JSON 对象字符串解析成 dict。"""
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail=f"参数不是合法 JSON: {value}") from None


def parse_json_model(value: str | None, model):
    """把 JSON 字符串解析成指定的 pydantic 模型实例；缺省时返回空模型。"""
    if not value:
        return model()
    try:
        return model(**json.loads(value))
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"参数解析失败: {e}") from e
