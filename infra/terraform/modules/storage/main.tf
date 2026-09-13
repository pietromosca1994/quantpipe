# Backs Docker's data root (see cloud-init/bootstrap.sh.tftpl) so every named
# volume — TimescaleDB, Prefect, MLflow, Grafana, Prometheus — survives
# instance recreation, not just the database's.
resource "oci_core_volume" "quantpipe_data" {
  compartment_id      = var.compartment_ocid
  availability_domain = var.availability_domain
  display_name        = "quantpipe-data-volume"
  size_in_gbs         = var.data_volume_size_in_gbs
}

resource "oci_core_volume_attachment" "quantpipe_data" {
  attachment_type = "iscsi"
  instance_id     = var.instance_id
  volume_id       = oci_core_volume.quantpipe_data.id
}

data "oci_objectstorage_namespace" "ns" {
  compartment_id = var.tenancy_ocid
}

# MLflow's artifact store in production (see mlflow's command in
# docker-compose.yml, which defaults to local filesystem for dev instead).
resource "oci_objectstorage_bucket" "quantpipe" {
  compartment_id = var.compartment_ocid
  namespace      = data.oci_objectstorage_namespace.ns.namespace
  name           = "quantpipe-artifacts"
  access_type    = "NoPublicAccess"
}
