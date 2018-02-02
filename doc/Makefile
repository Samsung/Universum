# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = TestDoc
SOURCEDIR     = .
BUILDDIR      = _build


SPHINX_AVAILABLE := $(shell command -v $(SPHINXBUILD) 2> /dev/null)

ifndef SPHINX_AVAILABLE
    $(error Sphinx is not available, please install it using the following command-line: sudo pip install sphinx)
endif

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)