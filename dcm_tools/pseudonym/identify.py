import argparse
import os

import pydicom

from dcm_tools.pseudonym.lib import IdentifierDict

parser = argparse.ArgumentParser()
parser.add_argument("file")
parser.add_argument("pseudonymization_dir")
args = parser.parse_args()

id_csv = os.path.join(args.pseudonymization_dir, "identification.csv")
header_dir = os.path.join(args.pseudonymization_dir, "header")
id_dict = IdentifierDict.from_csv(id_csv)

dcm = pydicom.dcmread(args.file, stop_before_pixels=True)
identifier = id_dict[dcm.SeriesInstanceUID]

dcm_header = pydicom.dcmread(os.path.join(args.pseudonymization_dir, "..", identifier.filename), stop_before_pixels=True)
print(dcm_header.PatientName)
