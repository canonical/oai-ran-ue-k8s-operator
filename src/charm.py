#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed operator for the OAI RAN User Equipment (UE) for K8s."""

import logging
from ipaddress import IPv4Address
from subprocess import check_output
from typing import Optional, Tuple

from charms.loki_k8s.v1.loki_push_api import LogForwarder
from charms.oai_ran_du_k8s.v0.fiveg_rfsim import LIBAPI, RFSIMRequires
from jinja2 import Environment, FileSystemLoader
from ops import (
    ActiveStatus,
    BlockedStatus,
    CollectStatusEvent,
    Framework,
    WaitingStatus,
    main,
)
from ops.charm import ActionEvent, CharmBase
from ops.model import ModelError
from ops.pebble import ExecError, Layer

from charm_config import CharmConfig, CharmConfigInvalidError
from k8s import K8sPrivileged, K8sUSBVolume

logger = logging.getLogger(__name__)

BASE_CONFIG_PATH = "/tmp/conf"
CONFIG_FILE_NAME = "ue.conf"
LOGGING_RELATION_NAME = "logging"
RFSIM_RELATION_NAME = "fiveg_rfsim"
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
        self.rfsim_requirer = RFSIMRequires(self, RFSIM_RELATION_NAME)
        self._k8s_privileged = K8sPrivileged(
            namespace=self.model.name, statefulset_name=self.app.name
        )
        self._k8s_usb_volume = K8sUSBVolume(
            namespace=self.model.name,
            statefulset_name=self.app.name,
            unit_name=self.unit.name,
            container_name=self._container_name,
        )

        try:
            self._charm_config: CharmConfig = CharmConfig.from_charm(charm=self)
        except CharmConfigInvalidError:
            return

        self.framework.observe(self.on.update_status, self._configure)
        self.framework.observe(self.on.config_changed, self._configure)
        self.framework.observe(self.on.ue_pebble_ready, self._configure)
        self.framework.observe(self.on[RFSIM_RELATION_NAME].relation_changed, self._configure)
        self.framework.observe(self.on.ping_action, self._on_ping_action)

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
        if not self._k8s_privileged.is_patched(container_name=self._container_name):
            event.add_status(WaitingStatus("Waiting for statefulset to be patched"))
            logger.info("Waiting for statefulset to be patched")
            return
        if (
            not self._relation_created(RFSIM_RELATION_NAME)
            and not self._k8s_usb_volume.is_mounted()
        ):
            event.add_status(WaitingStatus("Waiting for USB device to be mounted"))
            logger.info("Waiting for USB device to be mounted")
            return
        if self._relation_created(RFSIM_RELATION_NAME) and (
            not all(
                [
                    self.rfsim_requirer.provider_interface_version,
                    self.rfsim_requirer.sst,
                    self.rfsim_requirer.sd,
                    self.rfsim_requirer.band,
                    self.rfsim_requirer.dl_freq,
                    self.rfsim_requirer.numerology,
                    self.rfsim_requirer.carrier_bandwidth,
                    self.rfsim_requirer.start_subcarrier,
                ]
            )
        ):
            event.add_status(WaitingStatus("Waiting for RFSIM information"))
            logger.info("Waiting for RFSIM information")
            return
        if self._relation_created(RFSIM_RELATION_NAME) and (
            self.rfsim_requirer.provider_interface_version != LIBAPI
        ):
            event.add_status(
                BlockedStatus(
                    "Can't establish communication over the `fiveg_rfsim` "
                    "interface due to version mismatch!"
                )
            )
            logger.error(
                "Can't establish communication over the `fiveg_rfsim` interface "
                "due to version mismatch!"
            )
            return
        if not self._container.exists(path=BASE_CONFIG_PATH):
            event.add_status(WaitingStatus("Waiting for storage to be attached"))
            logger.info("Waiting for storage to be attached")
            return
        self.unit.set_workload_version(self._get_workload_version())
        event.add_status(ActiveStatus())

    def _configure(self, _) -> None:
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
        if not self._k8s_privileged.is_patched(container_name=self._container_name):
            self._k8s_privileged.patch_statefulset(container_name=self._container_name)
        if (
            not self._relation_created(RFSIM_RELATION_NAME)
            and not self._k8s_usb_volume.is_mounted()
        ):
            self._k8s_usb_volume.mount()
        if self._relation_created(RFSIM_RELATION_NAME) and self._k8s_usb_volume.is_mounted():
            self._k8s_usb_volume.unmount()
        if self._relation_created(relation_name=RFSIM_RELATION_NAME) and (
            not self.rfsim_requirer.rfsim_address or not self.rfsim_requirer.sst
        ):
            return
        if not self._container.exists(path=BASE_CONFIG_PATH):
            return
        rfsim = self._relation_created(relation_name=RFSIM_RELATION_NAME)

        ue_config = self._generate_ue_config()
        if service_restart_required := self._is_ue_config_up_to_date(ue_config):
            self._write_config_file(content=ue_config)
        self._configure_pebble(rfsim=rfsim, restart=service_restart_required)

    @staticmethod
    def get_sd_as_hex(value: Optional[int]) -> str:
        """Return the SD in Hexadecimal."""
        if value is None:
            # According to TS 23.003, no SD is defined as 0xffffff
            return "0xffffff"
        return hex(value)

    def _get_sst(self) -> Optional[int]:
        if self._relation_created(RFSIM_RELATION_NAME):
            return self.rfsim_requirer.sst
        else:
            return self._charm_config.sst

    def _get_sd(self) -> Optional[int]:
        if self._relation_created(RFSIM_RELATION_NAME):
            return self.rfsim_requirer.sd
        else:
            return self._charm_config.sd

    def _on_ping_action(self, event: ActionEvent) -> None:
        """Run network traffic simulation.

        The action tries to ping `8.8.8.8` using the UE interface (oaitun_ue1). Working ping
        guarantees correctness of the deployment.
        To avoid deadlocks we're sending only 10 packets.
        """
        if not self._container.can_connect():
            event.fail(message="Container is not ready")
            return
        try:
            self._container.get_service(self._service_name)
        except ModelError:
            event.fail(message="UE service is not ready")
            return
        try:
            stdout, _ = self._exec_command_in_workload(command="ping -I oaitun_ue1 8.8.8.8 -c 10")
            event.set_results(
                {
                    "success": "true",
                    "result": stdout,
                }
            )
        except ExecError as e:
            event.fail(message=f"Failed to execute simulation: {str(e.stdout)}")

    def _generate_ue_config(self) -> str:
        sst = self._get_sst()
        sd = self._get_sd()
        if not sst:
            logger.error("SST is not available")
            return ""
        return _render_config_file(
            imsi=self._charm_config.imsi,
            key=self._charm_config.key,
            opc=self._charm_config.opc,
            dnn=self._charm_config.dnn,
            sst=sst,
            sd=self.get_sd_as_hex(sd),
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

    def _relation_created(self, relation_name: str) -> bool:
        """Return whether a given Juju relation was created.

        Args:
            relation_name (str): Relation name

        Returns:
            bool: Whether the relation was created.
        """
        return bool(self.model.relations.get(relation_name))

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

    def _configure_pebble(self, rfsim: bool, restart: bool = False) -> None:
        """Configure the Pebble layer.

        Args:
            rfsim (bool): Whether to configure the UE for RF simulator.
            restart (bool): Whether to restart the DU container.
        """
        plan = self._container.get_plan()
        pebble_layer = self._get_ue_pebble_layer(rfsim=rfsim)
        if plan.services != pebble_layer.services:
            self._container.add_layer(self._container_name, pebble_layer, combine=True)
            self._container.replan()
            logger.info("New layer added: %s", pebble_layer)
        if restart:
            self._container.restart(self._service_name)
            logger.info("Restarted container %s", self._service_name)
            return
        self._container.replan()

    def _get_ue_pebble_layer(self, rfsim: bool) -> Layer:
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
                        "command": self._get_ue_startup_command(rfsim=rfsim),
                        "environment": self._ue_environment_variables,
                    },
                },
            }
        )

    def _get_ue_startup_command(self, rfsim: bool) -> str:
        if rfsim:
            return " ".join(
                [
                    "/opt/oai-gnb/bin/nr-uesoftmodem",
                    "-O",
                    f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}",
                    "--rfsim",
                    "-r",
                    str(self.rfsim_requirer.carrier_bandwidth),
                    "--numerology",
                    str(self.rfsim_requirer.numerology),
                    "-C",
                    str(self.rfsim_requirer.dl_freq),
                    "--ssb",
                    str(self.rfsim_requirer.start_subcarrier),
                    "--band",
                    str(self.rfsim_requirer.band),
                    "--log_config.global_log_options",
                    "level,nocolor,time",
                    "--rfsimulator.serveraddr",
                    str(self.rfsim_requirer.rfsim_address)
                    if self.rfsim_requirer.rfsim_address
                    else "",
                ]
            )
        return " ".join(
            [
                "/opt/oai-gnb/bin/nr-uesoftmodem",
                "-O",
                f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}",
                "-r",
                str(self.rfsim_requirer.carrier_bandwidth),
                "--numerology",
                str(self.rfsim_requirer.numerology),
                "-C",
                str(self.rfsim_requirer.dl_freq),
                "--ssb",
                str(self.rfsim_requirer.start_subcarrier),
                "--band",
                str(self.rfsim_requirer.band),
                "-E",
                "--log_config.global_log_options",
                "level,nocolor,time",
            ]
        )

    def _exec_command_in_workload(self, command: str) -> Tuple[Optional[str], Optional[str]]:
        """Execute command in workload container.

        Args:
            command: Command to execute
        """
        process = self._container.exec(
            command=command.split(),
            timeout=300,
        )
        return process.wait_output()

    @property
    def _ue_environment_variables(self) -> dict:
        return {
            "TZ": "UTC",
        }

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
    sd: str,
) -> str:
    """Render UE config file based on parameters.

    Args:
        imsi: IMSI identifying this UE.
        key: Secret Key for USIM
        opc: Secret Key for operator
        dnn: Data Network Name
        sst: Slice Service Type
        sd: Slice Differentiator

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
        sd=sd,
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
