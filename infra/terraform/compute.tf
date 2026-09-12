data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

resource "oci_core_instance" "quantpipe" {
  compartment_id      = var.compartment_ocid
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = "quantpipe-vm"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = var.instance_ocpus
    memory_in_gbs = var.instance_memory_in_gbs
  }

  source_details {
    source_type             = "image"
    source_id               = var.image_ocid
    boot_volume_size_in_gbs = var.boot_volume_size_in_gbs
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.quantpipe.id
    assign_public_ip = true
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data = base64encode(templatefile("${path.module}/cloud-init/bootstrap.sh.tftpl", {
      repo_url         = var.repo_url
      data_volume_path = "/dev/oracleoci/oraclevdb"
    }))
  }
}
