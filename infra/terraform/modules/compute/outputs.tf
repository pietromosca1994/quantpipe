output "instance_id" {
  description = "OCID of the compute instance, used by the storage module to attach the Block Volume."
  value       = oci_core_instance.quantpipe.id
}

output "instance_public_ip" {
  description = "SSH here, and reach Grafana at http://<this>:3000 (from one of admin_ips only)."
  value       = oci_core_instance.quantpipe.public_ip
}

output "availability_domain" {
  description = "Availability domain the instance was placed in, used by the storage module so the Block Volume lands in the same AD."
  value       = data.oci_identity_availability_domains.ads.availability_domains[0].name
}
