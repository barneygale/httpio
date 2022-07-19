# Disable type checking in this repo, since there are no type annotations
MS_DOCKER_MYPY:=FALSE

include static-commontooling/make/lib_static_commontooling.mk
include static-commontooling/make/standalone.mk
include static-commontooling/make/pythonic.mk
include static-commontooling/make/docker.mk
