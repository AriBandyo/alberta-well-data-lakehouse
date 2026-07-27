from __future__ import annotations

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

from .config import Settings


def create_spark_session(settings: Settings, app_name: str) -> SparkSession:
    builder = (
        SparkSession.builder.appName(app_name)
        .master(settings.spark_master)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.sql.shuffle.partitions", str(settings.spark_shuffle_partitions))
        .config("spark.databricks.delta.schema.autoMerge.enabled", "true")
        .config("spark.sql.session.timeZone", "UTC")
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()
