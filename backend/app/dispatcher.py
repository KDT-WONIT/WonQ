import json
import logging
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from contracts.messages import JobKind, JobMessage

from .config import settings
from .db import SessionLocal
from .models import Job

logger = logging.getLogger(__name__)


def run() -> None:
    if settings.queue_mode != "sqs":
        raise RuntimeError("The dispatcher requires QUEUE_MODE=sqs")
    sqs = boto3.client("sqs", region_name=settings.aws_region)
    while True:
        try:
            with SessionLocal() as session:
                pending = list(session.execute(
                    select(Job.id, Job.kind)
                    .where(Job.status == "queued", Job.published_at.is_(None))
                    .order_by(Job.created_at)
                    .limit(20)
                ))
            for job_id, raw_kind in pending:
                kind = JobKind(raw_kind)
                try:
                    sqs.send_message(
                        QueueUrl=settings.queue_urls[kind],
                        MessageBody=json.dumps(JobMessage(job_id, kind).as_dict()),
                    )
                except (BotoCoreError, ClientError):
                    logger.exception("SQS publish failed for job %s", job_id)
                    continue
                with SessionLocal.begin() as session:
                    session.execute(
                        update(Job)
                        .where(Job.id == job_id, Job.published_at.is_(None))
                        .values(published_at=datetime.now(timezone.utc))
                    )
        except SQLAlchemyError:
            logger.exception("Could not read or update job publication state")
        time.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
