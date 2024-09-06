#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed operator for the OAI RAN User Equipment (UE) for K8s."""

import logging
from ipaddress import IPv4Address
from subprocess import check_output
from typing import Optional

from charms.loki_k8s.v1.loki_push_api import LogForwarder
from jinja2 import Environment, FileSystemLoader
from ops import (
    ActiveStatus,
    BlockedStatus,
    CollectStatusEvent,
    Framework,
    WaitingStatus,
)
from ops.charm import CharmBase
from ops.main import main
from ops.pebble import Layer

from charm_config import CharmConfig, CharmConfigInvalidError

logger = logging.getLogger(__name__)

BASE_CONFIG_PATH = "/tmp/conf"
CONFIG_FILE_NAME = "ue.conf"
LOGGING_RELATION_NAME = "logging"
WORKLOAD_VERSION_FILE_NAME = "/etc/workload-version"


class OaiRanUeK8SOperatorCharm(CharmBase):
    """Main class to describe Juju event handling for the OAI RAN UE operator for K8s."""

    def __init__(self, framework: Framework):
        super().__init__(framework)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_unit_status)
        if not self.unit.is_leader():
            return
        self._container_name = self._service_name = "ue"
        self._container = self.unit.get_container(self._container_name)
        self._logging = LogForwarder(charm=self, relation_name=LOGGING_RELATION_NAME)

        try:
            self._charm_config: CharmConfig = CharmConfig.from_charm(charm=self)
        except CharmConfigInvalidError:
            return

        self.framework.observe(self.on.update_status, self._configure)
        self.framework.observe(self.on.config_changed, self._configure)
        self.framework.observe(self.on.ue_pebble_ready, self._configure)

    def _on_collect_unit_status(self, event: CollectStatusEvent):
        """Check the unit status and set to Unit when CollectStatusEvent is fired.

        Set the workload version if present in workload
        Args:
            event: CollectStatusEvent
        """
        if not self.unit.is_leader():
            # NOTE: In cases where leader status is lost before the charm is
            # finished processing all teardown events, this prevents teardown
            # event code from running. Luckily, for this charm, none of the
            # teardown code is necessary to perform if we're removing the
            # charm.
            event.add_status(BlockedStatus("Scaling is not implemented for this charm"))
            logger.info("Scaling is not implemented for this charm")
            return
        try:
            self._charm_config: CharmConfig = CharmConfig.from_charm(charm=self)  # type: ignore[no-redef]  # noqa: E501
        except CharmConfigInvalidError as exc:
            event.add_status(BlockedStatus(exc.msg))
            return
        if not self._container.can_connect():
            event.add_status(WaitingStatus("Waiting for container to be ready"))
            logger.info("Waiting for container to be ready")
            return
        if not _get_pod_ip():
            event.add_status(WaitingStatus("Waiting for Pod IP address to be available"))
            logger.info("Waiting for Pod IP address to be available")
            return
        self.unit.set_workload_version(self._get_workload_version())
        if not self._container.exists(path=BASE_CONFIG_PATH):
            event.add_status(WaitingStatus("Waiting for storage to be attached"))
            logger.info("Waiting for storage to be attached")
            return
        event.add_status(ActiveStatus())

    def _configure(self, _) -> None:  # noqa C901
        try:
            self._charm_config: CharmConfig = CharmConfig.from_charm(  # type: ignore[no-redef]  # noqa: E501
                charm=self
            )
        except CharmConfigInvalidError:
            return
        if not self._container.can_connect():
            return
        if not _get_pod_ip():
            return
        if not self._container.exists(path=BASE_CONFIG_PATH):
            return

        ue_config = self._generate_ue_config()
        if service_restart_required := self._is_ue_config_up_to_date(ue_config):
            self._write_config_file(content=ue_config)
        self._configure_pebble(restart=service_restart_required)

    def _generate_ue_config(self) -> str:
        return _render_config_file(
            imsi=self._charm_config.imsi,
            key=self._charm_config.key,
            opc=self._charm_config.opc,
            dnn=self._charm_config.dnn,
            sst=self._charm_config.sst,
        ).rstrip()

    def _is_ue_config_up_to_date(self, content: str) -> bool:
        """Decide whether config update is required by checking existence and config content.

        Args:
            content (str): desired config file content

        Returns:
            True if config update is required else False
        """
        if not self._config_file_content_matches(content=content):
            return True
        return False

    def _config_file_content_matches(self, content: str) -> bool:
        if not self._container.exists(path=f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}"):
            return False
        existing_content = self._container.pull(path=f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}")
        if existing_content.read() != content:
            return False
        return True

    def _write_config_file(self, content: str) -> None:
        self._container.push(source=content, path=f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}")
        logger.info("Config file written")

    def _configure_pebble(self, restart=False) -> None:
        """Configure the Pebble layer.

        Args:
            restart (bool): Whether to restart the DU container.
        """
        plan = self._container.get_plan()
        if plan.services != self._ue_pebble_layer.services:
            self._container.add_layer(self._container_name, self._ue_pebble_layer, combine=True)
            self._container.replan()
            logger.info("New layer added: %s", self._ue_pebble_layer)
        if restart:
            self._container.restart(self._service_name)
            logger.info("Restarted container %s", self._service_name)
            return
        self._container.replan()

    @property
    def _ue_pebble_layer(self) -> Layer:
        """Return pebble layer for the ue container.

        Returns:
            Layer: Pebble Layer
        """
        return Layer(
            {
                "services": {
                    self._service_name: {
                        "override": "replace",
                        "startup": "enabled",
                        "command": self._ue_startup_command,
                        "environment": self._ue_environment_variables,
                    },
                },
            }
        )

    @property
    def _ue_startup_command(self) -> str:
        return " ".join(
            [
                "/opt/oai-gnb/bin/nr-uesoftmodem",
                "-O",
                f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}",
                "--sa",
                "--rfsim",
                "--rfsimulator.serveraddr",
                self._du_address,
            ]
        )

    @property
    def _ue_environment_variables(self) -> dict:
        return {
            "TZ": "UTC",
        }

    @property
    def _du_address(self) -> str:
        """Return the DU address to connect to in simulation mode.

        TODO: This is currently hardcoded and the application name of
        the DU will need to match. This is expected to be replaced
        with an integration in the future.

        Returns:
            string: The address of the DU service
        """
        return "du"

    def _get_workload_version(self) -> str:
        """Return the workload version.

        Checks for the presence of /etc/workload-version file
        and if present, returns the contents of that file. If
        the file is not present, an empty string is returned.

        Returns:
            string: A human-readable string representing the version of the workload
        """
        if self._container.exists(path=WORKLOAD_VERSION_FILE_NAME):
            version_file_content = self._container.pull(path=WORKLOAD_VERSION_FILE_NAME).read()
            return version_file_content
        return ""


def _render_config_file(
    *,
    imsi: str,
    key: str,
    opc: str,
    dnn: str,
    sst: int,
) -> str:
    """Render UE config file based on parameters.

    Args:
        imsi: IMSI identifying this UE.
        key: Secret Key for USIM
        opc: Secret Key for operator
        dnn: Data Network Name
        sst: Slice Service Type

    Returns:
        str: Rendered UE configuration file
    """
    jinja2_env = Environment(loader=FileSystemLoader("src/templates"))
    template = jinja2_env.get_template(f"{CONFIG_FILE_NAME}.j2")
    return template.render(
        imsi=imsi,
        key=key,
        opc=opc,
        dnn=dnn,
        sst=sst,
    )


def _get_pod_ip() -> Optional[str]:
    """Return the pod IP using juju client.

    Returns:
        str: The pod IP.
    """
    ip_address = check_output(["unit-get", "private-address"])
    return str(IPv4Address(ip_address.decode().strip())) if ip_address else None


if __name__ == "__main__":  # pragma: nocover
    main(OaiRanUeK8SOperatorCharm)  # type: ignore
