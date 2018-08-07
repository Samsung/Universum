TEST_TARGETS = pytest source_doctest doc_doctest


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
	pytest --cov=_universum --cov=universum --cov=poll --cov=submit --cov-branch --cov-report=html -vv $(DOCKER_REGISTRY_ARGS)

source_doctest:
	pytest _universum/*.py --doctest-modules -vv

doc_doctest:
	+$(MAKE) -C doc doctest

pylint:
	pylint --rcfile=pylintrc *.py _universum/ tests/
