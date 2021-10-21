#!/bin/bash
REUSE_DOCKER_CONTAINERS=1 pytest -s tests/test_html_output.py::test_success[main]
