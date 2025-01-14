#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import patch

import pytest
from lightkube.models.apps_v1 import StatefulSetSpec
from lightkube.models.core_v1 import (
    Container,
    HostPathVolumeSource,
    PodSpec,
    PodTemplateSpec,
    SecurityContext,
    Volume,
    VolumeMount,
)
from lightkube.models.meta_v1 import LabelSelector
from lightkube.resources.apps_v1 import StatefulSet

from k8s import K8sUSBVolume

WORKLOAD_CONTAINER_NAME = "whatever"
UNPRIVILEGED_STATEFULSET = StatefulSet(
    spec=StatefulSetSpec(
        selector=LabelSelector(),
        serviceName="whatever",
        template=PodTemplateSpec(
            spec=PodSpec(
                containers=[
                    Container(
                        name=WORKLOAD_CONTAINER_NAME,
                        securityContext=SecurityContext(privileged=False),
                    )
                ],
            )
        ),
    )
)
PRIVILEGED_STATEFULSET = StatefulSet(
    spec=StatefulSetSpec(
        selector=LabelSelector(),
        serviceName="whatever",
        template=PodTemplateSpec(
            spec=PodSpec(
                containers=[
                    Container(
                        name=WORKLOAD_CONTAINER_NAME,
                        securityContext=SecurityContext(privileged=True),
                    )
                ],
            )
        ),
    )
)
USB_MOUNTED_STATEFULSET = StatefulSet(
    spec=StatefulSetSpec(
        selector=LabelSelector(),
        serviceName="whatever",
        template=PodTemplateSpec(
            spec=PodSpec(
                containers=[
                    Container(
                        name=WORKLOAD_CONTAINER_NAME,
                        securityContext=SecurityContext(privileged=True),
                        volumeMounts=[VolumeMount(name="usb", mountPath="/dev/bus/usb")],
                    )
                ],
                volumes=[
                    Volume(
                        name="usb",
                        hostPath=HostPathVolumeSource(path="/dev/bus/usb", type=""),
                    )
                ],
            )
        ),
    )
)
USB_UNMOUNTED_STATEFULSET = StatefulSet(
    spec=StatefulSetSpec(
        selector=LabelSelector(),
        serviceName="whatever",
        template=PodTemplateSpec(
            spec=PodSpec(
                containers=[
                    Container(
                        name=WORKLOAD_CONTAINER_NAME,
                        securityContext=SecurityContext(privileged=True),
                    )
                ],
            )
        ),
    )
)


class TestK8sUSBVolume:
    patcher_lightkube_client = patch("lightkube.core.client.GenericSyncClient")
    patcher_lightkube_client_get = patch("lightkube.core.client.Client.get")
    patcher_lightkube_client_replace = patch("lightkube.core.client.Client.replace")

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_lightkube_client = TestK8sUSBVolume.patcher_lightkube_client.start()
        self.mock_lightkube_client_get = TestK8sUSBVolume.patcher_lightkube_client_get.start()
        self.mock_lightkube_client_replace = (
            TestK8sUSBVolume.patcher_lightkube_client_replace.start()
        )

    def test_given_usb_volume_not_mounted_when_is_mounted_then_return_false(self):
        self.mock_lightkube_client_get.return_value = USB_UNMOUNTED_STATEFULSET

        usb_volume = K8sUSBVolume(
            namespace="my-namespace",
            statefulset_name="my-statefulset-name",
            unit_name="my-unit-name",
            container_name=WORKLOAD_CONTAINER_NAME,
        )

        assert not usb_volume.is_mounted()

    def test_given_usb_volume_mounted_when_is_mounted_then_return_true(self):
        self.mock_lightkube_client_get.return_value = USB_MOUNTED_STATEFULSET

        usb_volume = K8sUSBVolume(
            namespace="my-namespace",
            statefulset_name="my-statefulset-name",
            unit_name="my-unit-name",
            container_name=WORKLOAD_CONTAINER_NAME,
        )

        assert usb_volume.is_mounted()

    def test_given_usb_volume_not_mounted_when_mount_usb_then_usb_is_mounted(self):
        self.mock_lightkube_client_get.return_value = USB_UNMOUNTED_STATEFULSET

        usb_volume = K8sUSBVolume(
            namespace="my-namespace",
            statefulset_name="my-statefulset-name",
            unit_name="my-unit-name",
            container_name=WORKLOAD_CONTAINER_NAME,
        )

        usb_volume.mount()

        self.mock_lightkube_client_replace.assert_called_once_with(
            obj=StatefulSet(
                spec=StatefulSetSpec(
                    selector=LabelSelector(),
                    serviceName="whatever",
                    template=PodTemplateSpec(
                        spec=PodSpec(
                            containers=[
                                Container(
                                    name=WORKLOAD_CONTAINER_NAME,
                                    securityContext=SecurityContext(privileged=True),
                                    volumeMounts=[
                                        VolumeMount(name="usb", mountPath="/dev/bus/usb")
                                    ],
                                )
                            ],
                            volumes=[
                                Volume(
                                    name="usb",
                                    hostPath=HostPathVolumeSource(path="/dev/bus/usb", type=""),
                                )
                            ],
                        )
                    ),
                )
            )
        )
