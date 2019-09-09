#!/bin/bash
set -e

POD=$1


if [ -z $POD ]; then
    echo "Please provide a pod name"
    exit 1
fi

podid=$(crictl pods -q --name "$POD")

crictl inspectp "$podid"

for containerid in $(crictl ps -q --pod "$podid")
do
    crictl inspect "$containerid"
done
