.PHONY: image
image:
	podman build -f Dockerfile -t selinux-k8s:latest
