#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import patch

import pytest
import scenario

from charm import OaiRanUeK8SOperatorCharm


class UEFixtures:
    patcher_check_output = patch("charm.check_output")

    @pytest.fixture(autouse=True)
    def setUp(self, request):
        self.mock_check_output = UEFixtures.patcher_check_output.start()
        yield
        request.addfinalizer(self.tearDown)

    def tearDown(self) -> None:
        patch.stopall()

    @pytest.fixture(autouse=True)
    def context(self):
        self.ctx = scenario.Context(
            charm_type=OaiRanUeK8SOperatorCharm,
        )
