# infra/terraform

Provisions the Oracle Cloud resources QuantPipe runs on: a VCN with a single
public subnet, one Ampere A1 Flex instance, a Block Volume, and an Object
Storage bucket. This root module is applied directly for QuantPipe's one
environment — it is not published for external consumption, so there is no
`examples/` directory (see [Terraform's standard module structure][structure]
for that convention; it applies once there's a second consumer to demonstrate
usage for).

[structure]: https://developer.hashicorp.com/terraform/language/modules/develop/structure

## Layout

```
infra/terraform/
├── main.tf                      # wires the three nested modules together
├── variables.tf                 # every input this root module accepts
├── outputs.tf                   # instance public IP, bucket name, etc.
├── providers.tf                 # oci provider config (auth/region)
├── versions.tf                  # required_version + pinned required_providers
├── terraform.tfvars.example     # template — copy to terraform.tfvars, never commit that
└── modules/
    ├── network/                 # VCN, subnet, IGW, route table, security list
    ├── compute/                 # Ampere A1 instance + cloud-init/bootstrap.sh.tftpl
    └── storage/                 # Block Volume + Object Storage bucket
```

Each nested module is internal-use only (no `README.md` of its own, per the
standard structure's convention that only user-facing nested modules carry
one) and is composed here, not applied on its own.

## Usage

See [infra/README.md](../README.md) for the full runbook — first-time
`terraform.tfvars` setup, `init`/`plan`/`apply`, updating allowed SSH/Grafana
access, tearing down, and troubleshooting.
