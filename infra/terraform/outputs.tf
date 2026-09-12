output "instance_public_ip" {
  description = "SSH here, and reach Grafana at http://<this>:3000 (from admin_ip only)."
  value       = oci_core_instance.quantpipe.public_ip
}

output "object_storage_namespace" {
  value = data.oci_objectstorage_namespace.ns.namespace
}

output "object_storage_bucket_name" {
  value = oci_objectstorage_bucket.quantpipe.name
}
