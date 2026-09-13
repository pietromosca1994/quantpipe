variable "compartment_ocid" {
  description = "OCID of the compartment to create the VCN and its networking resources in."
  type        = string
}

variable "admin_ips" {
  description = "Admin public IPs in CIDR form (e.g. [\"203.0.113.4/32\"]), the only sources allowed to reach SSH and Grafana."
  type        = list(string)
}
