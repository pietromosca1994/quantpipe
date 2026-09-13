variable "tenancy_ocid" {
  description = "OCID of your OCI tenancy."
  type        = string
}

variable "user_ocid" {
  description = "OCID of the OCI user Terraform authenticates as."
  type        = string
}

variable "fingerprint" {
  description = "Fingerprint of the API signing key uploaded to that user."
  type        = string
}

variable "private_key_path" {
  description = "Path to the API signing key's private key file."
  type        = string
}

variable "region" {
  description = "OCI region, e.g. us-ashburn-1."
  type        = string
}

variable "compartment_ocid" {
  description = "OCID of the compartment to create resources in."
  type        = string
}

variable "admin_ips" {
  description = "Your public IP(s) in CIDR form (e.g. [\"203.0.113.4/32\"]), allowed to reach SSH and Grafana. Add an entry per network you connect from (home, travel, etc.) — never include 0.0.0.0/0."
  type        = list(string)
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
      oci compute image list --compartment-id <tenancy_ocid> \
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

variable "data_volume_size_in_gbs" {
  description = "Size of the Block Volume backing Docker's data root (all persistent container volumes, including TimescaleDB)."
  type        = number
  default     = 150
}

variable "repo_url" {
  description = "Git URL the instance clones/pulls on boot."
  type        = string
}
