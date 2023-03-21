import csv
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import pandas as pd


@dataclass(frozen=True)
class Identifier:
    """
    Mapping of data needed to re-identify a pseudonymized file.
    """

    siuid: str  # series instance uid
    pseudo_siuid: str  # pseudonym for the series instance uid
    filename: str  # where to find the according header file

    pid: Optional[str] = None  # patient id
    pseudo_pid: Optional[str] = None  # pseudonym for the patient id


class IdentifierDict:
    """
    The identifier dict allows to reference identifiers by different ids or pseudonyms.

    It is important for re-identification of pseudonymized data and it can also be
    used to store re-identification information in a csv file.
    """

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
        """
        Add an identifier to the identifier dict.

        Parameters
        ----------
        identifier: Identifier
        """
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
        """
        Get an identifier by id or pseudonym.

        If the id or pseudonym is a patient id or its according pseudonym, a
        list is returned because there may be multiple files for the same patient.

        Parameters
        ----------
        id_or_pseudonym: str

        Returns
        -------
        Identifier or list of Identifier
        """
        for _dict in self.dicts:
            if id_or_pseudonym in _dict:
                return _dict[id_or_pseudonym]
        raise ValueError(f"Cannot find identifier for {id_or_pseudonym}")

    def to_csv(self, filename: str, sort_by: List[str] = ["pid", "siuid"]):
        """
        Write an identification dict to a csv file.

        Parameters
        ----------
        filename: str
            the name of the csv file
        sort_by: list of str
            optional list to sort values before writing
        """
        data = dict((param, []) for param in Identifier.__annotations__.keys())
        for identifier in self.by_siuid.values():
            for key, _list in data.items():
                _list.append(getattr(identifier, key))

        dataframe = pd.DataFrame(data)
        dataframe.sort_values(by=sort_by, inplace=True)
        dataframe.to_csv(filename, index=False)

    @classmethod
    def from_csv(cls, filename: str):
        """
        Parse an identification dict from a csv file.

        Parameters
        ----------
        filename: str
            the csv file
        """
        id_dict = cls()
        with open(filename, mode="r") as f:
            reader = csv.DictReader(f)

            for row in reader:
                identifier = Identifier(**row)
                id_dict.add(identifier)
        return id_dict

