#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import tempfile

import pytest
from charms.oai_ran_du_k8s.v0.fiveg_rfsim import LIBAPI
from ops import testing
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus

from tests.unit.fixtures import UEFixtures

INVALID_FIVEG_RFSIM_API_VERSION = str(LIBAPI + 1)


class TestCharmCollectStatus(UEFixtures):
    def test_given_unit_is_not_leader_when_collect_status_then_status_is_blocked(self):
        self.mock_k8s_usb_volume.is_mounted.return_value = False
        state_in = testing.State(
            leader=False,
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == BlockedStatus("Scaling is not implemented for this charm")

    @pytest.mark.parametrize(
        "config_param,value",
        [
            pytest.param("imsi", "", id="empty_imsi"),
            pytest.param("imsi", "123abc", id="too_short_imsi"),
            pytest.param("imsi", "123abc123abc123abc", id="too_long_imsi"),
            pytest.param("key", "", id="empty_key"),
            pytest.param("key", "123abc", id="too_short_key"),
            pytest.param("key", "123abc123abc123abc123abc123abc123abc123abc", id="too_long_key"),
            pytest.param("opc", "", id="empty_opc"),
            pytest.param("opc", "123abc", id="too_short_opc"),
            pytest.param("opc", "123abc123abc123abc123abc123abc123abc123abc", id="too_long_opc"),
            pytest.param("dnn", "", id="empty_dnn"),
        ],
    )
    def test_given_invalid_config_when_collect_status_then_status_is_blocked(
        self, config_param, value
    ):
        self.mock_k8s_usb_volume.is_mounted.return_value = False
        state_in = testing.State(
            leader=True,
            config={config_param: value},
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == BlockedStatus(
            f"The following configurations are not valid: ['{config_param}']"
        )

    def test_given_fiveg_rfsim_relation_not_created_and_usb_not_mounted_when_collect_unit_status_then_status_is_waiting(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_k8s_usb_volume.is_mounted.return_value = False
            self.mock_check_output.return_value = b"1.1.1.1"
            config_mount = testing.Mount(
                source=temp_dir,
                location="/tmp/conf",
            )
            container = testing.Container(
                name="ue",
                can_connect=True,
                mounts={"config": config_mount},
            )
            state_in = testing.State(
                leader=True,
                relations=[],
                containers=[container],
            )

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.unit_status == WaitingStatus("Waiting for USB device to be mounted")

    def test_given_fiveg_rfsim_relation_created_but_provider_uses_different_interface_version_when_collect_unit_status_then_status_is_blocked(  # noqa: E501
        self,
    ):
        self.mock_k8s_usb_volume.is_mounted.return_value = False
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"
            rfsim_relation = testing.Relation(
                endpoint="fiveg_rfsim",
                interface="fiveg_rfsim",
                remote_app_data={
                    "version": INVALID_FIVEG_RFSIM_API_VERSION,
                    "rfsim_address": "1.1.1.1",
                    "sst": "1",
                    "sd": "12555",
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
                mounts={"config": config_mount},
            )
            state_in = testing.State(
                leader=True,
                relations=[rfsim_relation],
                containers=[container],
            )

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.unit_status == BlockedStatus(
                "Can't establish communication over the `fiveg_rfsim` "
                "interface due to version mismatch!"
            )

    @pytest.mark.parametrize(
        "remote_app_data",
        [
            pytest.param(
                {
                    "version": str(LIBAPI),
                    "sst": "1",
                    "band": "77",
                    "dl_freq": "3924060000",
                    "carrier_bandwidth": "106",
                    "numerology": "1",
                    "start_subcarrier": "529",
                },
                id="rfsim_address_missing",
            ),
            pytest.param(
                {
                    "version": str(LIBAPI),
                    "rfsim_address": "1.1.1.1",
                    "band": "77",
                    "dl_freq": "3924060000",
                    "carrier_bandwidth": "106",
                    "numerology": "1",
                    "start_subcarrier": "529",
                },
                id="sst_missing",
            ),
            pytest.param(
                {
                    "version": str(LIBAPI),
                    "rfsim_address": "1.1.1.1",
                    "sst": "1",
                    "dl_freq": "3924060000",
                    "carrier_bandwidth": "106",
                    "numerology": "1",
                    "start_subcarrier": "529",
                },
                id="band_missing",
            ),
            pytest.param(
                {
                    "version": str(LIBAPI),
                    "rfsim_address": "1.1.1.1",
                    "sst": "1",
                    "band": "77",
                    "carrier_bandwidth": "106",
                    "numerology": "1",
                    "start_subcarrier": "529",
                },
                id="dl_freq_missing",
            ),
            pytest.param(
                {
                    "version": str(LIBAPI),
                    "rfsim_address": "1.1.1.1",
                    "sst": "1",
                    "band": "77",
                    "dl_freq": "3924060000",
                    "numerology": "1",
                    "start_subcarrier": "529",
                },
                id="carrier_bandwidth_missing",
            ),
            pytest.param(
                {
                    "version": str(LIBAPI),
                    "rfsim_address": "1.1.1.1",
                    "sst": "1",
                    "band": "77",
                    "dl_freq": "3924060000",
                    "carrier_bandwidth": "106",
                    "start_subcarrier": "529",
                },
                id="numerology_missing",
            ),
            pytest.param(
                {
                    "version": str(LIBAPI),
                    "rfsim_address": "1.1.1.1",
                    "sst": "1",
                    "band": "77",
                    "dl_freq": "3924060000",
                    "carrier_bandwidth": "106",
                    "numerology": "1",
                },
                id="start_subcarrier_missing",
            ),
        ],
    )
    def test_given_fiveg_rfsim_relation_created_but_configuration_parameters_are_missing_from_the_relation_data_when_collect_unit_status_then_status_is_waiting(  # noqa: E501
        self, remote_app_data
    ):
        self.mock_k8s_usb_volume.is_mounted.return_value = False
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"
            rfsim_relation = testing.Relation(
                endpoint="fiveg_rfsim",
                interface="fiveg_rfsim",
                remote_app_data=remote_app_data,
            )
            config_mount = testing.Mount(
                source=temp_dir,
                location="/tmp/conf",
            )
            container = testing.Container(
                name="ue",
                can_connect=True,
                mounts={"config": config_mount},
            )
            state_in = testing.State(
                leader=True,
                relations=[rfsim_relation],
                containers=[container],
            )

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.unit_status == WaitingStatus("Waiting for RFSIM information")

    def test_given_cant_connect_to_container_when_collect_status_then_status_is_waiting(self):
        self.mock_k8s_usb_volume.is_mounted.return_value = False
        container = testing.Container(
            name="ue",
            can_connect=False,
        )
        state_in = testing.State(
            leader=True,
            relations=[],
            containers=[container],
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for container to be ready")

    def test_given_pod_address_not_available_when_collect_status_then_status_is_waiting(self):
        self.mock_k8s_usb_volume.is_mounted.return_value = False
        self.mock_check_output.return_value = b""
        container = testing.Container(
            name="ue",
            can_connect=True,
        )
        state_in = testing.State(
            leader=True,
            relations=[],
            containers=[container],
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for Pod IP address to be available")

    def test_given_charm_statefulset_is_not_patched_when_collect_unit_status_then_status_is_waiting(  # noqa: E501
        self,
    ):
        self.mock_k8s_usb_volume.is_mounted.return_value = False
        self.mock_k8s_privileged.is_patched.return_value = False
        self.mock_check_output.return_value = b"1.2.3.4"
        container = testing.Container(
            name="ue",
            can_connect=True,
        )
        state_in = testing.State(
            leader=True,
            relations=[],
            containers=[container],
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for statefulset to be patched")

    def test_given_config_file_doesnt_exist_when_collect_status_then_status_is_waiting(self):
        self.mock_k8s_usb_volume.is_mounted.return_value = True
        self.mock_check_output.return_value = b"1.2.3.4"

        container = testing.Container(
            name="ue",
            can_connect=True,
        )
        state_in = testing.State(
            leader=True,
            relations=[],
            containers=[container],
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for storage to be attached")

    def test_given_all_prerequisites_met_when_collect_status_then_status_is_active(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_usb_volume.is_mounted.return_value = True
            self.mock_check_output.return_value = b"1.2.3.4"
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
                relations=[],
                containers=[container],
            )

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.unit_status == ActiveStatus()
