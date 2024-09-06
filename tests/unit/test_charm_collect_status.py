#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import tempfile

import pytest
import scenario
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus

from tests.unit.fixtures import UEFixtures


class TestCharmCollectStatus(UEFixtures):
    def test_given_unit_is_not_leader_when_collect_status_then_status_is_blocked(self):
        state_in = scenario.State(
            leader=False,
        )

        state_out = self.ctx.run("collect_unit_status", state_in)

        assert state_out.unit_status == BlockedStatus("Scaling is not implemented for this charm")

    @pytest.mark.parametrize(
        "config_param,value",
        [
            pytest.param("imsi", "", id="empty_imsi"),
            pytest.param("key", "", id="empty_key"),
            pytest.param("opc", "", id="empty_opc"),
            pytest.param("dnn", "", id="empty_dnn"),
            pytest.param("sst", int(), id="empty_sst"),
        ],
    )
    def test_given_invalid_config_when_collect_status_then_status_is_blocked(
        self, config_param, value
    ):
        state_in = scenario.State(
            leader=True,
            config={config_param: value},
        )

        state_out = self.ctx.run("collect_unit_status", state_in)

        assert state_out.unit_status == BlockedStatus(
            f"The following configurations are not valid: ['{config_param}']"
        )

    def test_given_cant_connect_to_container_when_collect_status_then_status_is_waiting(self):
        container = scenario.Container(
            name="ue",
            can_connect=False,
        )
        state_in = scenario.State(
            leader=True,
            relations=[],
            containers=[container],
        )

        state_out = self.ctx.run("collect_unit_status", state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for container to be ready")

    def test_given_pod_address_not_available_when_collect_status_then_status_is_waiting(self):
        self.mock_check_output.return_value = b""
        container = scenario.Container(
            name="ue",
            can_connect=True,
        )
        state_in = scenario.State(
            leader=True,
            relations=[],
            containers=[container],
        )

        state_out = self.ctx.run("collect_unit_status", state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for Pod IP address to be available")

    def test_given_config_file_doesnt_exist_when_collect_status_then_status_is_waiting(self):
        self.mock_check_output.return_value = b"1.2.3.4"
        container = scenario.Container(
            name="ue",
            can_connect=True,
        )
        state_in = scenario.State(
            leader=True,
            relations=[],
            containers=[container],
        )

        state_out = self.ctx.run("collect_unit_status", state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for storage to be attached")

    def test_given_all_prerequisites_met_when_collect_status_then_status_is_active(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_check_output.return_value = b"1.2.3.4"
            config_mount = scenario.Mount(
                src=temp_dir,
                location="/tmp/conf",
            )
            container = scenario.Container(
                name="ue",
                can_connect=True,
                mounts={
                    "config": config_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                relations=[],
                containers=[container],
            )

            state_out = self.ctx.run("collect_unit_status", state_in)

            assert state_out.unit_status == ActiveStatus()
