#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import patch

import pytest
from ops import testing

from charm import OaiRanUeK8SOperatorCharm


class UEFixtures:
    patcher_check_output = patch("charm.check_output")
    patcher_k8s_privileged = patch("charm.K8sPrivileged")

    @pytest.fixture(autouse=True)
    def setUp(self, request):
        self.mock_check_output = UEFixtures.patcher_check_output.start()
        self.mock_k8s_privileged = UEFixtures.patcher_k8s_privileged.start().return_value
        yield
        request.addfinalizer(self.tearDown)

    def tearDown(self) -> None:
        patch.stopall()

    @pytest.fixture(autouse=True)
    def context(self):
        self.ctx = testing.Context(
            charm_type=OaiRanUeK8SOperatorCharm,
        )
