import argparse
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional, Tuple

import pydicom
from termcolor import colored

cmd_name = "diff"
cmd_desc = "Show the difference of two DICOM headers"

class DiffType(Enum):
    DIFFERENT = 1
    MISSING_L = 2
    MISSING_R = 3


color_by_diff = {
    DiffType.DIFFERENT: "yellow",
    DiffType.MISSING_L: "magenta",
    DiffType.MISSING_R: "cyan",
}

symbol_by_diff = {
    DiffType.DIFFERENT: "≠",
    DiffType.MISSING_L: "<",
    DiffType.MISSING_R: ">",
}


def format_str_len(_str: str, _len: int):
    _str = _str if len(_str) < _len else _str[:(_len - 3)] + "..."
    return f"{_str:>{_len}}"
    

@dataclass
class Diff:
    diff_type: DiffType
    tag: Tuple[int, int]
    description: str
    value_l: Any
    value_r: Any
    prefix: Optional[str] = None

    def __str__(self, max_len_tag: int = 50, max_len_val: int = 70):
        _prefix = symbol_by_diff[self.diff_type]
        _max_len_desc = max_len_tag - 15
        if self.prefix:
            _prefix += " " + self.prefix
            _max_len_desc -= 2
        _str = f"{_prefix} {format_str_len(self.description, _len=_max_len_desc)} - {self.tag}"

        str_l = str(self.value_l) if self.value_l is not None else "NULL"
        str_r = str(self.value_r) if self.value_r is not None else "NULL"
        _str = f"{_str} │ {format_str_len(str_l, max_len_val)} │ {format_str_len(str_r, max_len_val)}"
        return colored(_str, color_by_diff[self.diff_type])

def diff(dcm_l: pydicom.dataset.Dataset, dcm_r: pydicom.dataset.Dataset) -> List[Diff]:
    diffs = []

    tags_l = list(dcm_l.keys())
    tags_r = list(dcm_r.keys())

    tags = set(tags_l + tags_r)
    for tag in sorted(tags):
        if tag not in tags_l:
            elem = dcm_r[tag]
            if type(elem.value) == pydicom.sequence.Sequence:
                diffs.append(Diff(diff_type=DiffType.MISSING_L, tag=tag, description=f"[{len(elem.value)}] " + elem.description(), value_l=None, value_r="-----"))
            else:
                diffs.append(Diff(diff_type=DiffType.MISSING_L, tag=tag, description=elem.description(), value_l=None, value_r=elem.value))
            continue

        if tag not in tags_r:
            elem = dcm_l[tag]
            if type(elem.value) == pydicom.sequence.Sequence:
                diffs.append(Diff(diff_type=DiffType.MISSING_R, tag=tag, description=f"[{len(elem.value)}] " + elem.description(), value_l="-----", value_r=None))
            else:
                diffs.append(Diff(diff_type=DiffType.MISSING_R, tag=tag, description=elem.description(), value_l=elem.value, value_r=None))
            continue
        

        elem_l = dcm_l[tag]
        elem_r = dcm_r[tag]

        if type(elem_l.value) == pydicom.sequence.Sequence:
            for i in range(max(len(elem_l.value), len(elem_r.value))):
                if i > len(elem_l.value) - 1:
                    diffs.append(Diff(diff_type=DiffType.MISSING_L, tag=tag, description=elem_l.description() + f" [{i}]", value_l=None, value_r="-----"))
                elif i > len(elem_r.value) - 1:
                    diffs.append(Diff(diff_type=DiffType.MISSING_R, tag=tag, description=elem_l.description() + f" [{i}]", value_l="-----", value_r=None))
                else:
                    _diffs = diff(elem_l.value[i], elem_r.value[i])
                    if len(_diffs) == 0:
                        continue

                    diffs.append(Diff(diff_type=DiffType.DIFFERENT, tag=tag, description=f"[{i}] " + elem_l.description(), value_l="-----", value_r="-----", prefix="┌"))
                    for i, _diff in enumerate(_diffs):
                        _diff.prefix = "└" if i == len(_diffs) - 1 else "├"
                    diffs.extend(_diffs)
            continue

        if elem_l.value == elem_r.value:
            continue

        diffs.append(Diff(diff_type=DiffType.DIFFERENT, tag=tag, description=elem_l.description(), value_l=elem_l.value, value_r=elem_r.value))
    return diffs

def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("file_left", type=str, help="the left file for the diff")
    parser.add_argument("file_right", type=str, help="the right file for the diff")
    parser.add_argument("--len_col_tag", type=int, default=50, help="maximum length of printed tags")
    parser.add_argument("--len_col_val", type=int, default=70, help="maximum length of printed values")

def main(args):
    dcm_l = pydicom.dcmread(args.file_left)
    dcm_r = pydicom.dcmread(args.file_right)

    diffs = diff(dcm_l, dcm_r)

    # print header
    _str = f"  {'Tag':>{args.len_col_tag}} │ {'Left':>{args.len_col_val}} │ {'Right':>{args.len_col_val}}"
    print(_str)
    _str = "──" + ("─" * args.len_col_tag) + "─┼─" + ("─" * args.len_col_val) + "─┼─" + ("─" * args.len_col_val)
    print(_str)

    # print(diffs)
    for _diff in diffs:
        print(str(_diff))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=cmd_desc,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(func=main)

    add_args(parser)

    args = parser.parse_args()
    args.func(args)
