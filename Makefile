TEST_TARGETS = pytest doc_doctest


.PHONY: all doc test $(TEST_TARGETS) pylint images

all: doc

clean: doc_clean

doc:
	+$(MAKE) -C doc html

doc_clean:
	+$(MAKE) -C doc clean




test:
	for t in $(TEST_TARGETS); do $(MAKE) $$t || error=1; done; exit $$error

pytest:
	python3.7 -m pytest --doctest-modules -vv --junitxml=junit_results.xml --cov-report=html \
	--cov=universum --cov=analyzers --cov=code_report --cov=tests --cov-branch \
	--ignore=universum_log_collapser --ignore=tests/configs.py

doc_doctest:
	+$(MAKE) -C doc doctest

pylint:
	python3.7 -m pylint --rcfile=pylintrc *.py universum/ tests/

images:
	+$(MAKE) -C tests/docker all
