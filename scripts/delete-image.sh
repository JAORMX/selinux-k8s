#!/bin/bash
oc get images | grep selinux-k8s | awk '{print $1}' | xargs oc delete image
