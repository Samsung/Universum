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
	python3 -m pytest --doctest-modules -vv --junitxml=junit_results.xml --cov-report=html \
	--cov=_universum --cov=universum --cov=analyzers --cov=code_report --cov=tests --cov-branch


doc_doctest:
	+$(MAKE) -C doc doctest

pylint:
	python3 -m pylint --rcfile=pylintrc *.py _universum/ tests/

images:
	+$(MAKE) -C tests/docker all
