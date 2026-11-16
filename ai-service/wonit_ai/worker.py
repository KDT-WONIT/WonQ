import json
import logging
import os
import time
from uuid import UUID

import boto3
import httpx
from botocore.exceptions import BotoCoreError, ClientError

from contracts.messages import JobKind, JobMessage

from .handlers import HANDLERS

logger = logging.getLogger(__name__)


def process(client: httpx.Client, kind: JobKind, job_id: UUID | None = None) -> bool:
    claim = {"kind": kind.value}
    if job_id is not None:
        claim["job_id"] = str(job_id)
    response = client.post("/internal/worker/jobs/claim", json=claim)
    response.raise_for_status()
    job = response.json()

    if job["state"] == "terminal":
        return True
    if job["state"] != "claimed":
        return False

    try:
        result = HANDLERS[kind](job["context"])
        succeeded = True
    except Exception:
        logger.exception("Handler failed for job %s", job["job_id"])
        result = {"error": "작업 처리에 실패했습니다."}
        succeeded = False

    response = client.post(
        f"/internal/worker/jobs/{job['job_id']}/complete",
        json={"lease_token": job["lease_token"], "succeeded": succeeded, "result": result},
    )
    response.raise_for_status()
    return response.json()["status"] in {"completed", "failed"}


def consume_sqs(client: httpx.Client, kind: JobKind, queue_url: str) -> None:
    sqs = boto3.client("sqs", region_name=os.getenv("AWS_REGION", "ap-northeast-2"))
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                WaitTimeSeconds=20,
                MaxNumberOfMessages=1,
                VisibilityTimeout=150,
            )
            for receipt in response.get("Messages", []):
                try:
                    message = JobMessage.from_dict(json.loads(receipt["Body"]))
                    if message.kind != kind:
                        raise ValueError("Message kind does not match worker")
                except (AttributeError, KeyError, TypeError, ValueError):
                    logger.warning("Invalid message %s remains in the queue for redrive", receipt["MessageId"])
                    continue
                if process(client, kind, message.job_id):
                    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt["ReceiptHandle"])
        except (httpx.HTTPError, BotoCoreError, ClientError):
            logger.exception("Could not consume a queue message")
            time.sleep(2)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    kind = JobKind(os.environ["WORKER_KIND"])
    queue_mode = os.getenv("QUEUE_MODE", "database")
    if queue_mode not in {"sqs", "database"}:
        raise ValueError("QUEUE_MODE must be sqs or database")
    with httpx.Client(
        base_url=os.environ["BACKEND_API_URL"],
        headers={"Authorization": f"Bearer {os.environ['BACKEND_API_TOKEN']}"},
        timeout=10,
    ) as client:
        logger.info("Starting %s worker in %s mode", kind, queue_mode)
        if queue_mode == "sqs":
            consume_sqs(client, kind, os.environ["SQS_QUEUE_URL"])
            return
        while True:
            try:
                if not process(client, kind):
                    time.sleep(1)
            except httpx.HTTPError:
                logger.exception("Could not process a local job")
                time.sleep(2)


if __name__ == "__main__":
    main()
