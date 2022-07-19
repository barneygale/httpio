# Disable type checking in this repo, since there are no type annotations
MS_DOCKER_MYPY:=FALSE

# Set Twine repo to internal for this fork, rather than pushing a fork to PyPI
TWINE_REPO=https://artifactory.virt.ch.bbc.co.uk/artifactory/api/pypi/ap-python
TWINE_REPO_USERNAME?=cloudfit
TWINE_REPO_PASSWORD?=cloudfit

include static-commontooling/make/lib_static_commontooling.mk
include static-commontooling/make/standalone.mk
include static-commontooling/make/pythonic.mk
include static-commontooling/make/docker.mk
