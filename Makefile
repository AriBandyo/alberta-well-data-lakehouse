PYTHON ?= python

.PHONY: install check public-data spark-public dbt dagster test lint clean refresh-oil refresh-gas refresh-wells

install:
	$(PYTHON) -m pip install --upgrade pip setuptools wheel
	$(PYTHON) -m pip install -r requirements.txt

check:
	$(PYTHON) scripts/check_environment.py

public-data:
	$(PYTHON) scripts/build_public_data_project.py

spark-public:
	$(PYTHON) scripts/run_public_spark_pipeline.py

dbt: public-data
	PUBLIC_FACT_CSV=$(CURDIR)/warehouse/gold/fct_energy_activity.csv WAREHOUSE_DB_PATH=$(CURDIR)/warehouse/alberta_well_analytics.duckdb dbt build --project-dir dbt/alberta_well_analytics --profiles-dir dbt/alberta_well_analytics

dagster:
	dagster dev -m orchestration.definitions

refresh-oil:
	$(PYTHON) scripts/download_free_sources.py regional-oil

refresh-gas:
	$(PYTHON) scripts/download_free_sources.py regional-gas

refresh-wells:
	$(PYTHON) scripts/download_free_sources.py regional-wells

test:
	pytest -q

lint:
	ruff check src orchestration scripts tests

clean:
	rm -rf lakehouse/bronze/public_snapshot lakehouse/silver/public_snapshot warehouse/gold warehouse/*.sqlite warehouse/*.duckdb results tableau/data
