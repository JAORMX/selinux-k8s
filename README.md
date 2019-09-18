selinux-k8s
===========

This is a small script that wraps up udica and allows you to scan containers
from a Kubernetes deployment's CRI, and generate SELinux policies from them.
The script will create a ConfigMap in the namespace where the pod is running.

Normally one would deploy this as a pod (either directly or from an operator).

An example of how to deploy this pod is provided
[in the repo](manifests/selinux-k8s.yaml). This example contains all the
relevant bind-mounts to make udica and the SELinux utilities work from the pod,
as well as the bind-mount to be able to call the CRI.

TODO
====

- [ ] Handle duplicated ConfigMaps: What happens when the ConfigMap that this
  tool is trying to create already exists? Should it overwrite, ignore or fail?

- [ ] Get capabilities for pods

- [ ] Read extra capabilities needed for a specific pod (user provided)
