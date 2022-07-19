#
# Makefile include file to copy some files from commontooling/misc across to $(topdir)
#
# Before including this file may want to set any of the following variables:
#
#   MISC_FILES?=
#       A list of files in $(topdir) to be created
#

MISC_FILES?=
MISC_SOURCE_FILES?=$(patsubst $(topdir)/%,$(commontooling_dir)/misc/%,$(MISC_FILES))
CLEAN_FILES += $(MISC_FILES)

$(MISC_FILES): $(MISC_SOURCE_FILES)
	cp -f $(commontooling_dir)/misc/${notdir $@} $@

prepcode: $(MISC_FILES)
