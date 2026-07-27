from __future__ import annotations

from pathlib import Path

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T

from .config import Settings
from .spark import create_spark_session

SCHEMA = T.StructType(
    [
        T.StructField("municipality", T.StringType(), False),
        T.StructField("year", T.IntegerType(), False),
        T.StructField("metric", T.StringType(), False),
        T.StructField("value", T.DoubleType(), False),
        T.StructField("unit", T.StringType(), False),
        T.StructField("yoy_change_pct", T.DoubleType(), True),
        T.StructField("five_year_change_pct", T.DoubleType(), True),
        T.StructField("source_name", T.StringType(), False),
        T.StructField("source_url", T.StringType(), False),
        T.StructField("source_last_updated", T.StringType(), False),
        T.StructField("licence", T.StringType(), False),
        T.StructField("snapshot_retrieved_at", T.StringType(), False),
    ]
)


def merge_delta(spark: SparkSession, frame: DataFrame, target: Path) -> None:
    key = "target.municipality_key = source.municipality_key AND target.year = source.year AND target.metric = source.metric"
    if DeltaTable.isDeltaTable(spark, str(target)):
        DeltaTable.forPath(spark, str(target)).alias("target").merge(
            frame.alias("source"), key
        ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
    else:
        frame.write.format("delta").mode("overwrite").save(str(target))


def run(root: Path) -> dict[str, int]:
    settings = Settings.from_env()
    spark = create_spark_session(settings, "alberta-public-energy-snapshot")
    try:
        source_dir = root / "data" / "source_snapshot"
        files = [
            source_dir / "oil_production_by_municipality_2025.csv",
            source_dir / "natural_gas_production_by_municipality_2025.csv",
            source_dir / "well_count_by_municipality_2024.csv",
        ]
        bronze = None
        for source in files:
            current = (
                spark.read.option("header", True)
                .schema(SCHEMA)
                .csv(str(source))
                .withColumn("source_file", F.lit(source.name))
                .withColumn("ingested_at_utc", F.current_timestamp())
            )
            bronze = current if bronze is None else bronze.unionByName(current)
        assert bronze is not None
        bronze_target = root / "lakehouse" / "bronze" / "official_energy_activity"
        merge_delta(
            spark,
            bronze.withColumn(
                "municipality_key",
                F.sha2(
                    F.lower(F.regexp_replace(F.trim("municipality"), "[^A-Za-z0-9]+", "_")), 256
                ),
            ),
            bronze_target,
        )

        silver = (
            spark.read.format("delta")
            .load(str(bronze_target))
            .dropDuplicates(["municipality", "year", "metric"])
            .filter(F.col("value") >= 0)
            .withColumn("source_last_updated", F.to_date("source_last_updated"))
            .withColumn("snapshot_retrieved_at", F.to_date("snapshot_retrieved_at"))
        )
        silver_target = root / "lakehouse" / "silver" / "official_energy_activity"
        merge_delta(spark, silver, silver_target)
        export = root / "warehouse" / "silver_exports" / "official_energy_activity"
        silver.write.mode("overwrite").parquet(str(export))
        return {"bronze_rows": bronze.count(), "silver_rows": silver.count()}
    finally:
        spark.stop()
