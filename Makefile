TEST_TARGETS = pytest doctest

IMAGE_REBUILD_TARGETS = rebuild_python3.6 rebuild_python3.7 rebuild_python3.8

.PHONY: all clean doc doc_clean test $(TEST_TARGETS) pylint mypy images $(IMAGE_REBUILD_TARGETS)

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

rebuild_python3.6:
	+$(MAKE) -C tests/docker DOCKER_ARGS="--build-arg PYTHON_VERSION=3.6 --no-cache" all

rebuild_python3.7:
	+$(MAKE) -C tests/docker DOCKER_ARGS="--build-arg PYTHON_VERSION=3.7 --no-cache" all

rebuild_python3.8:
	+$(MAKE) -C tests/docker DOCKER_ARGS="--build-arg PYTHON_VERSION=3.8 --no-cache" all
