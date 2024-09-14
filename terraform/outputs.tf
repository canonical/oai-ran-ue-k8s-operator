# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.ue.name
}

output "fiveg_rfsim_endpoint" {
  description = "Name of the endpoint used to integrate with the rfsim provider."
  value       = "fiveg_rfsim"
}

output "logging_endpoint" {
  description = "Name of the endpoint used to integrate with the Logging provider."
  value       = "logging"
}
