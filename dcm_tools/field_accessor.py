from typing import List

import pydicom

class Field:
    def __init__(self, field_str: str):
        self.field_str = field_str
        self.index = None

        if "[" in self.field_str:
            split = self.field_str.split("[")
            self.field_str = split[0]
            self.index = int(split[1].split("]")[0])

    def __repr__(self):
        return (
            self.field_str if self.index is None else f"{self.field_str}[{self.index}]"
        )

    def __call__(self, dcm):
        return (
            dcm[self.field_str].value
            if self.index is None
            else dcm[self.field_str][self.index]
        )


class DeepField:

    def __init__(self, fields: List[Field]):
        self.fields = fields

    def __repr__(self):
        return ".".join(map(lambda field: field.__repr__(), self.fields))

    def __call__(self, dcm: pydicom.Dataset):
        value = dcm
        for field in self.fields:
            value = field(value)
        return value


def build_from_str(_str: str):
    if "." not in _str:
        return Field(_str)

    fields = list(map(lambda _str: Field(_str), _str.split(".")))
    return DeepField(fields)


if __name__ == "__main__":

    fd = build_from_str("PatientOrientationCodeSequence[0].PatientOrientationModifierCodeSequence[0].CodeMeaning")
    f_imageId = build_from_str("ImageID")
    fs = [fd, f_imageId]


    dcm = pydicom.dcmread("../mu-map/tmp/bad_oeynhausen/discovery/tmp/p_20230823_144246093/NM.1.2.840.113619.2.281.31108.105270.1692794999.428062300")
    for f in fs:
        print(f, "->", f(dcm))
