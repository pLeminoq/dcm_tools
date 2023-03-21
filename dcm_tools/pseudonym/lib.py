import csv
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import pandas as pd


@dataclass(frozen=True)
class Identifier:
    """
    Mapping to re-identify a pseudonymized file.
    """

    siuid: str  # series instance uid
    pseudo_siuid: str  # pseudonym for the series instance uid
    filename: str  # where to find the according header file

    pid: Optional[str] = None  # patient id
    pseudo_pid: Optional[str] = None  # pseudonym for the patient id


class IdentifierDict:
    def __init__(self):
        self.by_siuid: Dict[str, Identifier] = {}
        self.by_pseudo_siuid: Dict[str, Identifier] = {}
        self.by_pid: Dict[str, List[Identifier]] = {}
        self.by_pseudo_pid: Dict[str, List[Identifier]] = {}
        self.dicts = [
            self.by_siuid,
            self.by_pseudo_siuid,
            self.by_pid,
            self.by_pseudo_pid,
        ]

    def add(self, identifier: Identifier):
        self.by_siuid[identifier.siuid] = identifier
        self.by_pseudo_siuid[identifier.pseudo_siuid] = identifier

        if identifier.pid is None or identifier.pid == "":
            return

        self.by_pid[identifier.pid] = [
            *self.by_pid.get(identifier.pid, []),
            identifier,
        ]
        self.by_pseudo_pid[identifier.pseudo_pid] = [
            *self.by_pseudo_pid.get(identifier.pseudo_pid, []),
            identifier,
        ]

    def __getitem__(self, id_or_pseudonym: str) -> Union[Identifier, List[Identifier]]:
        for _dict in self.dicts:
            if id_or_pseudonym in _dict:
                return _dict[id_or_pseudonym]
        raise ValueError(f"Cannot find identifier for {id_or_pseudonym}")

    def to_csv(self, filename: str, sort_by: List[str] = ["pid", "siuid"]):
        data = dict((param, []) for param in Identifier.__annotations__.keys())
        for identifier in self.by_siuid.values():
            for key, _list in data.items():
                _list.append(getattr(identifier, key))

        dataframe = pd.DataFrame(data)
        dataframe.sort_values(by=sort_by, inplace=True)
        dataframe.to_csv(filename, index=False)

    @classmethod
    def from_csv(cls, filename):
        id_dict = cls()
        with open(filename, mode="r") as f:
            reader = csv.DictReader(f)

            for row in reader:
                identifier = Identifier(**row)
                id_dict.add(identifier)
        return id_dict

if __name__ == "__main__":
    id1 = Identifier(siuid="1", pseudo_siuid="p1", filename="a.dcm", pid="bat", pseudo_pid="bat1")
    id2 = Identifier(siuid="2", pseudo_siuid="p2", filename="b.dcm", pid="pat", pseudo_pid="pat2")
    id3 = Identifier(siuid="3", pseudo_siuid="p3", filename="c.dcm", pid="pat", pseudo_pid="pat2")

    id_dict = IdentifierDict()
    id_dict.add(id1)
    id_dict.add(id2)
    id_dict.add(id3)
    id_dict.to_csv("test.csv")

    id_dict = IdentifierDict.from_csv("test.csv")
    print(id_dict["pat"])
    print(id_dict["1"])
