from abc import ABC
from typing import Any


class Base_Reporter(ABC):
    def send(self, data_dict) -> Any:
        ...
