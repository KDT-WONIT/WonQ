from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from contracts.messages import JobKind


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str
    jwt_secret: str = Field(min_length=32)
    backend_api_token: str = Field(min_length=32)
    dev_mode: bool = False
    queue_mode: Literal["database", "sqs"] = "database"
    aws_region: str = "ap-northeast-2"
    chatbot_queue_url: str = ""
    report_queue_url: str = ""
    inspection_queue_url: str = ""
    monitoring_queue_url: str = ""

    @property
    def queue_urls(self) -> dict[JobKind, str]:
        return {
            JobKind.CHATBOT: self.chatbot_queue_url,
            JobKind.REPORT: self.report_queue_url,
            JobKind.INSPECTION: self.inspection_queue_url,
            JobKind.MONITORING: self.monitoring_queue_url,
        }

    @model_validator(mode="after")
    def validate_queues(self) -> "Settings":
        if self.queue_mode == "sqs" and (
            not all(self.queue_urls.values()) or len(set(self.queue_urls.values())) != len(JobKind)
        ):
            raise ValueError("SQS mode requires four distinct queue URLs")
        return self


settings = Settings()
