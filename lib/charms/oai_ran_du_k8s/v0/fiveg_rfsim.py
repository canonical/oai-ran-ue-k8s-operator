# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for the `fiveg_rfsim` relation.

This library contains the Requires and Provides classes for handling the `fiveg_rfsim` interface.

The purpose of this library is to relate two charms to pass the RF SIM address.
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
The provider charm is the one providing the information about RF SIM address.
Typically, this will be the DU charm.

Example:
```python

from ops.charm import CharmBase, RelationJoinedEvent
from ops.main import main

from charms.oai_ran_du_k8s.v0.fiveg_rfsim import RFSIMProvides


class DummyFivegRFSIMProviderCharm(CharmBase):

    RFSIM_ADDRESS = "192.168.70.130:4043"

    def __init__(self, *args):
        super().__init__(*args)
        self.rfsim_provider = RFSIMProvides(self, "fiveg_rfsim")
        self.framework.observe(
            self.on.fiveg_rfsim_relation_joined, self._on_fiveg_rfsim_relation_joined
        )

    def _on_fiveg_rfsim_relation_joined(self, event: RelationJoinedEvent):
        if self.unit.is_leader():
            self.rfsim_provider.set_rfsim_information(
                rfsim_address=self.RFSIM_ADDRESS,
            )


if __name__ == "__main__":
    main(DummyFivegRFSIMProviderCharm)
```

### Requirer charm
The requirer charm is the one requiring the RF simulator information.
Typically, this will be the UE charm.

Example:
```python

from ops.charm import CharmBase
from ops.main import main

from charms.oai_ran_du_k8s.v0.fiveg_rfsim import FivegRFSIMInformationAvailableEvent, RFSIMRequires

logger = logging.getLogger(__name__)


class DummyFivegRFSIMRequires(CharmBase):

    def __init__(self, *args):
        super().__init__(*args)
        self.rfsim_requirer = RFSIMRequires(self, "fiveg_rfsim")
        self.framework.observe(
            self.rfsim_requirer.on.fiveg_rfsim_provider_available, self._on_rfsim_information_available
        )

    def _on_rfsim_information_available(self, event: FivegRFSIMInformationAvailableEvent):
        provider_rfsim_address = event.rfsim_address
        <do something with the rfsim address here>


if __name__ == "__main__":
    main(DummyFivegRFSIMRequires)
```

"""


import logging
from typing import Any, Dict, Optional

from interface_tester.schema_base import DataBagSchema
from ops.charm import CharmBase, CharmEvents, RelationChangedEvent
from ops.framework import EventBase, EventSource, Handle, Object
from ops.model import Relation
from pydantic import BaseModel, Field, ValidationError


# The unique Charmhub library identifier, never change it
LIBID = "e5d421b1edce4e8b8b3632d55869117c"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1


logger = logging.getLogger(__name__)


class FivegRFSIMProviderAppData(BaseModel):
    """Provider app data for fiveg_rfsim."""

    rfsim_address: str = Field(
        description="RF simulator service address of DU including DU pod ip and port",
        examples=["192.168.70.130:4043"],
    )


class ProviderSchema(DataBagSchema):
    """Provider schema for the fiveg_rfsim interface."""

    app: FivegRFSIMProviderAppData


def provider_data_is_valid(data: Dict[str, Any]) -> bool:
    """Return whether the provider data is valid.

    Args:
        data (dict): Data to be validated.

    Returns:
        bool: True if data is valid, False otherwise.
    """
    try:
        ProviderSchema(app=data)
        return True
    except ValidationError as e:
        logger.error("Invalid data: %s", e)
        return False


class FivegRFSIMInformationAvailableEvent(EventBase):
    """Charm event emitted when the RFSIM provider info is available.

    The event carries the RFSIM provider's address.
    """

    def __init__(self, handle: Handle, rfsim_address: str):
        """Init."""
        super().__init__(handle)
        self.rfsim_address = rfsim_address

    def snapshot(self) -> dict:
        """Return snapshot."""
        return {
            "rfsim_address": self.rfsim_address,
        }

    def restore(self, snapshot: dict) -> None:
        """Restores snapshot."""
        self.rfsim_address = snapshot["rfsim_address"]


class FivegRFSIMRequirerCharmEvents(CharmEvents):
    """The event that the RFSIM requirer charm can leverage."""

    fiveg_rfsim_provider_available = EventSource(FivegRFSIMInformationAvailableEvent)


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

    def set_rfsim_information(self, rfsim_address: str) -> None:
        """Push the information about the RFSIM interface in the application relation data.

        Args:
            rfsim_address (str): rfsim service address including the pod ip and port number.
        """
        if not self.charm.unit.is_leader():
            raise FivegRFSIMError("Unit must be leader to set application relation data.")
        relations = self.model.relations[self.relation_name]
        if not relations:
            raise FivegRFSIMError(f"Relation {self.relation_name} not created yet.")
        if not provider_data_is_valid({"rfsim_address": rfsim_address}):
            raise FivegRFSIMError("Invalid relation data")
        for relation in relations:
            relation.data[self.charm.app].update(
                {
                    "rfsim_address": rfsim_address,
                }
            )


class RFSIMRequires(Object):
    """Class to be instantiated by the charm requiring relation using the `fiveg_rfsim` interface."""

    on = FivegRFSIMRequirerCharmEvents()

    def __init__(self, charm: CharmBase, relation_name: str):
        """Init."""
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name
        self.framework.observe(charm.on[relation_name].relation_changed, self._on_relation_changed)

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handle relation changed event.

        Args:
            event (RelationChangedEvent): Juju event.
        """
        if remote_app_relation_data := self._get_remote_app_relation_data(event.relation):
            self.on.fiveg_rfsim_provider_available.emit(
                rfsim_address=remote_app_relation_data["rfsim_address"],
            )

    @property
    def rfsim_address(self) -> Optional[str]:
        """Return address of the RFSIM.

        Returns:
            str: rfsim address including pod ip and port number.
        """
        if remote_app_relation_data := self._get_remote_app_relation_data():
            return remote_app_relation_data.get("rfsim_address")
        return None

    def _get_remote_app_relation_data(
        self, relation: Optional[Relation] = None
    ) -> Optional[Dict[str, str]]:
        """Get relation data for the remote application.

        Args:
            relation: Juju relation object (optional).

        Returns:
            Dict: Relation data for the remote application
            or None if the relation data is invalid.
        """
        relation = relation or self.model.get_relation(self.relation_name)
        if not relation:
            logger.error("No relation: %s", self.relation_name)
            return None
        if not relation.app:
            logger.warning("No remote application in relation: %s", self.relation_name)
            return None
        remote_app_relation_data = dict(relation.data[relation.app])
        if not provider_data_is_valid(remote_app_relation_data):
            logger.error("Invalid relation data: %s", remote_app_relation_data)
            return None
        return remote_app_relation_data
