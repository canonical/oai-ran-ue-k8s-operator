# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for the `fiveg_rfsim` relation.

This library contains the Requires and Provides classes for handling the `fiveg_rfsim` interface.

The purpose of this library is to relate two charms to pass the RF SIM address and network information (SST and SD).
In the Telco world this will typically be charms implementing
the DU (Distributed Unit) and the UE (User equipment).

## Getting Started
From a charm directory, fetch the library using `charmcraft`:

```shell
charmcraft fetch-lib charms.oai_ran_du_k8s.v0.fiveg_rfsim
```

Add the following libraries to the charm's `requirements.txt` file:
- pydantic
- pytest-interface-tester

### Provider charm
The provider charm is the one providing the information about RF SIM address, Network Slice Type (SST) and Network Differentiator (SD).
Typically, this will be the DU charm.

Example:
```python

from ops import main
from ops.charm import CharmBase, RelationChangedEvent

from charms.oai_ran_du_k8s.v0.fiveg_rfsim import RFSIMProvides


class DummyFivegRFSIMProviderCharm(CharmBase):

    RFSIM_ADDRESS = "192.168.70.130"
    SST = 1
    SD = 1

    def __init__(self, *args):
        super().__init__(*args)
        self.rfsim_provider = RFSIMProvides(self, "fiveg_rfsim")
        self.framework.observe(
            self.on.fiveg_rfsim_relation_changed, self._on_fiveg_rfsim_relation_changed
        )

    def _on_fiveg_rfsim_relation_changed(self, event: RelationChangedEvent):
        if self.unit.is_leader():
            self.rfsim_provider.set_rfsim_information(
                rfsim_address=self.RFSIM_ADDRESS
                sst=self.SST,
                sd=self.SD,
            )


if __name__ == "__main__":
    main(DummyFivegRFSIMProviderCharm)
```

### Requirer charm
The requirer charm is the one requiring the RF simulator information.
Typically, this will be the UE charm.

Example:
```python

from ops import main
from ops.charm import CharmBase, RelationChangedEvent

from charms.oai_ran_du_k8s.v0.fiveg_rfsim import RFSIMRequires

logger = logging.getLogger(__name__)


class DummyFivegRFSIMRequires(CharmBase):

    def __init__(self, *args):
        super().__init__(*args)
        self.rfsim_requirer = RFSIMRequires(self, "fiveg_rfsim")
        self.framework.observe(
            self.on.fiveg_rfsim_relation_changed, self._on_fiveg_rfsim_relation_changed
        )

    def _on_fiveg_rfsim_relation_changed(self, event: RelationChangedEvent):
        provider_rfsim_address = event.rfsim_address
        provider_sst = event.sst
        provider_st = event.sd
        <do something with the rfsim address, SST and SD here>


if __name__ == "__main__":
    main(DummyFivegRFSIMRequires)
```

"""


import logging
from typing import Any, Dict, Optional

from interface_tester.schema_base import DataBagSchema
from ops.charm import CharmBase
from ops.framework import Object
from ops.model import Relation
from pydantic import BaseModel, Field, IPvAnyAddress, ValidationError


# The unique Charmhub library identifier, never change it
LIBID = "e5d421b1edce4e8b8b3632d55869117c"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 3


logger = logging.getLogger(__name__)

"""Schemas definition for the provider and requirer sides of the `fiveg_rfsim` interface.
It exposes two interface_tester.schema_base.DataBagSchema subclasses called:
- ProviderSchema
- RequirerSchema
Examples:
    ProviderSchema:
        unit: <empty>
        app: {
            "rfsim_address": "192.168.70.130",
            "sst": 1,
            "sd": 1,
        }
    RequirerSchema:
        unit: <empty>
        app:  <empty>
"""


class ProviderAppData(BaseModel):
    """Provider app data for fiveg_rfsim."""

    rfsim_address: IPvAnyAddress = Field(
        description="RF simulator service address which is equal to DU pod ip",
        examples=["192.168.70.130"],
    )
    sst: int = Field(
        description="Slice/Service Type",
        examples=[1, 2, 3, 4],
        ge=0,
        le=255,
    )
    sd: Optional[int] = Field(
        description="Slice Differentiator",
        default=None,
        examples=[1],
        ge=0,
        le=16777215,
    )


class ProviderSchema(DataBagSchema):
    """Provider schema for the fiveg_rfsim interface."""

    app_data: ProviderAppData


def provider_data_is_valid(data: Dict[str, Any]) -> bool:
    """Return whether the provider data is valid.

    Args:
        data (dict): Data to be validated.

    Returns:
        bool: True if data is valid, False otherwise.
    """
    try:
        ProviderSchema(app_data=ProviderAppData(**data))
        return True
    except ValidationError as e:
        logger.error("Invalid data: %s", e)
        return False


class FivegRFSIMError(Exception):
    """Custom error class for the `fiveg_rfsim` library."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class RFSIMProvides(Object):
    """Class to be instantiated by the charm providing relation using the `fiveg_rfsim` interface."""

    def __init__(self, charm: CharmBase, relation_name: str):
        """Init."""
        super().__init__(charm, relation_name)
        self.relation_name = relation_name
        self.charm = charm

    def set_rfsim_information(self, rfsim_address: str, sst: int, sd: Optional[int]) -> None:
        """Push the information about the RFSIM interface in the application relation data.

        Args:
            rfsim_address (str): rfsim service address which is equal to DU pod ip.
            sst (int): Slice/Service Type
            sd (Optional[int]): Slice Differentiator
        """
        if not self.charm.unit.is_leader():
            raise FivegRFSIMError("Unit must be leader to set application relation data.")
        relations = self.model.relations[self.relation_name]
        if not relations:
            raise FivegRFSIMError(f"Relation {self.relation_name} not created yet.")
        if not provider_data_is_valid(
            {
                "rfsim_address": rfsim_address,
                "sst": sst,
                "sd": sd,
            }
        ):
            raise FivegRFSIMError("Invalid relation data")
        for relation in relations:
            data = {
                "rfsim_address": rfsim_address,
                "sst": str(sst),
            }
            if sd is not None:
                data["sd"] = str(sd)
            relation.data[self.charm.app].update(data)


class RFSIMRequires(Object):
    """Class to be instantiated by the charm requiring relation using the `fiveg_rfsim` interface."""

    def __init__(self, charm: CharmBase, relation_name: str):
        """Init."""
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name

    @property
    def rfsim_address(self) -> Optional[IPvAnyAddress]:
        """Return address of the RFSIM.

        Returns:
            Optional[IPvAnyAddress]: rfsim address which is equal to DU pod ip.
        """
        if remote_app_relation_data := self.get_provider_rfsim_information():
            return remote_app_relation_data.rfsim_address
        return None

    @property
    def sst(self) -> Optional[int]:
        """Return the Network Slice Service Type (SST).

        Returns:
            Optional[int]: sst (Network Slice Service Type)
        """
        if remote_app_relation_data := self.get_provider_rfsim_information():
            return remote_app_relation_data.sst
        return None

    @property
    def sd(self) -> Optional[int]:
        """Return the Network Slice Differentiator (SD).

        Returns:
           Optional[int] : sd (Network Slice Differentiator)
        """
        if remote_app_relation_data := self.get_provider_rfsim_information():
            return remote_app_relation_data.sd
        return None

    def get_provider_rfsim_information(self, relation: Optional[Relation] = None
    ) -> Optional[ProviderAppData]:
        """Get relation data for the remote application.

        Args:
            relation: Juju relation object (optional).

        Returns:
            ProviderAppData: Relation data for the remote application if data is valid,
            None otherwise.
        """
        relation = relation or self.model.get_relation(self.relation_name)
        if not relation:
            logger.error("No relation: %s", self.relation_name)
            return None
        if not relation.app:
            logger.warning("No remote application in relation: %s", self.relation_name)
            return None
        remote_app_relation_data: Dict[str, Any] = dict(relation.data[relation.app])

        try:
            remote_app_relation_data["sst"] = int(remote_app_relation_data.get("sst", ""))
        except ValueError as err:
            logger.error("Invalid relation data: %s: %s", remote_app_relation_data, str(err))
            return None

        try:
            if sd := remote_app_relation_data.get("sd"):
                remote_app_relation_data["sd"] = int(sd)
        except ValueError as err:
            logger.error("Invalid relation data: %s: %s", remote_app_relation_data, str(err))
            return None

        try:
            provider_app_data = ProviderAppData(**remote_app_relation_data)
        except ValidationError:
            logger.error("Invalid relation data: %s", remote_app_relation_data)
            return None
        return provider_app_data
