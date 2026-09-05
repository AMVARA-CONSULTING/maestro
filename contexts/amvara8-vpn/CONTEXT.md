# amvara8-vpn

## What

VPN stack on **amvara8**: **OpenVPN server** (primary long-running service) and **WireGuard** (`wg0`). Separate catalog entry from host **`amvara8-ops`**.

## Paths (on amvara8)

| What | Where |
|------|--------|
| OpenVPN (catalog path) | `/etc/openvpn` |
| OpenVPN server conf | `/etc/openvpn/server/` (`server.conf` symlink) |
| Easy-RSA / clients | `easy-rsa/`, `client/`, `ccd/` |
| WireGuard | `/etc/wireguard` (`wg0.conf`, keys — never Discord) |
| Status helper | `/root/openvpn-status.sh` |
| Client/gen helpers | `/home/amvara/projects/scripts/` (`generate_openvpn_client.sh`, `vpn/`, …) |

## Services / interfaces (typical)

| Stack | Unit | Interface |
|-------|------|-----------|
| OpenVPN | `openvpn-server@server` | `tun0` (e.g. `10.8.0.1/24`) |
| WireGuard | `wg-quick@wg0` | `wg0` (e.g. `10.66.66.1/24`) |

Note: a legacy/unit `openvpn@server` may show flapping (`activating auto-restart`); prefer **`openvpn-server@server`** as the live server unless Luipy says otherwise.

## How to reach from Maestro (lu-zero)

```bash
ssh amvara8 'systemctl status openvpn-server@server wg-quick@wg0 --no-pager; ip -br a show tun0 wg0'
```

Do **not** dump private keys, client certs, or full `wg0.conf` / CCD material into Discord.

## Source of truth

`/etc/openvpn`, `/etc/wireguard`, systemd units, and VPN scripts under `/home/amvara/projects/scripts` (ops tree).

## Normal behavior

- Prefer read-only status (clients, interfaces, unit health) unless asked to change config or issue certs.
- Mutating VPN/firewall is high-impact: confirm with Luipy before edits/restarts.
- Never post secrets, keys, or `.conf` private material to Discord.
- Disk/journal housekeeping → **`amvara8-ops`**.
