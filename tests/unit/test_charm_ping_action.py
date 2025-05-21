#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import tempfile

import pytest
from charms.oai_ran_du_k8s.v0.fiveg_rf_config import LIBAPI
from ops import testing
from ops.pebble import Layer, ServiceStatus
from ops.testing import ActionFailed

from src.charm import RF_CONFIG_RELATION_NAME
from tests.unit.fixtures import UEFixtures


class TestCharmPingAction(UEFixtures):
    def test_given_ue_container_not_available_when_ping_action_then_action_status_is_failed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_check_output.return_value = b"1.2.3.4"
            config_mount = testing.Mount(
                source=temp_dir,
                location="/tmp/conf",
            )
            container = testing.Container(
                name="ue",
                can_connect=False,
                mounts={
                    "config": config_mount,
                },
            )
            state_in = testing.State(
                leader=True,
                containers=[container],
            )

            with pytest.raises(ActionFailed) as exc_info:
                self.ctx.run(self.ctx.on.action("ping"), state_in)

            assert exc_info.value.message == "Container is not ready"

    def test_given_ue_service_not_ready_when_ping_action_then_action_status_is_failed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_check_output.return_value = b"1.2.3.4"
            rf_config_relation = testing.Relation(
                endpoint=RF_CONFIG_RELATION_NAME,
                interface=RF_CONFIG_RELATION_NAME,
                remote_app_data={
                    "version": str(LIBAPI),
                    "sst": "1",
                    "band": "77",
                    "dl_freq": "3924060000",
                    "carrier_bandwidth": "106",
                    "numerology": "1",
                    "start_subcarrier": "529",
                },
            )
            config_mount = testing.Mount(
                source=temp_dir,
                location="/tmp/conf",
            )
            container = testing.Container(
                name="ue",
                can_connect=True,
                mounts={
                    "config": config_mount,
                },
            )
            state_in = testing.State(
                leader=True,
                relations=[rf_config_relation],
                containers=[container],
            )

            with pytest.raises(ActionFailed) as exc_info:
                self.ctx.run(self.ctx.on.action("ping"), state_in)

            assert exc_info.value.message == "UE service is not ready"

    def test_given_ping_transmits_packets_correctly_when_ping_action_then_action_status_is_successful(  # noqa: E501
        self,
    ):
        test_successful_stdout = "10 packets transmitted, 10 received, 0% packet loss, time 9012ms"
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_check_output.return_value = b"1.2.3.4"
            rf_config_relation = testing.Relation(
                endpoint=RF_CONFIG_RELATION_NAME,
                interface=RF_CONFIG_RELATION_NAME,
                remote_app_data={
                    "version": str(LIBAPI),
                    "sst": "1",
                    "band": "77",
                    "dl_freq": "3924060000",
                    "carrier_bandwidth": "106",
                    "numerology": "1",
                    "start_subcarrier": "529",
                },
            )
            config_mount = testing.Mount(
                source=temp_dir,
                location="/tmp/conf",
            )
            container = testing.Container(
                name="ue",
                can_connect=True,
                layers={"ue": Layer({"services": {"ue": {}}})},
                service_statuses={"ue": ServiceStatus.ACTIVE},
                mounts={
                    "config": config_mount,
                },
                execs={
                    testing.Exec(
                        command_prefix=["ping", "-I", "oaitun_ue1", "8.8.8.8", "-c", "10"],
                        return_code=0,
                        stdout=test_successful_stdout,
                        stderr="",
                    )
                },
            )
            state_in = testing.State(
                leader=True,
                relations=[rf_config_relation],
                containers=[container],
            )

            self.ctx.run(self.ctx.on.action("ping"), state_in)

            assert self.ctx.action_results
            assert self.ctx.action_results["result"] == test_successful_stdout

    def test_given_ping_doesnt_transmit_packets_correctly_when_ping_action_then_action_status_is_failed(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_check_output.return_value = b"1.2.3.4"
            rf_config_relation = testing.Relation(
                endpoint=RF_CONFIG_RELATION_NAME,
                interface=RF_CONFIG_RELATION_NAME,
                remote_app_data={
                    "version": str(LIBAPI),
                    "sst": "1",
                    "band": "77",
                    "dl_freq": "3924060000",
                    "carrier_bandwidth": "106",
                    "numerology": "1",
                    "start_subcarrier": "529",
                },
            )
            config_mount = testing.Mount(
                source=temp_dir,
                location="/tmp/conf",
            )
            container = testing.Container(
                name="ue",
                can_connect=True,
                layers={"ue": Layer({"services": {"ue": {}}})},
                service_statuses={"ue": ServiceStatus.ACTIVE},
                mounts={
                    "config": config_mount,
                },
                execs={
                    testing.Exec(
                        command_prefix=["ping", "-I", "oaitun_ue1", "8.8.8.8", "-c", "10"],
                        return_code=1,
                        stdout="10 packets transmitted, 0 received, 100% packet loss, time 9012ms",
                        stderr="",
                    )
                },
            )
            state_in = testing.State(
                leader=True,
                relations=[rf_config_relation],
                containers=[container],
            )

            with pytest.raises(ActionFailed) as exc_info:
                self.ctx.run(self.ctx.on.action("ping"), state_in)

            assert "Failed to execute simulation:" in exc_info.value.message
