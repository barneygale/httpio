#
# Makefile include file to include standard cloudfit dockerignore behaviour
# Do not include directly, is used by docker.mk


CLEAN_FILES += .dockerignore
EXTRA_GITIGNORE_LINES += .dockerignore
DOCKERIGNORE_LINES?=

.dockerignore:
	@[ ! -z "$(DOCKERIGNORE_LINES)" ] && \
	echo "\n\n# Docker ignore lines from Makefile" >> $@ && \
	set -f; for ignore_line in $(DOCKERIGNORE_LINES); do \
		echo $$ignore_line >> $@ ; \
	done
