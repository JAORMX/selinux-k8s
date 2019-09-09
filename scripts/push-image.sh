#!/bin/bash
podman push --tls-verify=false localhost/selinux-k8s localhost:5000/default/selinux-k8s:latest
