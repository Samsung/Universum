#!/usr/bin/env bash

if [ "$1" = "pass" ]
then
    echo "Script succeeded"
    exit 0
elif [ "$1" = "fail" ]
then
    echo "Script failed"
    exit 1
else
    echo "Unknown outcome"
    exit 2
fi