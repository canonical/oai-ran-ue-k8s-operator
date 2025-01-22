# OAI RAN UE (User Equipment) Operator (k8s)
[![CharmHub Badge](https://charmhub.io/oai-ran-ue-k8s/badge.svg)](https://charmhub.io/oai-ran-ue-k8s)

A Charmed Operator for the OAI RAN User Equipment (UE) for K8s.

## Pre-requisites

A Kubernetes cluster with the Multus addon enabled.

## Usage

Enable the Multus addon on MicroK8s.

```bash
sudo microk8s addons repo add community https://github.com/canonical/microk8s-community-addons --reference feat/strict-fix-multus
sudo microk8s enable multus
```

Deploy the charm.

```bash
juju deploy oai-ran-cu-k8s --trust --channel=2.2/edge 
juju deploy oai-ran-du-k8s --trust --channel=2.2/edge --config simulation-mode=true
juju deploy oai-ran-ue-k8s --trust --channel=2.2/edge
juju integrate oai-ran-du-k8s:fiveg_f1 oai-ran-cu-k8s:fiveg_f1
juju integrate oai-ran-du-k8s:fiveg_rfsim oai-ran-ue-k8s:fiveg_rfsim
```

## Image

- **oai-ran-ue**: `ghcr.io/canonical/oai-ran-ue:2.2.0`
