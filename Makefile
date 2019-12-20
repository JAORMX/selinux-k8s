IMAGE_PATH?=quay.io/jaosorior/selinux-k8s
TAG?=latest
.PHONY: image
image:
	podman build -f Dockerfile -t $(IMAGE_PATH):$(TAG)

.PHONY: push
push:
	podman push $(IMAGE_PATH):$(TAG)
