# infra

Infrastructure-as-code for QuantPipe's Oracle Cloud deployment.
[`terraform/`](terraform/README.md) documents the module layout; this page is
the day-to-day runbook for actually running it.

## Prerequisites

- Terraform >= 1.5.0 (`terraform version`).
- An OCI account with the Always Free resources available in your chosen region.
- OCI CLI configured (`oci setup config`). Not strictly required to run
  Terraform, but `terraform.tfvars`'s auth fields (`tenancy`, `user`,
  `fingerprint`, `key_file`, `region`) are named to match `~/.oci/config`'s
  fields 1:1, so if you've already done this you can copy values straight
  across instead of re-deriving them from the console.
- An SSH keypair — `ssh-keygen -t ed25519` if you don't have one. Its
  `.pub` path goes into `ssh_public_key_path`.

## First-time setup

1. `cd infra/terraform && cp terraform.tfvars.example terraform.tfvars`.
2. Fill in `tenancy` / `user` / `fingerprint` / `key_file` / `region` from
   `~/.oci/config`.
3. Fill in the rest:
   - **`compartment_ocid`** — Console → ☰ → Identity & Security →
     Compartments. (Using `tenancy`'s value here targets the root
     compartment — valid, just less isolated than a dedicated one.)
   - **`image_ocid`** — region-specific; look up the current ARM Ubuntu
     image for your region:
     ```
     oci compute image list --compartment-id <tenancy> \
       --operating-system "Canonical Ubuntu" --shape "VM.Standard.A1.Flex"
     ```
   - **`admin_ips`** — your current public **IPv4** egress, as
     `["x.x.x.x/32"]`. Check it with `curl -4 -s ifconfig.me`; an IPv6
     address won't match anything here, since the VCN doesn't have IPv6
     enabled.
   - `ssh_public_key_path`, `repo_url`.

`terraform.tfvars` is gitignored — it holds real credentials and never gets committed.

## Standard workflow

```
cd infra/terraform
terraform init       # downloads the oracle/oci provider
terraform validate   # config-only checks, no API calls, no credentials needed
terraform plan       # review before applying
terraform apply
```

## Updating allowed SSH/Grafana access

`admin_ips` is a list, not a single IP — most home routers get a dynamic
public IP from the ISP, so it can and does change, and you may also want
access from a second network (travel, a different location) without losing
access from the first.

1. Find the public IP you're connecting from: `curl -4 -s ifconfig.me`.
2. Add or update the corresponding entry in `terraform.tfvars`'s `admin_ips`
   list (`"x.x.x.x/32"`), keeping any other network you still need access from.
3. `terraform apply`. This only updates the security list's ingress rules —
   it doesn't touch the running instance, so there's no downtime for the app.

You do **not** need to already be in an allowed IP to do this — `apply`
talks to OCI's API over the public internet, not to the VM itself. Never add
`0.0.0.0/0` as a shortcut; that removes the only network-level protection
SSH and Grafana have.

## Tearing down

```
terraform destroy
```

Review the plan it prints before confirming — this deletes the VM, its Block
Volume (**data loss**: TimescaleDB and every other Docker volume live there),
the VCN, and the Object Storage bucket (including any MLflow artifacts in it).

## Troubleshooting

### `terraform init` fails with "connection reset" / `wsarecv: An existing connection was forcibly closed by the remote host`

This is Terraform's Go HTTP/2 client getting reset by something on the
network path (a router, antivirus, or VPN client that mishandles HTTP/2) —
not a registry outage. Confirm with `curl` against the same URL (curl
defaults to HTTP/1.1 unless the server negotiates otherwise); if that
succeeds where Terraform fails, force Terraform onto HTTP/1.1 too:

```
GODEBUG=http2client=0 terraform init
```

Prefix `plan`/`apply` the same way if the issue persists there too.

### Locked out of SSH/Grafana after applying

Your `admin_ips` entry is stale — see "Updating allowed SSH/Grafana access" above.

### `terraform plan` fails reading the SSH public key file

`ssh_public_key_path` must point to a file that exists. The variable's
default (`~/.ssh/id_rsa.pub`) is just a placeholder — if you generated a
different key type (e.g. `ed25519`) or keep keys elsewhere, update it to
match.
