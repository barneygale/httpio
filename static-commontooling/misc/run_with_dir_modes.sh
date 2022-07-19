#!/bin/bash

if (( $# < 2 )); then
    echo "Useage: $0 <DIR> <CMD> [<ARG>]..."
    echo ""
    echo "Run the specified CMD with the specified ARGs. Regardless of whether"
    echo "it succeeeds or fails afterwards recursively chown the specified DIR"
    echo "and all its contents to be owned by the user and group that owned DIR"
    echo "when the script was entered. Then return with the same return code that"
    echo "CMD had."
    exit 1
fi


DIR=$1
shift
CMD=$1
shift

USER=$(stat -c '%u' $DIR)
GROUP=$(stat -c '%g' $DIR)

$CMD $@
RESULT=$?

chown -R $USER:$GROUP $DIR

exit $RESULT
