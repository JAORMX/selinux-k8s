# Copyright (C) 2019 Juan Antonio Osorio Robles, <jaosorior@redhat.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import base64
import gzip
import json
import subprocess

import kubernetes

def get_args():
    parser = argparse.ArgumentParser(description='Script generates SELinux'
                                                 'policy for running k8s pod.')
    selector_group = parser.add_mutually_exclusive_group(required=True)
    selector_group.add_argument(
        '--name', type=str, help='Running pod name', dest='podname',
        default=None)
    selector_group.add_argument(
        '--label', type=str, help='label to identify the pod', dest='label',
        default=None)
    parser.add_argument(
        '--namespace', type=str, help='Running pod namespace', dest='namespace',
        default=None)
    return parser.parse_args()

def get_pod_filter(args):
    podfilter = None
    if args.podname:
        podfilter = ["--name", args.podname]
    else:
        podfilter = ["--label", args.label]
    if args.namespace:
        return podfilter + ["--namespace", args.namespace]
    return podfilter

def get_pod_id(podfilter):
    podid = subprocess.check_output(
            ["crictl", "pods", "-q"] + podfilter
        ).decode().rstrip().split("\n")
    if not podid:
        raise Exception('Pod not found with filter "%s"' % podfilter)
    return podid[0]

def get_pod_name(pod_data):
    return pod_data["status"]["metadata"]["name"]

def get_pod_data(podid):
    pod_data = subprocess.check_output(["crictl", "inspectp", podid]).decode()
    return json.loads(pod_data)

def get_unparsed_container_data(containerid):
    return subprocess.check_output(["crictl", "inspect", containerid]).decode()

def get_containers(podid):
    return subprocess.check_output(["crictl", "ps", "-q", "--pod",
                                    podid]).decode().rstrip().split("\n")

def get_container_name(container_data):
    return container_data["status"]["metadata"]["name"]

def needs_host_network(pod_data):
    return pod_data["status"]["linux"]["namespaces"]["options"]["network"] == \
            "NODE"

def get_udica_args(udicaid, pod_data):
    network_flag = []
    if needs_host_network(pod_data):
        network_flag = ["--full-network-access"]
    udica_args = ["udica", "-j", "-", udicaid]
    udica_args += network_flag
    return udica_args

def get_udica_file_base_name(podname, containername):
    return podname + "_" + containername

def create_config_map(name, file_name, policy, compressed=False):
    annotations = {}
    if compressed:
        annotations = {
            "selinux-policy-helper/compressed": ""
        }
    return kubernetes.client.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        metadata=kubernetes.client.V1ObjectMeta(
            name=name,
            annotations=annotations
        ),
        data={
            file_name + ".cil": policy
        }
    )

def policy_needs_compression(policy):
    return len(policy) > 1048570

def compress_policy(policy):
    # Encode the CIL policy in ascii, compress it with gzip, b64encode it so it
    # can be stored in the configmap, and finally pass the bytes to a UTF-8
    # python3 sring.
    return base64.b64encode(gzip.compress(policy.encode('ascii'))).decode()

def main():
    """Main entrypoint"""
    kubernetes.config.load_incluster_config()

    k8sv1api = kubernetes.client.CoreV1Api()

    args = get_args()
    podfilter = get_pod_filter(args)
    podid = get_pod_id(podfilter)
    pod_data = get_pod_data(podid)
    # We get it from here since the pod might have been selected through the
    # label
    podname = get_pod_name(pod_data)

    for containerid in get_containers(podid):
        container_raw_data = get_unparsed_container_data(containerid)
        containername = get_container_name(json.loads(container_raw_data))
        udica_file_base = get_udica_file_base_name(podname, containername)
        udica_args = get_udica_args(udica_file_base, pod_data)
        with subprocess.Popen(udica_args, stdin=subprocess.PIPE) as proc:
            print(proc.communicate(input=container_raw_data.encode())[0])
            with open(udica_file_base + ".cil", 'r') as cil:
                policy = cil.read()
                compressed = False

                if policy_needs_compression(policy):
                    policy = compress_policy(policy)
                    compressed = True

                confmap = create_config_map("policy-for-" +
                                            udica_file_base.replace("_", "-"),
                                            udica_file_base,
                                            policy, compressed=compressed)
                resp = k8sv1api.create_namespaced_config_map(
                    body=confmap,
                    namespace="selinux-policy-helper-operator")
                print("ConfigMap created: %s" % resp.metadata.name)


if __name__ == "__main__":
    main()
