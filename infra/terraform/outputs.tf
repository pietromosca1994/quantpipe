output "instance_public_ip" {
  description = "SSH here, and reach Grafana at http://<this>:3000 (from one of admin_ips only)."
  value       = module.compute.instance_public_ip
}

output "object_storage_namespace" {
  description = "Object Storage namespace for the tenancy, needed to build the S3-compatible endpoint MLflow uses as its artifact store."
  value       = module.storage.object_storage_namespace
}

output "object_storage_bucket_name" {
  description = "Name of the bucket MLflow uses as its artifact store."
  value       = module.storage.object_storage_bucket_name
}
