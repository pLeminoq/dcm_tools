import argparse

import dcm_tools.diff as diff
import dcm_tools.dump as dump
import dcm_tools.pseudonym.create as pseudonymize
import dcm_tools.send as send
import dcm_tools.sort_files as sort_files

cmds = [diff, dump, pseudonymize, send, sort_files]

parser = argparse.ArgumentParser(description="DICOM tools", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
subparsers = parser.add_subparsers(required=True)

for cmd in cmds:
    _parser = subparsers.add_parser(cmd.cmd_name, description=cmd.cmd_desc, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    cmd.add_args(_parser)
    _parser.set_defaults(func=cmd.main)

args = parser.parse_args()
args.func(args)

