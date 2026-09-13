module "network" {
  source = "./modules/network"

  compartment_ocid = var.compartment_ocid
  admin_ips        = var.admin_ips
}

module "compute" {
  source = "./modules/compute"

  compartment_ocid        = var.compartment_ocid
  tenancy_ocid            = var.tenancy_ocid
  subnet_id               = module.network.subnet_id
  ssh_public_key_path     = var.ssh_public_key_path
  image_ocid              = var.image_ocid
  instance_ocpus          = var.instance_ocpus
  instance_memory_in_gbs  = var.instance_memory_in_gbs
  boot_volume_size_in_gbs = var.boot_volume_size_in_gbs
  repo_url                = var.repo_url
}

module "storage" {
  source = "./modules/storage"

  compartment_ocid        = var.compartment_ocid
  tenancy_ocid            = var.tenancy_ocid
  availability_domain     = module.compute.availability_domain
  instance_id             = module.compute.instance_id
  data_volume_size_in_gbs = var.data_volume_size_in_gbs
}
