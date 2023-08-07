import argparse
import os
from typing import List
import shutil

import pydicom

cmd_name = "sort_files"
cmd_desc = "Sort DICOM files into a directory with the structure: <patient_name>-<patient_id>/<series_instance_uid>.dcm"


def recursive_listdir(_file: str) -> List[str]:
    """
    Recursively list a files in a directory.

    Parameters
    ----------
    _file: str
        the directory to be recursively listed

    Returns
    -------
    List[str]
    """
    if os.path.isfile(_file):
        return [_file]

    files = []
    for f in [os.path.join(_file, _f) for _f in os.listdir(_file)]:
        files.extend(recursive_listdir(f))
    return files


def add_args(parser: argparse.ArgumentParser):
    """
    Add arguments for this command to an argument parser.
    """
    parser.add_argument("dir_in", type=str, help="input directory which is searched for files")
    parser.add_argument("--dir_out", type=str, help="output directory - defaults to the input directory if not given")
    parser.add_argument(
        "-m",
        "--move",
        action="store_true",
        help="move files to their new location instead of copying",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="do not print any output"
    )


def main(args):
    if args.dir_out is None:
        args.dir_out = args.dir_in

    _print = (lambda *args: None) if args.quiet else print
    copy_or_move = shutil.move if args.move else shutil.copyfile
    for file_in in recursive_listdir(args.dir_in):
        dcm = pydicom.dcmread(file_in, stop_before_pixels=True)

        patient_dir = f"{dcm.PatientName.family_name.lower()}_{dcm.PatientName.given_name.lower()}-{dcm.PatientID}"
        patient_dir = os.path.join(args.dir_out, patient_dir)
        os.makedirs(patient_dir, exist_ok=True)

        file_out = dcm.SeriesInstanceUID.replace(".", "_") + ".dcm"
        file_out = os.path.join(patient_dir, file_out)

        if os.path.exists(file_out):
            _print(f"Skip {file_out} because it already exists!")
            continue

        _print(f"{file_in} -> {file_out}")
        copy_or_move(file_in, file_out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=cmd_desc,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(func=main)

    add_args(parser)

    args = parser.parse_args()
    args.func(args)
