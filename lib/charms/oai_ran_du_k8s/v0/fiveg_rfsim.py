# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for the `fiveg_rfsim` relation.

This library contains the Requires and Provides classes for handling the `fiveg_rfsim` interface.

The purpose of this library is to relate two charms to pass the network configuration data required to start the RF simulation.
In particular the RF SIM address, Network Slice Type (SST), Slice Differentiator (SD), RF band, downlink frequency, carrier bandwidth, numerology and the number of the first usable subcarrier will be passed through the interface.
In the Telco world this will typically be charms implementing the DU (Distributed Unit) and the UE (User equipment).

## Getting Started
From a charm directory, fetch the library using `charmcraft`:

```shell
charmcraft fetch-lib charms.oai_ran_du_k8s.v0.fiveg_rfsim
```

Add the following libraries to the charm's `requirements.txt` file:
- pydantic
- pytest-interface-tester

### Provider charm
The provider charm is the one providing the information about RF SIM address, SST, SD, RF band, downlink frequency, carrier bandwidth, numerology and the number of the first usable subcarrier.
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
    BAND = 77
    DL_FREQ = 4059090000  # In Hz
    CARRIER_BANDWIDTH = 106  # In PRBs
    NUMEROLOGY = 1
    START_SUBCARRIER = 541

    def __init__(self, *args):
        super().__init__(*args)
        self.rfsim_provider = RFSIMProvides(self, "fiveg_rfsim")
        self.framework.observe(
            self.on.fiveg_rfsim_relation_changed, self._on_fiveg_rfsim_relation_changed
        )

    def _on_fiveg_rfsim_relation_changed(self, event: RelationChangedEvent):
        if self.unit.is_leader():
            self.rfsim_provider.set_rfsim_information(
                version=0,
                rfsim_address=self.RFSIM_ADDRESS,
                sst=self.SST,
                sd=self.SD,
                band=self.BAND,
                dl_freq=self.DL_FREQ,
                carrier_bandwidth=self.CARRIER_BANDWIDTH,
                numerology=self.NUMEROLOGY,
                start_subcarrier=self.START_SUBCARRIER
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
        provider_sd = event.sd
        provider_band = event.band
        provider_dl_freq = event.dl_freq
        provider_carrier_bandwidth = event.carrier_bandwidth
        provider_numerology = event.numerology
        provider_start_subcarrier = event.start_subcarrier
        <do something with the received data>


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
LIBPATCH = 1


logger = logging.getLogger(__name__)

"""Schemas definition for the provider and requirer sides of the `fiveg_rfsim` interface.
It exposes two interface_tester.schema_base.DataBagSchema subclasses called:
- ProviderSchema
- RequirerSchema
Examples:
    ProviderSchema:
        unit: <empty>
        app: {
            "version": 0,
            "rfsim_address": "192.168.70.130",
            "sst": 1,
            "sd": 1,
            "band": 77,
            "dl_freq": 4059090000,
            "carrier_bandwidth": 106,
            "numerology": 1,
            "start_subcarrier": 541,
        }
    RequirerSchema:
        unit: <empty>
        app: {
            "version": 0,
        }
"""


class ProviderAppData(BaseModel):
    """Provider app data for fiveg_rfsim."""

    version: int = Field(
        description="Interface version",
        examples=[0, 1, 2, 3],
        ge=0,
    )
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
    band: int = Field(
        description="Frequency band",
        default=None,
        examples=[34, 77, 102],
        gt=0,
    )
    dl_freq: int = Field(
        description="Downlink frequency in Hz",
        default=None,
        examples=[4059090000],
        ge=410000000,
    )
    carrier_bandwidth: int = Field(
        description="Carrier bandwidth (number of downlink PRBs)",
        default=None,
        examples=[106],
        ge=11,
        le=273,
    )
    numerology: int = Field(
        description="Numerology",
        default=None,
        examples=[0, 1, 2, 3],
        ge=0,
        le=6,
    )
    start_subcarrier: int = Field(
        description="First usable subcarrier",
        default=None,
        examples=[530, 541],
        ge=0,
    )


class ProviderSchema(DataBagSchema):
    """Provider schema for the fiveg_rfsim interface."""

    app_data: ProviderAppData


class RequirerAppData(BaseModel):
    """Requirer app data for fiveg_rfsim."""

    version: int = Field(
        description="Interface version",
        examples=[0, 1, 2, 3],
        ge=0,
    )


class RequirerSchema(DataBagSchema):
    """Requirer schema for the fiveg_rfsim interface."""

    app_data: RequirerAppData


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

    def set_rfsim_information(
        self,
        rfsim_address: str,
        sst: int,
        sd: Optional[int],
        band: int,
        dl_freq: int,
        carrier_bandwidth: int,
        numerology: int,
        start_subcarrier: int,
    ) -> None:
        """Push the information about the RFSIM interface in the application relation data.

        Args:
            rfsim_address (str): rfsim service address which is equal to DU pod ip.
            sst (int): Slice/Service Type
            sd (Optional[int]): Slice Differentiator
            band (int): Valid 5G band
            dl_freq (int): Downlink frequency in Hz
            carrier_bandwidth (int): Carrier bandwidth (number of downlink PRBs)
            numerology (int): Numerology
            start_subcarrier (int): First usable subcarrier
        """
        if not self.charm.unit.is_leader():
            raise FivegRFSIMError("Unit must be leader to set application relation data.")
        relations = self.model.relations[self.relation_name]
        if not relations:
            raise FivegRFSIMError(f"Relation {self.relation_name} not created yet.")
        if not provider_data_is_valid(
            {
                "version": str(LIBAPI),
                "rfsim_address": rfsim_address,
                "sst": sst,
                "sd": sd,
                "band": band,
                "dl_freq": dl_freq,
                "carrier_bandwidth": carrier_bandwidth,
                "numerology": numerology,
                "start_subcarrier": start_subcarrier,
            }
        ):
            raise FivegRFSIMError("Invalid relation data")
        for relation in relations:
            data = {
                "version": str(LIBAPI),
                "rfsim_address": rfsim_address,
                "sst": str(sst),
                "band": str(band),
                "dl_freq": str(dl_freq),
                "carrier_bandwidth": str(carrier_bandwidth),
                "numerology": str(numerology),
                "start_subcarrier": str(start_subcarrier),
            }
            if sd is not None:
                data["sd"] = str(sd)
            relation.data[self.charm.app].update(data)

    @property
    def interface_version(self):
        return LIBAPI


class RFSIMRequires(Object):
    """Class to be instantiated by the charm requiring relation using the `fiveg_rfsim` interface."""

    def __init__(self, charm: CharmBase, relation_name: str):
        """Init."""
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name

    @property
    def provider_interface_version(self) -> Optional[int]:
        """Return interface version used by the provider.

        Returns:
            Optional[int]: The `fiveg_rfsim` interface version used by the provider.
        """
        return self._get_provider_interface_version()

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

    @property
    def band(self) -> Optional[int]:
        """Return the RF Band number.

        Returns:
           Optional[int] : band (RF Band number)
        """
        if remote_app_relation_data := self.get_provider_rfsim_information():
            return remote_app_relation_data.band
        return None

    @property
    def dl_freq(self) -> Optional[int]:
        """Return the Downlink frequency.

        Returns:
           Optional[int] : dl_freq (Downlink frequency)
        """
        if remote_app_relation_data := self.get_provider_rfsim_information():
            return remote_app_relation_data.dl_freq
        return None

    @property
    def carrier_bandwidth(self) -> Optional[int]:
        """Return the carrier bandwidth (number of downlink PRBs).

        Returns:
           Optional[int] : carrier_bandwidth (carrier bandwidth)
        """
        if remote_app_relation_data := self.get_provider_rfsim_information():
            return remote_app_relation_data.carrier_bandwidth
        return None

    @property
    def numerology(self) -> Optional[int]:
        """Return numerology.

        Returns:
           Optional[int] : numerology
        """
        if remote_app_relation_data := self.get_provider_rfsim_information():
            return remote_app_relation_data.numerology
        return None

    @property
    def start_subcarrier(self) -> Optional[int]:
        """Return number of the first usable subcarrier.

        Returns:
           Optional[int] : start_subcarrier
        """
        if remote_app_relation_data := self.get_provider_rfsim_information():
            return remote_app_relation_data.start_subcarrier
        return None

    def _get_provider_interface_version(self) -> Optional[int]:
        """Get provider interface version.

        Returns:
            Optional[int]: The `fiveg_rfsim` interface version used by the provider.
        """
        relation = self.model.get_relation(self.relation_name)
        if not relation:
            logger.error("No relation: %s", self.relation_name)
            return None
        if not relation.app:
            logger.warning("No remote application in relation: %s", self.relation_name)
            return None
        try:
            return int(dict(relation.data[relation.app]).get("version", ""))
        except ValueError:
            logger.error("Invalid or missing `fiveg_rfsim` provider interface version.")
            return None

    def get_provider_rfsim_information(
        self, relation: Optional[Relation] = None
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
            remote_app_relation_data["band"] = int(remote_app_relation_data.get("band", ""))
            remote_app_relation_data["dl_freq"] = int(remote_app_relation_data.get("dl_freq", ""))
            remote_app_relation_data["carrier_bandwidth"] = int(
                remote_app_relation_data.get("carrier_bandwidth", "")
            )
            remote_app_relation_data["numerology"] = int(
                remote_app_relation_data.get("numerology", "")
            )
            remote_app_relation_data["start_subcarrier"] = int(
                remote_app_relation_data.get("start_subcarrier", "")
            )
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
        except ValidationError as err:
            logger.error("Invalid relation data: %s: %s", remote_app_relation_data, str(err))
            return None
        return provider_app_data
