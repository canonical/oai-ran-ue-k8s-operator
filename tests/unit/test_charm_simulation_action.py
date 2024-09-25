#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import tempfile

import scenario
from ops.pebble import Layer, ServiceStatus
from tests.unit.fixtures import UEFixtures


class TestCharmConfigure(UEFixtures):
    def test_given_ue_container_not_available_when_start_simulation_action_then_action_status_is_failed(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_check_output.return_value = b"1.2.3.4"
            rfsim_relation = scenario.Relation(
                endpoint="fiveg_rfsim",
                interface="fiveg_rfsim",
                remote_app_data={
                    "rfsim_address": "1.1.1.1",
                },
            )
            config_mount = scenario.Mount(
                src=temp_dir,
                location="/tmp/conf",
            )
            container = scenario.Container(
                name="ue",
                can_connect=False,
                mounts={
                    "config": config_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                relations=[rfsim_relation],
                containers=[container],
            )

            action_results = self.ctx.run_action("start-simulation", state_in)

            assert not action_results.success
            assert action_results.failure
            assert action_results.failure == "Container is not ready"

    def test_given_ue_service_not_ready_when_start_simulation_action_then_action_status_is_failed(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_check_output.return_value = b"1.2.3.4"
            rfsim_relation = scenario.Relation(
                endpoint="fiveg_rfsim",
                interface="fiveg_rfsim",
                remote_app_data={
                    "rfsim_address": "1.1.1.1",
                },
            )
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
                relations=[rfsim_relation],
                containers=[container],
            )

            action_results = self.ctx.run_action("start-simulation", state_in)

            assert not action_results.success
            assert action_results.failure
            assert action_results.failure == "UE service is not ready"

    def test_given_ping_transmits_packets_correctly_when_start_simulation_action_then_action_status_is_successful(  # noqa: E501
        self,
    ):
        test_successful_stdout = "10 packets transmitted, 10 received, 0% packet loss, time 9012ms"
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_check_output.return_value = b"1.2.3.4"
            rfsim_relation = scenario.Relation(
                endpoint="fiveg_rfsim",
                interface="fiveg_rfsim",
                remote_app_data={
                    "rfsim_address": "1.1.1.1",
                },
            )
            config_mount = scenario.Mount(
                src=temp_dir,
                location="/tmp/conf",
            )
            container = scenario.Container(
                name="ue",
                can_connect=True,
                layers={"ue": Layer({"services": {"ue": {}}})},
                service_status={"ue": ServiceStatus.ACTIVE},
                mounts={
                    "config": config_mount,
                },
                exec_mock={
                    ("ping", "-I", "oaitun_ue1", "8.8.8.8", "-c", "10"): scenario.ExecOutput(
                        return_code=0,
                        stdout=test_successful_stdout,
                        stderr="",
                    ),
                },
            )
            state_in = scenario.State(
                leader=True,
                relations=[rfsim_relation],
                containers=[container],
            )

            action_results = self.ctx.run_action("start-simulation", state_in)

            assert action_results.success
            assert action_results.results
            assert action_results.results["success"] == "true"
            assert action_results.results["result"] == test_successful_stdout

    def test_given_ping_doesnt_transmit_packets_correctly_when_start_simulation_action_then_action_status_is_failed(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_check_output.return_value = b"1.2.3.4"
            rfsim_relation = scenario.Relation(
                endpoint="fiveg_rfsim",
                interface="fiveg_rfsim",
                remote_app_data={
                    "rfsim_address": "1.1.1.1",
                },
            )
            config_mount = scenario.Mount(
                src=temp_dir,
                location="/tmp/conf",
            )
            container = scenario.Container(
                name="ue",
                can_connect=True,
                layers={"ue": Layer({"services": {"ue": {}}})},
                service_status={"ue": ServiceStatus.ACTIVE},
                mounts={
                    "config": config_mount,
                },
                exec_mock={
                    ("ping", "-I", "oaitun_ue1", "8.8.8.8", "-c", "10"): scenario.ExecOutput(
                        return_code=1,
                        stdout="10 packets transmitted, 0 received, 100% packet loss, time 9012ms",
                        stderr="",
                    ),
                },
            )
            state_in = scenario.State(
                leader=True,
                relations=[rfsim_relation],
                containers=[container],
            )

            action_results = self.ctx.run_action("start-simulation", state_in)

            assert not action_results.success
            assert action_results.failure
            assert "Failed to execute simulation:" in action_results.failure
