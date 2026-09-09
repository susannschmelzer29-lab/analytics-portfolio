# Convenience targets. Everything works without make too.
export DBT_PROFILES_DIR := $(CURDIR)/dbt

.PHONY: seeds build test docs clean

seeds:            ## regenerate the synthetic source data
	python scripts/generate_seeds.py

build: seeds      ## seeds + models + tests, the whole thing
	cd dbt && dbt build

test:             ## tests only, against the existing warehouse
	cd dbt && dbt test

docs:             ## generate and serve the dbt documentation site
	cd dbt && dbt docs generate && dbt docs serve

clean:
	rm -rf dbt/target dbt/logs warehouse.duckdb
