import argparse

import dcm_tools.dump as dump
import dcm_tools.pseudonym.create as pseudonymize
import dcm_tools.send as send

cmds = [dump, pseudonymize, send]

parser = argparse.ArgumentParser(description="DICOM tools", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
subparsers = parser.add_subparsers(required=True)

for cmd in cmds:
    _parser = subparsers.add_parser(cmd.cmd_name, description=cmd.cmd_desc)
    cmd.add_args(_parser)
    _parser.set_defaults(func=cmd.main)

args = parser.parse_args()
args.func(args)

