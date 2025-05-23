#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import os
import tempfile

import pytest
from charms.oai_ran_du_k8s.v0.fiveg_rf_config import LIBAPI
from ops import testing
from ops.pebble import Layer

from src.charm import RF_CONFIG_RELATION_NAME
from tests.unit.fixtures import UEFixtures

INVALID_FIVEG_RF_CONFIG_API_VERSION = str(LIBAPI + 1)
VALID_SIMULATION_MODE_RF_CONFIG_REMOTE_DATA_WITHOUT_SD = {
    "version": str(LIBAPI),
    "rfsim_address": "1.1.1.1",
    "sst": "1",
    "band": "77",
    "dl_freq": "3924060000",
    "carrier_bandwidth": "106",
    "numerology": "1",
    "start_subcarrier": "529",
}
VALID_NON_SIMULATION_MODE_RF_CONFIG_REMOTE_DATA_WITHOUT_SD = {
    "version": str(LIBAPI),
    "sst": "1",
    "band": "77",
    "dl_freq": "3924060000",
    "carrier_bandwidth": "106",
    "numerology": "1",
    "start_subcarrier": "529",
}
VALID_RF_CONFIG_REMOTE_DATA_WITH_SD = {
    "version": str(LIBAPI),
    "rfsim_address": "1.1.1.1",
    "sst": "2",
    "sd": "12555",
    "band": "77",
    "dl_freq": "3924060000",
    "carrier_bandwidth": "106",
    "numerology": "1",
    "start_subcarrier": "529",
}


class TestCharmConfigure(UEFixtures):
    def test_given_statefulset_is_not_patched_when_config_changed_then_statefulset_is_patched(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.mock_k8s_privileged.is_patched.return_value = False
            self.mock_k8s_usb_volume.is_mounted.return_value = False
            self.mock_check_output.return_value = b"1.2.3.4"
            config_mount = testing.Mount(
                location="/tmp/conf",
                source=tmpdir,
            )
            container = testing.Container(
                name="ue",
                mounts={"config": config_mount},
                can_connect=True,
            )
            state_in = testing.State(
                leader=True,
                containers=[container],
                relations=[],
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_k8s_privileged.patch_statefulset.assert_called_with(container_name="ue")

    def test_given_workload_is_ready_to_be_configured_and_ue_startup_params_are_available_when_configure_then_ue_config_file_is_generated_and_pushed_to_the_workload_container(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_check_output.return_value = b"1.2.3.4"
            self.mock_k8s_usb_volume.is_mounted.return_value = False
            rf_config_relation = testing.Relation(
                endpoint=RF_CONFIG_RELATION_NAME,
                interface=RF_CONFIG_RELATION_NAME,
                remote_app_data=VALID_SIMULATION_MODE_RF_CONFIG_REMOTE_DATA_WITHOUT_SD,
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
                model=testing.Model(name="whatever"),
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            with open(
                "tests/unit/resources/expected_config_without_sd.conf"
            ) as expected_config_file:
                expected_config = expected_config_file.read()

            with open(f"{temp_dir}/ue.conf") as generated_config_file:
                generated_config = generated_config_file.read()

            assert generated_config.strip() == expected_config.strip()

    def test_given_workload_is_ready_to_be_configured_but_sst_is_not_available_when_configure_then_ue_config_file_is_not_generated(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_usb_volume.is_mounted.return_value = False
            self.mock_check_output.return_value = b"1.2.3.4"
            rf_config_relation = testing.Relation(
                endpoint=RF_CONFIG_RELATION_NAME,
                interface=RF_CONFIG_RELATION_NAME,
                remote_app_data={
                    "version": "0",
                    "rfsim_address": "1.1.1.1",
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
                model=testing.Model(name="whatever"),
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            with pytest.raises(Exception) as e:
                with open(f"{temp_dir}/ue.conf") as generated_config_file:
                    generated_config_file.read()
            assert "No such file or directory" in str(e.value)

    def test_given_ue_config_file_is_up_to_date_when_configure_then_ue_config_file_is_not_pushed_to_the_workload_container(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_usb_volume.is_mounted.return_value = False
            self.mock_check_output.return_value = b"1.2.3.4"
            rf_config_relation = testing.Relation(
                endpoint=RF_CONFIG_RELATION_NAME,
                interface=RF_CONFIG_RELATION_NAME,
                remote_app_data=VALID_SIMULATION_MODE_RF_CONFIG_REMOTE_DATA_WITHOUT_SD,
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
                model=testing.Model(name="whatever"),
            )
            with open(
                "tests/unit/resources/expected_config_without_sd.conf"
            ) as expected_config_file:
                expected_config = expected_config_file.read().strip()

            with open(f"{temp_dir}/ue.conf", "w") as generated_config_file:
                generated_config_file.write(expected_config)

            config_modification_time = os.stat(temp_dir + "/ue.conf").st_mtime

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert os.stat(temp_dir + "/ue.conf").st_mtime == config_modification_time

    def test_given_ue_config_file_is_up_to_date_when_rf_config_relation_changed_then_ue_config_file_is_not_pushed_to_the_workload_container(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_usb_volume.is_mounted.return_value = False
            self.mock_check_output.return_value = b"1.2.3.4"
            rf_config_relation = testing.Relation(
                endpoint=RF_CONFIG_RELATION_NAME,
                interface=RF_CONFIG_RELATION_NAME,
                remote_app_data=VALID_SIMULATION_MODE_RF_CONFIG_REMOTE_DATA_WITHOUT_SD,
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
                model=testing.Model(name="whatever"),
            )
            with open(
                "tests/unit/resources/expected_config_without_sd.conf"
            ) as expected_config_file:
                expected_config = expected_config_file.read().strip()

            with open(f"{temp_dir}/ue.conf", "w") as generated_config_file:
                generated_config_file.write(expected_config)

            config_modification_time = os.stat(temp_dir + "/ue.conf").st_mtime

            self.ctx.run(self.ctx.on.relation_changed(rf_config_relation), state_in)

            assert os.stat(temp_dir + "/ue.conf").st_mtime == config_modification_time

    def test_given_ue_config_exists_when_rf_config_relation_changed_then_new_ue_config_file_is_pushed_to_the_workload_container(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_usb_volume.is_mounted.return_value = False
            self.mock_check_output.return_value = b"1.2.3.4"
            rf_config_relation = testing.Relation(
                endpoint=RF_CONFIG_RELATION_NAME,
                interface=RF_CONFIG_RELATION_NAME,
                remote_app_data=VALID_RF_CONFIG_REMOTE_DATA_WITH_SD,
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
                model=testing.Model(name="whatever"),
            )

            with open("tests/unit/resources/expected_config_without_sd.conf") as old_config_file:
                old_config = old_config_file.read().strip()

            with open(f"{temp_dir}/ue.conf", "w") as generated_config_file:
                generated_config_file.write(old_config)

            config_modification_time = os.stat(temp_dir + "/ue.conf").st_mtime

            self.ctx.run(self.ctx.on.relation_changed(rf_config_relation), state_in)

            with open(f"{temp_dir}/ue.conf") as updated_config_file:
                updated_config = updated_config_file.read()

            with open("tests/unit/resources/expected_config_with_sd.conf") as expected_config_file:
                expected_config = expected_config_file.read()

            assert updated_config.strip() == expected_config.strip()

            assert os.stat(temp_dir + "/ue.conf").st_mtime != config_modification_time

    def test_given_charm_running_in_simulation_mode_and_can_connect_when_configure_then_pebble_layer_is_created(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_usb_volume.is_mounted.return_value = False
            self.mock_check_output.return_value = b"1.2.3.4"
            rf_config_relation = testing.Relation(
                endpoint=RF_CONFIG_RELATION_NAME,
                interface=RF_CONFIG_RELATION_NAME,
                remote_app_data=VALID_SIMULATION_MODE_RF_CONFIG_REMOTE_DATA_WITHOUT_SD,
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
                config={"simulation-mode": True},
                relations=[rf_config_relation],
                containers=[container],
                model=testing.Model(name="whatever"),
            )

            state_out = self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            container = state_out.get_container("ue")
            assert container.layers == {
                "ue": Layer(
                    {
                        "services": {
                            "ue": {
                                "startup": "enabled",
                                "override": "replace",
                                "command": "/opt/oai-gnb/bin/nr-uesoftmodem -O /tmp/conf/ue.conf -r 106 --numerology 1 -C 3924060000 --ssb 529 --band 77 --log_config.global_log_options level,nocolor,time --rfsim --rfsimulator.serveraddr 1.1.1.1",  # noqa: E501
                                "environment": {"TZ": "UTC"},
                            }
                        }
                    }
                )
            }

    def test_given_charm_running_in_non_simulation_mode_and_can_connect_when_configure_then_pebble_layer_is_created(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_usb_volume.is_mounted.return_value = True
            self.mock_check_output.return_value = b"1.2.3.4"
            rf_config_relation = testing.Relation(
                endpoint=RF_CONFIG_RELATION_NAME,
                interface=RF_CONFIG_RELATION_NAME,
                remote_app_data=VALID_NON_SIMULATION_MODE_RF_CONFIG_REMOTE_DATA_WITHOUT_SD,
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
                model=testing.Model(name="whatever"),
            )

            state_out = self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            container = state_out.get_container("ue")
            assert container.layers == {
                "ue": Layer(
                    {
                        "services": {
                            "ue": {
                                "startup": "enabled",
                                "override": "replace",
                                "command": "/opt/oai-gnb/bin/nr-uesoftmodem -O /tmp/conf/ue.conf -r 106 --numerology 1 -C 3924060000 --ssb 529 --band 77 --log_config.global_log_options level,nocolor,time",  # noqa: E501
                                "environment": {"TZ": "UTC"},
                            }
                        }
                    }
                )
            }

    def test_given_three_quarter_sampling_enabled_when_configure_then_ue_startup_command_has_correct_params(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_usb_volume.is_mounted.return_value = False
            self.mock_check_output.return_value = b"1.2.3.4"
            rf_config_relation = testing.Relation(
                endpoint=RF_CONFIG_RELATION_NAME,
                interface=RF_CONFIG_RELATION_NAME,
                remote_app_data=VALID_SIMULATION_MODE_RF_CONFIG_REMOTE_DATA_WITHOUT_SD,
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
                model=testing.Model(name="whatever"),
                config={"simulation-mode": True, "use-three-quarter-sampling": True},
            )

            state_out = self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            container = state_out.get_container("ue")
            ue_pebble_layer = container.layers["ue"].to_dict()
            ue_startup_command = (
                ue_pebble_layer.get("services", {}).get("ue", {}).get("command", "")
            )
            assert (
                ue_startup_command
                == "/opt/oai-gnb/bin/nr-uesoftmodem -O /tmp/conf/ue.conf -r 106 --numerology 1 -C 3924060000 --ssb 529 --band 77 --log_config.global_log_options level,nocolor,time --rfsim --rfsimulator.serveraddr 1.1.1.1 -E"  # noqa: E501
            )

    def test_given_use_mimo_enabled_when_configure_then_ue_startup_command_has_correct_params(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_usb_volume.is_mounted.return_value = False
            self.mock_check_output.return_value = b"1.2.3.4"
            rf_config_relation = testing.Relation(
                endpoint=RF_CONFIG_RELATION_NAME,
                interface=RF_CONFIG_RELATION_NAME,
                remote_app_data=VALID_SIMULATION_MODE_RF_CONFIG_REMOTE_DATA_WITHOUT_SD,
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
                model=testing.Model(name="whatever"),
                config={"simulation-mode": True, "use-mimo": True},
            )

            state_out = self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            container = state_out.get_container("ue")
            ue_pebble_layer = container.layers["ue"].to_dict()
            ue_startup_command = (
                ue_pebble_layer.get("services", {}).get("ue", {}).get("command", "")
            )
            assert (
                ue_startup_command
                == "/opt/oai-gnb/bin/nr-uesoftmodem -O /tmp/conf/ue.conf -r 106 --numerology 1 -C 3924060000 --ssb 529 --band 77 --log_config.global_log_options level,nocolor,time --rfsim --rfsimulator.serveraddr 1.1.1.1 --ue-nb-ant-tx 2 --ue-nb-ant-rx 2"  # noqa: E501
            )

    @pytest.mark.parametrize(
        "remote_app_data",
        [
            pytest.param(
                {
                    "version": str(LIBAPI),
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
    def test_given_charm_running_in_non_simulation_mode_and_can_connect_to_the_container_but_configuration_parameters_are_missing_from_the_fiveg_rf_config_relation_data_when_configure_then_pebble_layer_is_not_created(  # noqa: E501
        self, remote_app_data
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_usb_volume.is_mounted.return_value = True
            self.mock_check_output.return_value = b"1.2.3.4"
            rf_config_relation = testing.Relation(
                endpoint=RF_CONFIG_RELATION_NAME,
                interface=RF_CONFIG_RELATION_NAME,
                remote_app_data=remote_app_data,
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
                model=testing.Model(name="whatever"),
            )

            state_out = self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            container = state_out.get_container("ue")
            assert container.layers == {}

    def test_given_charm_running_in_simulation_mode_and_can_connect_to_the_container_but_rfsim_address_is_missing_from_the_fiveg_rf_config_relation_data_when_configure_then_pebble_layer_is_not_created(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_usb_volume.is_mounted.return_value = False
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
                config={"simulation-mode": True},
                relations=[rf_config_relation],
                containers=[container],
                model=testing.Model(name="whatever"),
            )

            state_out = self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            container = state_out.get_container("ue")
            assert container.layers == {}
