#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Config of the Charm."""

import dataclasses
import logging

import ops
from pydantic import (  # pylint: disable=no-name-in-module,import-error
    BaseModel,
    Field,
    StrictStr,
    ValidationError,
)

logger = logging.getLogger(__name__)


class CharmConfigInvalidError(Exception):
    """Exception raised when a charm configuration is found to be invalid."""

    def __init__(self, msg: str):
        """Initialize a new instance of the CharmConfigInvalidError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


def to_kebab(name: str) -> str:
    """Convert a snake_case string to kebab-case."""
    return name.replace("_", "-")


class UEConfig(BaseModel):  # pylint: disable=too-few-public-methods
    """Represent the OAI RAN UE operator builtin configuration values."""

    class Config:
        """Represent config for Pydantic model."""

        alias_generator = to_kebab

    imsi: StrictStr = Field(default="208930100007487", max_length=15, min_length=14)
    key: StrictStr = Field(
        default="5122250214c33e723a5dd523fc145fc0",
        max_length=32,
        min_length=32,
    )
    opc: StrictStr = Field(
        default="981d464c7c52eb6e5036234984ad0bcf",
        max_length=32,
        min_length=32,
    )
    dnn: StrictStr = Field(default="internet", min_length=1)
    simulation_mode: bool = False
    use_three_quarter_sampling: bool = False
    use_mimo: bool = False


@dataclasses.dataclass
class CharmConfig:
    """Represents the state of the OAI RAN DU operator charm.

    Attributes:
        imsi: IMSI identifying this UE.
        key: Secret Key for USIM
        opc: Secret Key for operator
        dnn: Data Network Name
        simulation_mode: Run UE in simulation mode
        use_three_quarter_sampling: Enable three-quarter sampling rate
        use_mimo: Enable support for 2x2 MIMO
    """

    imsi: StrictStr
    key: StrictStr
    opc: StrictStr
    dnn: StrictStr
    simulation_mode: bool
    use_three_quarter_sampling: bool
    use_mimo: bool

    def __init__(self, *, ue_config: UEConfig):
        """Initialize a new instance of the CharmConfig class.

        Args:
            ue_config: OAI RAN UE operator configuration.
        """
        self.imsi = ue_config.imsi
        self.key = ue_config.key
        self.opc = ue_config.opc
        self.dnn = ue_config.dnn
        self.simulation_mode = ue_config.simulation_mode
        self.use_three_quarter_sampling = ue_config.use_three_quarter_sampling
        self.use_mimo = ue_config.use_mimo

    @classmethod
    def from_charm(
        cls,
        charm: ops.CharmBase,
    ) -> "CharmConfig":
        """Initialize a new instance of the CharmState class from the associated charm."""
        try:
            # ignoring because mypy fails with:
            # "has incompatible type "**dict[str, str]"; expected ...""
            return cls(ue_config=UEConfig(**dict(charm.config.items())))  # type: ignore
        except ValidationError as exc:
            error_fields: list = []
            for error in exc.errors():
                if param := error["loc"]:
                    error_fields.extend(param)
                else:
                    value_error_msg: ValueError = error["ctx"]["error"]  # type: ignore
                    error_fields.extend(str(value_error_msg).split())
            error_fields.sort()
            error_field_str = ", ".join(f"'{f}'" for f in error_fields)
            raise CharmConfigInvalidError(
                f"The following configurations are not valid: [{error_field_str}]"
            ) from exc
