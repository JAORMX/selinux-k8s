#!/bin/bash
oc create serviceaccount selinux-operator

oc adm policy add-scc-to-user privileged -z selinux-operator
