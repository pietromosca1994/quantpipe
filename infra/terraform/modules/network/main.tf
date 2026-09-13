resource "oci_core_vcn" "quantpipe" {
  compartment_id = var.compartment_ocid
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "quantpipe-vcn"
  dns_label      = "quantpipe"
}

resource "oci_core_internet_gateway" "quantpipe" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.quantpipe.id
  display_name   = "quantpipe-igw"
  enabled        = true
}

resource "oci_core_route_table" "quantpipe" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.quantpipe.id
  display_name   = "quantpipe-public-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.quantpipe.id
  }
}

# Everything except SSH and Grafana stays off this list entirely — Postgres,
# Prometheus, MLflow, and the Prefect API are only reachable on the
# Docker-internal network, never the VCN. See CLAUDE.md's network principle.
resource "oci_core_security_list" "quantpipe" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.quantpipe.id
  display_name   = "quantpipe-public-sl"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    description = "SSH, admin IP only"
    source      = var.admin_ip
    protocol    = "6" # TCP
    tcp_options {
      min = 22
      max = 22
    }
  }

  ingress_security_rules {
    description = "Grafana, admin IP only — put an authenticated reverse proxy in front before widening this"
    source      = var.admin_ip
    protocol    = "6"
    tcp_options {
      min = 3000
      max = 3000
    }
  }
}

resource "oci_core_subnet" "quantpipe" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.quantpipe.id
  cidr_block                 = "10.0.0.0/24"
  display_name               = "quantpipe-public-subnet"
  dns_label                  = "public"
  route_table_id             = oci_core_route_table.quantpipe.id
  security_list_ids          = [oci_core_security_list.quantpipe.id]
  prohibit_public_ip_on_vnic = false
}
