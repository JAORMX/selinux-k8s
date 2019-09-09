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
import json
import subprocess

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
    return parser.parse_args()

def get_pod_filter(args):
    if args.podname:
        return ["--name", args.podname]
    return ["--label", args.label]

def get_pod_id(podfilter):
    return subprocess.check_output(
            ["crictl", "pods", "-q"] + podfilter
        ).decode().rstrip()

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

def main():
    """Main entrypoint"""
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
            print("====================")
            print("Policy for pod %s - container %s" %(podname, containername))
            print("====================\n")
            with open(udica_file_base + ".cil", 'r') as cil:
                print(cil.read())


if __name__ == "__main__":
    main()
