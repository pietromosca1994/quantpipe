output "object_storage_namespace" {
  description = "Object Storage namespace for the tenancy, needed to build the S3-compatible endpoint MLflow uses as its artifact store."
  value       = data.oci_objectstorage_namespace.ns.namespace
}

output "object_storage_bucket_name" {
  description = "Name of the bucket MLflow uses as its artifact store."
  value       = oci_objectstorage_bucket.quantpipe.name
}
