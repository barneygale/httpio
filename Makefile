# Disable type checking in this repo, since there are no type annotations
MS_DOCKER_MYPY:=FALSE

# include commontooling/make/lib_static_commontooling.mk
include commontooling/make/standalone.mk
include commontooling/make/pythonic.mk
include commontooling/make/docker.mk
