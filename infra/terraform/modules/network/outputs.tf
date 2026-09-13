output "subnet_id" {
  description = "OCID of the public subnet the compute instance attaches its VNIC to."
  value       = oci_core_subnet.quantpipe.id
}
