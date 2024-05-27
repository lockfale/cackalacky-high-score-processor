import json
import logging.config
import os
import socket
from functools import lru_cache

import redis
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

import config
from connectors.pgsql import PostgreSQLConnector
from game.challenge import process_challenge_score
from game.scores import process_high_scores, submit_around_the_world
from s3_logger import S3TimedRotatingFileHandler

# Get the host name of the machine
host_name = socket.gethostname()
logging.config.fileConfig("log.ini")
logger = logging.getLogger("s3logger")

# Setup OpenTelemetry
resource = Resource.create(
    {
        "service.name": "high-score-processor",
    }
)
exporter = OTLPMetricExporter(endpoint=f"http://{os.getenv('OTEL_COLLECTOR_SVC')}:4317", insecure=True)
metric_reader = PeriodicExportingMetricReader(exporter)
provider = MeterProvider(metric_readers=[metric_reader], resource=resource)

# Sets the global default meter provider
metrics.set_meter_provider(provider)

# Creates a meter from the global meter provider
meter = metrics.get_meter("hsp.sync")

# A simple counter metric
sync_counter = meter.create_counter(
    "processed",
    description="Number of high scores processed",
)
logger.info(sync_counter)

logger = logging.getLogger("s3logger")
logger.setLevel(logging.INFO)
hostname = socket.gethostname()
s3_handler = S3TimedRotatingFileHandler(
    f"{hostname}.log",
    bucket_name=os.getenv("BUCKET_NAME"),
    aws_access_key_id=os.getenv("AWS_LOGGER_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_LOGGER_SECRET_KEY"),
    when="M",
    interval=1,
    backupCount=5,
)
formatter = logging.Formatter("[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(filename)s:%(lineno)d]: %(message)s")
s3_handler.setFormatter(formatter)
logger.addHandler(s3_handler)


@lru_cache()
def get_settings():
    return config.SettingsFromEnvironment()


def process_messages_from_queue(message: str) -> None:
    """

    Parameters
    ----------
    message: str
    """
    pgsql_db = PostgreSQLConnector()
    pgsql_db.connect(get_settings())
    logger.info(message)
    try:
        parsed_message = json.loads(str(message))
        logger.info(parsed_message)
        uuid = parsed_message.get("user_uuid")
        mac_address = parsed_message.get("mac_address")
        event = parsed_message.get("event")
        if event == "high-score":
            high_scores = parsed_message.get("high_scores")
            process_high_scores(pgsql_db, uuid, mac_address, high_scores)
        if event == "around-the-world":
            logger.info("checking around the world...")
            submit_around_the_world(pgsql_db, uuid, mac_address)
        if event == "challenge-check":
            logger.info("checking for challenge...")
            score_id = parsed_message.get("score_id")
            process_challenge_score(pgsql_db, uuid, mac_address, score_id)

        if event:
            sync_counter.add(1, {"host": host_name, "event": event})
    except Exception as e:
        logger.error(e)
        return


def syncer_processor() -> None:
    """The infinite process loop. Don't stop little buddy."""
    logger.info("Starting processor...")
    rd_con = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)
    mobile = rd_con.pubsub()
    mobile.subscribe("high-score-processor")

    for message in mobile.listen():
        logger.info(message)
        try:
            process_messages_from_queue(str(message.get("data").decode()))
        except Exception as e:
            logger.error(e)


if __name__ == "__main__":
    syncer_processor()
