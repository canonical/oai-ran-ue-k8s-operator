#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from pathlib import Path

import pytest
import yaml
from pytest_operator.plugin import OpsTest

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
APP_NAME = METADATA["name"]
AMF_CHARM_NAME = "sdcore-amf-k8s"
AMF_CHARM_CHANNEL = "1.5/edge"
DB_CHARM_NAME = "mongodb-k8s"
DB_CHARM_CHANNEL = "6/edge"
GRAFANA_AGENT_CHARM_NAME = "grafana-agent-k8s"
NRF_CHARM_NAME = "sdcore-nrf-k8s"
NRF_CHARM_CHANNEL = "1.5/edge"
CU_CHARM_NAME = "oai-ran-cu-k8s"
CU_CHARM_CHANNEL = "2.1/edge"
DU_CHARM_NAME = "oai-ran-du-k8s"
DU_CHARM_CHANNEL = "2.1/edge"
NMS_CHARM_NAME = "sdcore-nms-k8s"
NMS_CHARM_CHANNEL = "1.5/edge"
TLS_CHARM_NAME = "self-signed-certificates"
TLS_CHARM_CHANNEL = "latest/stable"
TIMEOUT = 5 * 60


@pytest.mark.abort_on_fail
async def test_deploy_charm_and_wait_for_active_status(ops_test: OpsTest, deploy_charm_under_test):
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
        relation1=f"{APP_NAME}:logging", relation2=GRAFANA_AGENT_CHARM_NAME
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        raise_on_error=False,
        status="active",
        timeout=TIMEOUT,
    )


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
    await _deploy_webui(ops_test)
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
    await ops_test.model.integrate(relation1=AMF_CHARM_NAME, relation2=NMS_CHARM_NAME)
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
    await ops_test.model.integrate(relation1=NRF_CHARM_NAME, relation2=NMS_CHARM_NAME)


async def _deploy_webui(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        NMS_CHARM_NAME,
        application_name=NMS_CHARM_NAME,
        channel=NMS_CHARM_CHANNEL,
    )
    await ops_test.model.integrate(
        relation1=f"{NMS_CHARM_NAME}:common_database", relation2=f"{DB_CHARM_NAME}"
    )
    await ops_test.model.integrate(
        relation1=f"{NMS_CHARM_NAME}:auth_database", relation2=f"{DB_CHARM_NAME}"
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


async def _deploy_du(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        DU_CHARM_NAME,
        application_name=DU_CHARM_NAME,
        channel=DU_CHARM_CHANNEL,
        trust=True,
    )
    await ops_test.model.integrate(relation1=DU_CHARM_NAME, relation2=CU_CHARM_NAME)
