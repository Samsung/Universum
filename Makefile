TEST_TARGETS = pytest doctest

.PHONY: all clean doc doc_clean test $(TEST_TARGETS) pylint mypy images rebuild

all: doc

clean: doc_clean

doc:
	+$(MAKE) -C doc html

doc_clean:
	+$(MAKE) -C doc clean



test:
	for t in $(TEST_TARGETS); do $(MAKE) $$t || error=1; done; exit $$error

pytest:
	python -m pytest --doctest-modules -vv --junitxml=junit_results.xml --cov-report=html \
	--cov=universum --cov=analyzers --cov=code_report --cov=tests --cov-branch \
	--ignore=universum_log_collapser --ignore=.universum.py --ignore=noxfile.py

doctest:
	+$(MAKE) -C doc doctest

pylint:
	python -m pylint --rcfile=pylintrc *.py universum/ tests/

mypy:
	python -m mypy universum/ --ignore-missing-imports



images:
	+$(MAKE) -C tests/docker all

rebuild:
	+$(MAKE) -C tests/docker DOCKER_ARGS="--no-cache" all
