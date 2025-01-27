# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.ue.name
}

output "requires" {
  value = {
    "fiveg_rfsim" = "fiveg_rfsim"
    "logging"     = "logging"
  }
}
