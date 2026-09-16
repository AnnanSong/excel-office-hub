from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobOut(BaseModel):
    id: int
    job_type: str
    status: str
    output_file: str | None = None
    message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiResponse(BaseModel):
    success: bool = True
    data: Any | None = None
    message: str | None = None
    download_url: str | None = None
