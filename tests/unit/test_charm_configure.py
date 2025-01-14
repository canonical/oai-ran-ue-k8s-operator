#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


import os
import tempfile

import pytest
from ops import testing
from ops.pebble import Layer

from tests.unit.fixtures import UEFixtures


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

    def test_given_workload_is_ready_to_be_configured_and_sst_is_available_when_configure_then_ue_config_file_is_generated_and_pushed_to_the_workload_container(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_check_output.return_value = b"1.2.3.4"
            self.mock_k8s_usb_volume.is_mounted.return_value = False
            rfsim_relation = testing.Relation(
                endpoint="fiveg_rfsim",
                interface="fiveg_rfsim",
                remote_app_data={
                    "rfsim_address": "1.1.1.1",
                    "sst": "1",
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
                relations=[rfsim_relation],
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
            rfsim_relation = testing.Relation(
                endpoint="fiveg_rfsim",
                interface="fiveg_rfsim",
                remote_app_data={
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
                relations=[rfsim_relation],
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
            rfsim_relation = testing.Relation(
                endpoint="fiveg_rfsim",
                interface="fiveg_rfsim",
                remote_app_data={
                    "rfsim_address": "1.1.1.1",
                    "sst": "1",
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
                relations=[rfsim_relation],
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

    def test_given_ue_config_file_is_up_to_date_when_rfsim_relation_changed_then_ue_config_file_is_not_pushed_to_the_workload_container(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_usb_volume.is_mounted.return_value = False
            self.mock_check_output.return_value = b"1.2.3.4"
            rfsim_relation = testing.Relation(
                endpoint="fiveg_rfsim",
                interface="fiveg_rfsim",
                remote_app_data={
                    "rfsim_address": "1.1.1.1",
                    "sst": "1",
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
                relations=[rfsim_relation],
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

            self.ctx.run(self.ctx.on.relation_changed(rfsim_relation), state_in)

            assert os.stat(temp_dir + "/ue.conf").st_mtime == config_modification_time

    def test_given_ue_config_is_exist_when_rfsim_relation_changed_then_new_ue_config_file_is_pushed_to_the_workload_container(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_usb_volume.is_mounted.return_value = False
            self.mock_check_output.return_value = b"1.2.3.4"
            rfsim_relation = testing.Relation(
                endpoint="fiveg_rfsim",
                interface="fiveg_rfsim",
                remote_app_data={"rfsim_address": "1.1.1.1", "sst": "2", "sd": "12555"},
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
                relations=[rfsim_relation],
                containers=[container],
                model=testing.Model(name="whatever"),
            )

            with open("tests/unit/resources/expected_config_without_sd.conf") as old_config_file:
                old_config = old_config_file.read().strip()

            with open(f"{temp_dir}/ue.conf", "w") as generated_config_file:
                generated_config_file.write(old_config)

            config_modification_time = os.stat(temp_dir + "/ue.conf").st_mtime

            self.ctx.run(self.ctx.on.relation_changed(rfsim_relation), state_in)

            with open(f"{temp_dir}/ue.conf") as updated_config_file:
                updated_config = updated_config_file.read()

            with open("tests/unit/resources/expected_config_with_sd.conf") as expected_config_file:
                expected_config = expected_config_file.read()

            assert updated_config.strip() == expected_config.strip()

            assert os.stat(temp_dir + "/ue.conf").st_mtime != config_modification_time

    def test_given_can_connect_when_configure_then_pebble_layer_is_created(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_usb_volume.is_mounted.return_value = False
            self.mock_check_output.return_value = b"1.2.3.4"
            rfsim_relation = testing.Relation(
                endpoint="fiveg_rfsim",
                interface="fiveg_rfsim",
                remote_app_data={
                    "rfsim_address": "1.1.1.1",
                    "sst": "1",
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
                relations=[rfsim_relation],
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
                                "command": "/opt/oai-gnb/bin/nr-uesoftmodem -O /tmp/conf/ue.conf --sa --rfsim -r 106 --numerology 1 -C 3924060000 --ssb 530 --band 77 --log_config.global_log_options level,nocolor,time --rfsimulator.serveraddr 1.1.1.1",  # noqa: E501
                                "environment": {"TZ": "UTC"},
                            }
                        }
                    }
                )
            }

    def test_given_can_connect_rfsim_data_not_available_when_configure_then_pebble_layer_is_not_created(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_check_output.return_value = b"1.2.3.4"
            rfsim_relation = testing.Relation(
                endpoint="fiveg_rfsim",
                interface="fiveg_rfsim",
                remote_app_data={},
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
                relations=[rfsim_relation],
                containers=[container],
                model=testing.Model(name="whatever"),
            )

            state_out = self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            container = state_out.get_container("ue")
            assert container.layers == {}
