import argparse
import os
import stat
import random
import shutil
import string
from typing import List

from dicomanonymizer.simpledicomanonymizer import anonymize_dataset, keep as action_keep
import pydicom

from dcm_tools.pseudonym.lib import Identifier, IdentifierDict

cmd_name = "pseudonymize"
cmd_desc = "Pseudonmyize a directory of DICOM files"


def list_files_recursive(filename: str) -> List[str]:
    """
    Recursively list all files in a directory.

    Parameters
    ----------
    filename: str
        a filename of a directory

    Returns
    -------
    List[str]
        a list of all files in the directory and its sub-directories
    """
    if os.path.isfile(filename):
        return [filename]

    files = []
    if os.path.isdir(filename):
        sub_files = [os.path.join(filename, f) for f in os.listdir(filename)]
        sub_files.sort()

        for sub_file in sub_files:
            files.extend(list_files_recursive(sub_file))

    return files


class PseudonymGenerator:
    """
    Abstract base class for a pseudonym generator.

    Calling the generator will generate a new pseudonym.
    A prefix for the generated pseudonyms can be specified.
    """

    def __init__(self, prefix: str):
        self.prefix = prefix

    def __call__(self) -> str:
        raise NotImplementedError("Abstract base class")


class RandomPseudonymGenerator(PseudonymGenerator):
    """
    Generator for random pseudonyms.

    Pseudonyms have the format {prefix}{[A-Z0-9]**k}

    Parameters
    ----------
    prefix: str
        a prefix added to the generated pseudonym
    k: int
        the number of random uppercase letters and digits the pseudonym should consist of
    """

    def __init__(self, prefix: str = "ANONYM_", k: int = 12):
        super().__init__(prefix)

        self.k = k

    def __call__(self) -> str:
        _id = "".join(random.choices(string.ascii_uppercase + string.digits, k=self.k))
        return f"{self.prefix}{_id}"


class OrderedPseudonymGenerator(PseudonymGenerator):
    """
    Generator for ordered pseudonyms.

    Pseudonyms have the format {prefix}{idx:0{leading_zeros}d}

    Parameters
    ----------
    prefix: str
        a prefix added to the generated pseudonym
    start_idx: int
        the starting number for pseudonym generation
    leading_zeros: int
        the number of leading zeros added to pseudonym numbers
    """

    def __init__(
        self, prefix: str = "ANONYM_", start_idx: int = 1, leading_zeros: int = 3
    ):
        super().__init__(prefix)

        self.idx = start_idx
        self.leading_zeros = leading_zeros

    def __call__(self) -> str:
        print(f"Call {self.idx}")
        pseudonym = f"{self.prefix}{self.idx:0{self.leading_zeros}d}"
        self.idx += 1
        return pseudonym


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "in_dir", type=str, help="input directory containing the DICOM dataset"
    )
    parser.add_argument(
        "out_dir",
        type=str,
        help="output directory containing pseudonymized and header data as well as a mapping",
    )
    parser.add_argument(
        "--pseudonymized_dir",
        type=str,
        default="pseudonymized",
        help="directory unter <out_dir> mirroring <in_dir> with pseudonymized DICOM files",
    )
    parser.add_argument(
        "--header_dir",
        type=str,
        default="header",
        help="directory unter <out_dir> mirroring <in_dir> with header (fields contain headers with real values) DICOM files",
    )
    parser.add_argument(
        "--identification_csv",
        type=str,
        default="identification.csv",
        help="csv file containing data to re-identify pseudonymized files",
    )
    parser.add_argument(
        "--no_patient_id",
        action="store_true",
        help="do not generate a pseudonym for the patient id - in this case it is no longer visible if pseudonymized files belong to the same patient",
    )
    parser.add_argument(
        "--copy_non_dicom",
        action="store_true",
        help="when mirroring the input directory copy non-DICOM files - else they are left out",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="if the output directory already exists, it is replaced",
    )
    parser.add_argument(
        "--pseudo_prefix",
        type=str,
        default="ANONYM_",
        help="prefix for the generated pseudonyms",
    )
    parser.add_argument(
        "--numbered_pseudonym",
        action="store_true",
        help="do not generate a random pseudonym but continuous numbers",
    )
    parser.add_argument(
        "--pseudo_len",
        type=int,
        default=12,
        help="length of the generated pseudonym (if not <numbered_pseudonym>)",
    )
    parser.add_argument(
        "--leading_zeros",
        type=int,
        default=3,
        help="number of leading zeros (if <numbered_pseudonym>)",
    )
    parser.add_argument(
        "--keep_private_tags",
        action="store_true",
        help="keep all private tags",
    )
    parser.add_argument(
        "--keep",
        type=str,
        nargs="*",
        help="define tags that should not be removed/modified",
    )


def main(args):
    args.pseudonymized_dir = os.path.join(args.out_dir, args.pseudonymized_dir)
    args.header_dir = os.path.join(args.out_dir, args.header_dir)
    args.identification_csv = os.path.join(args.out_dir, args.identification_csv)

    # make sure in_dir is a directory
    assert os.path.isdir(args.in_dir), f"{args.in_dir} is not a directory"

    # make sure out dir does not exist, is empty or the force flag is set
    if os.path.exists(args.out_dir):
        assert os.path.isdir(args.out_dir), f"{args.out_dir} is not a directory"

        if not args.force:
            assert (
                len(os.listdir(args.out_dir)) == 0
            ), f"{args.out_dir} is not empty - please chose an empty directory or use the -f/--force option"
    shutil.rmtree(args.out_dir, ignore_errors=True)
    os.makedirs(args.out_dir)

    pseudo_by_pid = {}  # store pseudonyms by patient id
    id_dict = IdentifierDict()

    # store pseudonym generation function with given parameters
    pseudonym_generator = (
        OrderedPseudonymGenerator(
            prefix=args.pseudo_prefix, leading_zeros=args.leading_zeros
        )
        if args.numbered_pseudonym
        else RandomPseudonymGenerator(prefix=args.pseudo_prefix, k=args.pseudo_len)
    )

    print(f"Args.keep: {args.keep}")
    print(args)
    _keep = [] if args.keep is None else args.keep
    tags_to_keep = []
    for tag in _keep:
        assert tag.startswith(
            "0x"
        ), f"Tag {tag} is not in hex notation. Please use a hex Notation (e.g. 0x00010002) to define tags"
        tag = tag[2:]
        assert (
            len(tag) == 8
        ), f"Tag should have a length of 8 in hex notation, but was {tag} with len {len(tag)}"
        tag = (int(tag[:4], base=16), int(tag[4:], base=16))
        tags_to_keep.append(tag)

    extra_anonymization_rules = dict([(tag, action_keep) for tag in tags_to_keep])
    print(f"Tags to keep:")
    for k, v in extra_anonymization_rules.items():
        print(f"{k}: {v}")

    # process input directory
    for f in list_files_recursive(args.in_dir):
        # handle non DICOM files
        if not pydicom.misc.is_dicom(f):
            if args.copy_non_dicom:
                f_out = f.replace(args.in_dir, args.pseudonymized_dir, 1)
                print(f"{f} -> {f_out}")
                os.makedirs(os.path.dirname(f_out), exist_ok=True)
                shutil.copyfile(f, f_out)
            continue

        # handle DICOM files
        dcm = pydicom.dcmread(f)

        # generate pseudonym for series instance uid
        pseudo_siuid = pydicom.uid.generate_uid()

        # generate or retrieve pseudonym for patient id
        pid = dcm.PatientID
        if pid not in pseudo_by_pid:
            pseudo_by_pid[pid] = pseudonym_generator()
        pseudo_pid = pseudo_by_pid[pid]

        # create pseudonymized DICOM file
        anonymize_dataset(
            dcm,
            extra_anonymization_rules=extra_anonymization_rules,
            delete_private_tags=not args.keep_private_tags,
        )
        dcm.SeriesInstanceUID = pseudo_siuid
        dcm.PatientID = "" if args.no_patient_id else pseudo_pid
        # store
        f_out = f.replace(args.in_dir, args.pseudonymized_dir)
        print(f"{f} -> {f_out}")
        os.makedirs(os.path.dirname(f_out), exist_ok=True)
        pydicom.dcmwrite(f_out, dcm)

        # create header data for re-identification
        dcm_header = pydicom.dcmread(f, stop_before_pixels=True)
        f_out = f.replace(args.in_dir, args.header_dir)
        print(f"{f} -> {f_out}")
        os.makedirs(os.path.dirname(f_out), exist_ok=True)
        pydicom.dcmwrite(f_out, dcm_header)
        os.chmod(f_out, stat.S_IRUSR)  # make non-writable

        id_dict.add(
            Identifier(
                siuid=dcm_header.SeriesInstanceUID,
                pseudo_siuid=pseudo_siuid,
                filename=f_out,
                pid=dcm_header.PatientID,
                pseudo_pid=pseudo_pid,
            )
        )
    id_dict.to_csv(args.identification_csv)
    os.chmod(args.identification_csv, stat.S_IRUSR)  # make non-writable


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=cmd_desc,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(func=main)

    add_args(parser)

    args = parser.parse_args()
    args.func(args)
