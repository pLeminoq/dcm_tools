import argparse
import subprocess
from typing import Dict, List

import yaml

parser = argparse.ArgumentParser(
    description="Send images to a DICOM node",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument(
    "--node_yml",
    type=str,
    default="data/dcm_nodes.yml",
    help="file containing definitions of available DICOM nodes",
)
parser.add_argument(
    "--node",
    type=str,
    required=True,
    help="an id, an alias or an AET matching to a node in the yaml file",
)
parser.add_argument(
    "--sending_aet", type=str, default="GORILLA", help="the AET of the sending node"
)
parser.add_argument("--files", type=str, nargs="+", help="the files to send")
args = parser.parse_args()

with open(args.node_yml, mode="r") as f:
    nodes = yaml.safe_load(f.read())


def match_node(node: Dict, _str: str):
    try:
        _id = int(_str)
        if _id == node["Id"]:
            return True
    except:
        # string cannot be parsed as an int so it will not match an id anyway
        pass

    _str = _str.lower()
    if _str == node["AET"].lower():
        return True

    if "Alias" in node:
        _aliases = list(map(lambda alias: alias.lower(), node["Alias"]))
        if _str in _aliases:
            return True

    return False


target_node = filter(lambda node: match_node(node, args.node), nodes)
target_node = list(target_node)

if len(target_node) == 0:
    print(f"Could not find node {args.node} in definitions in {args.node_yml}")
    exit(1)
target_node = target_node[0]

print(f"Send to node: {target_node}")

target_aet = target_node["AET"]
target_ip = target_node["IP"]
target_port = target_node["Port"]

for _file in args.files:
    _args = [
        "storescu",
        "-v",
        f"-aet {args.sending_aet}",
        f"-aec {target_aet}",
        str(target_ip),
        str(target_port),
        _file,
    ]
    _args_str = " ".join(_args)
    print(f" - Run {_args_str}")
    process = subprocess.run(_args_str, capture_output=True, check=True, shell=True)
