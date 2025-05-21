#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import json
from pathlib import Path

import pytest
import requests
import yaml
from pytest_operator.plugin import OpsTest

from src.charm import RF_CONFIG_RELATION_NAME

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
NMS_MOCK_CHARM_PATH = "./tests/integration/nms_mock_charm.py"
APP_NAME = METADATA["name"]
AMF_CHARM_NAME = "sdcore-amf-k8s"
AMF_CHARM_CHANNEL = "1.6/edge"
DB_CHARM_NAME = "mongodb-k8s"
DB_CHARM_CHANNEL = "6/stable"
GRAFANA_AGENT_CHARM_NAME = "grafana-agent-k8s"
NRF_CHARM_NAME = "sdcore-nrf-k8s"
NRF_CHARM_CHANNEL = "1.6/edge"
CU_CHARM_NAME = "oai-ran-cu-k8s"
CU_CHARM_CHANNEL = "2.2/edge"
DU_CHARM_NAME = "oai-ran-du-k8s"
DU_CHARM_CHANNEL = "2.2/edge"
NMS_MOCK = "nms-mock"
TLS_CHARM_NAME = "self-signed-certificates"
TLS_CHARM_CHANNEL = "latest/stable"
TIMEOUT = 5 * 60


@pytest.mark.abort_on_fail
async def test_deploy_charm_and_wait_for_active_status(
    ops_test: OpsTest,
    deploy_charm_under_test,
):
    assert ops_test.model
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        status="active",
        timeout=TIMEOUT,
    )


@pytest.mark.abort_on_fail
async def test_relate_and_wait_for_active_status(
    ops_test: OpsTest, deploy_charm_under_test, deploy_dependencies
):
    assert ops_test.model
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:{RF_CONFIG_RELATION_NAME}", relation2=DU_CHARM_NAME
    )
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:logging", relation2=GRAFANA_AGENT_CHARM_NAME
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        raise_on_error=False,
        status="active",
        timeout=TIMEOUT,
    )


@pytest.mark.abort_on_fail
async def test_remove_du_and_wait_for_active_status(
    ops_test: OpsTest, deploy_charm_under_test, deploy_dependencies
):
    assert ops_test.model
    await ops_test.model.remove_application(DU_CHARM_NAME, block_until_done=True)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active", timeout=TIMEOUT)


@pytest.mark.abort_on_fail
async def test_restore_du_and_wait_for_active_status(
    ops_test: OpsTest, deploy_charm_under_test, deploy_dependencies
):
    assert ops_test.model
    await _deploy_du(ops_test)
    await ops_test.model.integrate(relation1=APP_NAME, relation2=DU_CHARM_NAME)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active", timeout=TIMEOUT)


@pytest.fixture(scope="module")
@pytest.mark.abort_on_fail
async def deploy_charm_under_test(ops_test: OpsTest, request):
    """Deploy oai-ran-du-k8s operator."""
    assert ops_test.model
    charm = Path(request.config.getoption("--charm_path")).resolve()
    resources = {
        "ue-image": METADATA["resources"]["ue-image"]["upstream-source"],
    }
    await ops_test.model.set_config({"update-status-hook-interval": "1m"})
    await ops_test.model.deploy(
        charm,
        resources=resources,
        application_name=APP_NAME,
        trust=True,
    )


@pytest.fixture(scope="module")
@pytest.mark.abort_on_fail
async def deploy_dependencies(ops_test: OpsTest):
    """Deploy oai-ran-ue-k8s dependencies."""
    assert ops_test.model
    await _deploy_mongodb(ops_test)
    await _deploy_tls_provider(ops_test)
    await _deploy_nms_mock(ops_test)
    await _deploy_nrf(ops_test)
    await _deploy_amf(ops_test)
    await _deploy_grafana_agent(ops_test)
    await _deploy_cu(ops_test)
    await _deploy_du(ops_test)


async def _deploy_amf(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        AMF_CHARM_NAME,
        application_name=AMF_CHARM_NAME,
        channel=AMF_CHARM_CHANNEL,
        trust=True,
    )
    await ops_test.model.integrate(relation1=AMF_CHARM_NAME, relation2=NRF_CHARM_NAME)
    await ops_test.model.integrate(relation1=f"{AMF_CHARM_NAME}:sdcore_config", relation2=NMS_MOCK)
    await ops_test.model.integrate(relation1=AMF_CHARM_NAME, relation2=TLS_CHARM_NAME)


async def _deploy_grafana_agent(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        GRAFANA_AGENT_CHARM_NAME,
        application_name=GRAFANA_AGENT_CHARM_NAME,
        channel="stable",
    )


async def _deploy_mongodb(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        DB_CHARM_NAME,
        application_name=DB_CHARM_NAME,
        channel=DB_CHARM_CHANNEL,
        trust=True,
    )


async def _deploy_tls_provider(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        TLS_CHARM_NAME,
        application_name=TLS_CHARM_NAME,
        channel=TLS_CHARM_CHANNEL,
    )


async def _deploy_nrf(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        NRF_CHARM_NAME,
        application_name=NRF_CHARM_NAME,
        channel=NRF_CHARM_CHANNEL,
        trust=True,
    )
    await ops_test.model.integrate(relation1=NRF_CHARM_NAME, relation2=DB_CHARM_NAME)
    await ops_test.model.integrate(relation1=NRF_CHARM_NAME, relation2=TLS_CHARM_NAME)
    await ops_test.model.integrate(relation1=f"{NRF_CHARM_NAME}:sdcore_config", relation2=NMS_MOCK)


async def _deploy_nms_mock(ops_test: OpsTest):
    fiveg_core_gnb_lib_url = "https://github.com/canonical/sdcore-nms-k8s-operator/raw/main/lib/charms/sdcore_nms_k8s/v0/fiveg_core_gnb.py"
    fiveg_core_gnb_lib = requests.get(fiveg_core_gnb_lib_url, timeout=10).text
    sdcore_config_lib_url = "https://github.com/canonical/sdcore-nms-k8s-operator/raw/main/lib/charms/sdcore_nms_k8s/v0/sdcore_config.py"
    sdcore_config_lib = requests.get(sdcore_config_lib_url, timeout=10).text
    any_charm_src_overwrite = {
        "fiveg_core_gnb.py": fiveg_core_gnb_lib,
        "sdcore_config.py": sdcore_config_lib,
        "any_charm.py": Path(NMS_MOCK_CHARM_PATH).read_text(),
    }
    assert ops_test.model
    await ops_test.model.deploy(
        "any-charm",
        application_name=NMS_MOCK,
        channel="beta",
        config={
            "src-overwrite": json.dumps(any_charm_src_overwrite),
            "python-packages": "ops==2.17.1\npytest-interface-tester",
        },
    )


async def _deploy_cu(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        CU_CHARM_NAME,
        application_name=CU_CHARM_NAME,
        channel=CU_CHARM_CHANNEL,
        trust=True,
    )
    await ops_test.model.integrate(relation1=CU_CHARM_NAME, relation2=AMF_CHARM_NAME)
    await ops_test.model.integrate(relation1=f"{CU_CHARM_NAME}:fiveg_core_gnb", relation2=NMS_MOCK)


async def _deploy_du(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        DU_CHARM_NAME,
        application_name=DU_CHARM_NAME,
        channel=DU_CHARM_CHANNEL,
        config={
            "bandwidth": 40,
            "frequency-band": 77,
            "sub-carrier-spacing": 30,
            "center-frequency": "4060",
        },
        trust=True,
    )
    await ops_test.model.integrate(relation1=DU_CHARM_NAME, relation2=CU_CHARM_NAME)
