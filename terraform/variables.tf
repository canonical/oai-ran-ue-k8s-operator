# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Name of the application in the Juju model."
  type        = string
  default     = "ue"
}

variable "channel" {
  description = "The channel to use when deploying a charm."
  type        = string
  default     = "2.2/edge"
}

variable "config" {
  description = "Application config. Details about available options can be found at https://charmhub.io/oai-ran-ue-k8s/configuration."
  type        = map(string)
  default     = {}
}

variable "constraints" {
  description = "Juju constraints to apply for this application."
  type        = string
  default     = "arch=amd64"
}

variable "model" {
  type        = string
  description = "Reference to a `juju_model`."
  default     = ""
}

variable "resources" {
  description = "Resources to use with the application. Details about available options can be found at https://charmhub.io/oai-ran-ue-k8s/configure."
  type        = map(string)
  default     = {}
}

variable "revision" {
  description = "Revision number of the charm"
  type        = number
  default     = null
}

variable "units" {
  description = "Number of units to deploy"
  type        = number
  default     = 1

  validation {
    condition     = var.units == 1
    error_message = "Scaling is not supported for this charm."
  }
}
