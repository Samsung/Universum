#!/usr/bin/env bash

cd "$(dirname "$0")"

echo "Building for platform $1 $2"
if [ "$1" = "--platform_b" ] && [ "$2" = "--64" ]
then
    >&2 echo "Build failure: unsupported combination of platform and bittness"
    exit 1
fi

mkdir -p out
echo "Build result for $1 $2" > out/result$1$2.txt

echo "Build finished!"