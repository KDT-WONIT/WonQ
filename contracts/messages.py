from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class JobKind(StrEnum):
    CHATBOT = "chatbot"
    REPORT = "report"
    INSPECTION = "inspection"
    MONITORING = "monitoring"


@dataclass(frozen=True)
class JobMessage:
    job_id: UUID
    kind: JobKind

    def as_dict(self) -> dict:
        return {"schema_version": 1, "job_id": str(self.job_id), "kind": self.kind.value}

    @classmethod
    def from_dict(cls, body: dict) -> "JobMessage":
        if type(body.get("schema_version")) is not int or body["schema_version"] != 1:
            raise ValueError("Unsupported job message version")
        return cls(job_id=UUID(body["job_id"]), kind=JobKind(body["kind"]))
