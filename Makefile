PYTHON_VERSION :=

ifeq ($(PYTHON_VERSION),)
long_version = $(shell python --version)
ifneq ($(long_version),)
version_list = $(subst ., ,$(long_version))
PYTHON_VERSION :=  $(word 2,${version_list}).$(word 3,$(version_list))
else
PYTHON_VERSION := 3.7
endif
endif

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
	+$(MAKE) -C tests/docker DOCKER_ARGS="--build-arg PYTHON_VERSION="$(PYTHON_VERSION)" --no-cache" all
