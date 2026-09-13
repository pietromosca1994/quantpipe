variable "compartment_ocid" {
  description = "OCID of the compartment to create the instance in."
  type        = string
}

variable "tenancy_ocid" {
  description = "OCID of the OCI tenancy, used to look up availability domains."
  type        = string
}

variable "subnet_id" {
  description = "OCID of the subnet the instance's VNIC attaches to."
  type        = string
}

variable "ssh_public_key_path" {
  description = "Path to the SSH public key installed on the instance."
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "image_ocid" {
  description = <<-EOT
    OCID of the ARM (Ampere A1) boot image to use — region-specific, so look
    it up yourself, e.g.:
      oci compute image list --compartment-id <your tenancy OCID> \
        --operating-system "Canonical Ubuntu" --shape "VM.Standard.A1.Flex"
  EOT
  type        = string
}

variable "instance_ocpus" {
  description = "OCPUs for the Ampere A1 Flex instance. Always Free tier tops out at 4 total across all A1 instances."
  type        = number
  default     = 4
}

variable "instance_memory_in_gbs" {
  description = "Memory (GB) for the Ampere A1 Flex instance. Always Free tier tops out at 24GB total."
  type        = number
  default     = 24
}

variable "boot_volume_size_in_gbs" {
  description = "Size (GB) of the instance's boot volume."
  type        = number
  default     = 50
}

variable "repo_url" {
  description = "Git URL the instance clones/pulls on boot."
  type        = string
}
