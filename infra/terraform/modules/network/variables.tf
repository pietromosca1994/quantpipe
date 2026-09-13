variable "compartment_ocid" {
  description = "OCID of the compartment to create the VCN and its networking resources in."
  type        = string
}

variable "admin_ip" {
  description = "Admin's public IP in CIDR form (e.g. 203.0.113.4/32), the only source allowed to reach SSH and Grafana."
  type        = string
}
