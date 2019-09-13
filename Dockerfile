FROM udica:latest

USER root

# CRI-O dependencies
RUN dnf module enable -y cri-o:1.14 && \
    dnf install --disableplugin=subscription-manager -y \
        cri-tools \
        python3-kubernetes \
    && rm -rf /var/cache/yum

# build selinux-k8s
WORKDIR /tmp
COPY selinux_k8s/ selinux_k8s/selinux_k8s/
COPY setup.py selinux_k8s/
WORKDIR /tmp/selinux_k8s
RUN python3 setup.py install
WORKDIR /

# Clean up
RUN rm -rf /tmp/selinux_k8s/

ENTRYPOINT ["/usr/bin/selinuxk8s"]
