import argparse
import os
from typing import List
import shutil

import pydicom

cmd_name = "sort_files"
cmd_desc = "Sort DICOM files into a directory with the structure: <patient_name>-<patient_id>/<series_instance_uid>.dcm"


def dry_methods():
    shutil.move = lambda *args: print(f"            Move {args[0]} -> {args[1]}")
    shutil.copyfile = lambda *args: print(f"            Copy {args[0]} -> {args[1]}")
    os.remove = lambda *args: print(f"          Remove {args[0]}")
    os.rmdir = lambda *args: print(f"Remove directory {args[0]}")
    os.makedirs = lambda *args, **kwargs: print(f"  Make directory {args[0]}")


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


def delete_empty_subdirectories(_dir: str):
    if not os.path.isdir(_dir):
        return

    subdirs = [os.path.join(_dir, d) for d in os.listdir(_dir)]
    subdirs = filter(os.path.isdir, subdirs)
    subdirs = filter(lambda d: len(os.listdir(d)) == 0, subdirs)
    list(map(lambda d: os.rmdir(d), subdirs))


def sort_files(dir_in: str, dir_out: str, move: bool, quiet: bool, dry: bool):
    assert (
        dir_in != dir_out
    ), f"Input directory {args.dir_in} and output directory {args.dir_out} have to differ!"

    _print = (lambda *args: None) if quiet or dry else print
    copy_or_move = shutil.move if move else shutil.copyfile

    directories = set()
    for file_in in recursive_listdir(dir_in):
        directories.add(os.path.dirname(file_in))

        dcm = pydicom.dcmread(file_in, stop_before_pixels=True)

        patient_dir = f"{dcm.PatientName.family_name.lower()}_{dcm.PatientName.given_name.lower()}-{dcm.PatientID}"
        patient_dir = os.path.join(dir_out, patient_dir)
        if not os.path.exists(patient_dir):
            os.makedirs(patient_dir, exist_ok=True)

        file_out = dcm.SeriesInstanceUID.replace(".", "_") + ".dcm"
        file_out = os.path.join(patient_dir, file_out)

        if os.path.exists(file_out):
            if not args.quiet:
                print(f"            Skip {file_out} because it already exists!")

            if move:
                os.remove(file_in)
            continue

        _print(f"{file_in} -> {file_out}")
        copy_or_move(file_in, file_out)


def add_args(parser: argparse.ArgumentParser):
    """
    Add arguments for this command to an argument parser.
    """
    parser.add_argument(
        "dir_in", type=str, help="input directory which is searched for files"
    )
    parser.add_argument(
        "dir_out",
        type=str,
        help="output directory",
    )
    parser.add_argument(
        "-m",
        "--move",
        action="store_true",
        help="move files to their new location instead of copying",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="do not print any output"
    )
    parser.add_argument("-d", "--dry", action="store_true", help="perform a dry run")
    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="watch for changes to the input directory and re-run",
    )


def main(args):
    if args.dry:
        dry_methods()

    sort_files(
        args.dir_in, args.dir_out, move=args.move, quiet=args.quiet, dry=args.dry
    )
    if args.move and not args.dry:
        delete_empty_subdirectories(args.dir_in)

    if args.watch:
        import time
        from watchdog.observers import Observer
        from watchdog.events import DirCreatedEvent, FileSystemEventHandler

        class EventHandler(FileSystemEventHandler):
            def __init__(self):
                super().__init__()

            def on_created(self, ev):
                if type(ev) is DirCreatedEvent:
                    return

                sort_files(
                    ev.src_path,
                    args.dir_out,
                    move=args.move,
                    quiet=args.quiet,
                    dry=args.dry,
                )

        handler = EventHandler()
        observer = Observer()
        observer.schedule(handler, args.dir_in, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(10)
                if args.move:
                    delete_empty_subdirectories(args.dir_in)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=cmd_desc,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(func=main)

    add_args(parser)

    args = parser.parse_args()
    args.func(args)
