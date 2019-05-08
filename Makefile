TEST_TARGETS = pytest doc_doctest


.PHONY: all doc test $(TEST_TARGETS) pylint

all: doc 

clean: doc_clean

doc:
	+$(MAKE) -C doc html

doc_clean:
	+$(MAKE) -C doc clean




test:
	for t in $(TEST_TARGETS); do $(MAKE) $$t || error=1; done; exit $$error

pytest:
	python2 -m pytest --cov=_universum --cov=universum --cov=analyzers --cov=code_report --cov=tests --cov-branch --cov-report=html --doctest-modules -vv $(DOCKER_REGISTRY_ARGS)


doc_doctest:
	+$(MAKE) -C doc doctest

pylint:
	python2 -m pylint --rcfile=pylintrc *.py _universum/ tests/
