import argparse

import pydicom

cmd_name = "dump"
cmd_desc = "Dump the header of a DICOM image"

def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("file", type=str, help="the DICOM file whose header is dumped")

def main(args):
    print(pydicom.dcmread(args.file))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=cmd_desc,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(func=main)

    add_args(parser)

    args = parser.parse_args()
    args.func(args)

