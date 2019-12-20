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
    return podname + "-" + containername

def create_policy_object(k8sapi, name, namespace, file_name, policy, compressed=False):
    annotations = {}
    if compressed:
        annotations = {
            "selinux-policy-helper/compressed": ""
        }
    policy_resource = {
        "apiVersion": "selinux.openshift.io/v1alpha1",
        "kind": "SelinuxPolicy",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "annotations": annotations,
        },
        "spec": {
            "policy": policy
        }
    }
    return k8sapi.create_namespaced_custom_object(
        group="selinux.openshift.io",
        version="v1alpha1",
        namespace="default",
        plural="selinuxpolicies",
        body=policy_resource,
    )

def policy_needs_compression(policy):
    return len(policy) > 1048570

def compress_policy(policy):
    # Encode the CIL policy in ascii, compress it with gzip, b64encode it so it
    # can be stored in the configmap, and finally pass the bytes to a UTF-8
    # python3 sring.
    return base64.b64encode(gzip.compress(policy.encode('ascii'))).decode()

def get_inner_policy(policy):
    if len(policy) < 2:
        raise RuntimeError("Invalid policy read")
    first_p_idx = policy.index("(")
    second_p_idx = policy.index("(", first_p_idx + 1)
    last_p_idx = policy.rindex(")")
    return policy[second_p_idx:last_p_idx]

def main():
    """Main entrypoint"""
    kubernetes.config.load_incluster_config()

    k8sapi = kubernetes.client.CustomObjectsApi()

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

                policy = get_inner_policy(policy)
                resp = create_policy_object(k8sapi, udica_file_base,
                                               args.namespace,
                                               udica_file_base,
                                               policy, compressed=compressed)
                print(resp)
                print("SelinuxPolicy created: %s" % udica_file_base)


if __name__ == "__main__":
    main()
