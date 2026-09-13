variable "compartment_ocid" {
  description = "OCID of the compartment to create the Block Volume and Object Storage bucket in."
  type        = string
}

variable "tenancy_ocid" {
  description = "OCID of the OCI tenancy, used to look up the Object Storage namespace."
  type        = string
}

variable "availability_domain" {
  description = "Availability domain the Block Volume must be created in, matching the compute instance it attaches to."
  type        = string
}

variable "instance_id" {
  description = "OCID of the compute instance the Block Volume attaches to."
  type        = string
}

variable "data_volume_size_in_gbs" {
  description = "Size of the Block Volume backing Docker's data root (all persistent container volumes, including TimescaleDB)."
  type        = number
  default     = 150
}
