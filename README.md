# Proxmox VE SSH Script

A Home Assistant custom integration that lets you run bash scripts on your Proxmox VE node via SSH. Each script is exposed as a **button entity** in Home Assistant.

---

## Features

- SSH password authentication (PAM users)
- Multiline bash script editor in the UI
- stdout/stderr logged to the Home Assistant log
- Add and remove scripts at any time without reinstalling
- All buttons grouped under a single Proxmox VE device
- Supports multiple Proxmox hosts (add the integration more than once)

---

## Requirements

- Home Assistant 2023.1 or newer
- A Proxmox VE node reachable from your Home Assistant instance over the network
- A PAM user on the Proxmox node with permissions to execute the desired scripts
- HACS installed

---

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant.
2. Go to **Integrations** and click the three-dot menu in the top right.
3. Select **Custom repositories**.
4. Add `https://github.com/macokay/hacs-proxmox-ve-ssh-script` with category **Integration**.
5. Find **Proxmox VE SSH Script** in the HACS store and click **Download**.
6. Restart Home Assistant.

### Manual

1. Download the latest release from [GitHub Releases](https://github.com/macokay/hacs-proxmox-ve-ssh-script/releases).
2. Copy the `proxmox_ve_ssh_script` folder into your `custom_components` directory.
3. Restart Home Assistant.

---

## Setup

1. Go to **Settings > Devices & Services** and click **Add Integration**.
2. Search for **Proxmox VE SSH Script**.
3. Enter your connection details:

| Field | Description |
|---|---|
| Host | IP address or hostname of your Proxmox VE node |
| SSH port | Default: `22` |
| Username | PAM username (e.g. `homeassistant-ssh`) |
| Password | PAM password |

4. The integration will test the SSH connection before saving. If it fails, check the host, port, and credentials.
5. Once connected, open the integration's options to **Add script**.

---

## Adding Scripts

1. Go to **Settings > Devices & Services**.
2. Find **Proxmox VE SSH Script** and click **Configure**.
3. Select **Add script**.
4. Enter a **Script name** (used as the button label) and the **bash script content**.
5. Select **Save and close** from the menu.

The integration reloads automatically and a new button entity appears under the Proxmox VE device.

**Example scripts:**

Restart a container:
```bash
pct restart 100
```

Reboot the node:
```bash
reboot
```

Run a wrapper script already on the host:
```bash
sudo /usr/local/bin/update-proxmox-host.sh
```

---

## Recommended Proxmox Setup

Rather than connecting as `root`, the recommended approach is a dedicated, least-privilege PAM user that can only execute specific, pre-approved scripts via `sudo`. This limits exposure if Home Assistant credentials are ever compromised.

### Step 1 - Create a dedicated SSH user

```bash
adduser --disabled-password --gecos "" homeassistant-ssh
passwd homeassistant-ssh
```

### Step 2 - Restrict sudo to specific scripts only

Create a dedicated sudoers file:

```bash
nano /etc/sudoers.d/homeassistant-ssh
```

List only the scripts this user is allowed to run as root:

```
homeassistant-ssh ALL=(root) NOPASSWD: /usr/local/bin/update-lxc-containers.sh
homeassistant-ssh ALL=(root) NOPASSWD: /usr/local/bin/update-proxmox-host.sh
```

Set correct permissions and validate syntax:

```bash
chmod 440 /etc/sudoers.d/homeassistant-ssh
visudo -c -f /etc/sudoers.d/homeassistant-ssh
```

Verify the result:

```bash
sudo -u homeassistant-ssh sudo -l
```

Expected output:

```
User homeassistant-ssh may run the following commands on zimacube:
    (root) NOPASSWD: /usr/local/bin/update-lxc-containers.sh
    (root) NOPASSWD: /usr/local/bin/update-proxmox-host.sh
```

### Step 3 - Create the wrapper scripts

Scripts must be owned by root and not writable by the SSH user.

**`/usr/local/bin/update-proxmox-host.sh`** - update Proxmox host packages:

```bash
#!/bin/bash
apt-get update && apt-get dist-upgrade -y
```

**`/usr/local/bin/update-lxc-containers.sh`** - update all LXC containers using the community script:

```bash
#!/bin/bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/tools/pve/update-lxcs-cron.sh)"
```

Set ownership and make executable:

```bash
chmod +x /usr/local/bin/update-proxmox-host.sh
chmod +x /usr/local/bin/update-lxc-containers.sh
chown root:root /usr/local/bin/update-*.sh
```

### Step 4 - Configure the integration

In the integration setup, use:

| Field | Value |
|---|---|
| Host | IP or hostname of your Proxmox node |
| Username | `homeassistant-ssh` |
| Password | Password set in Step 1 |

### Step 5 - Add the buttons in Home Assistant

Add two scripts via the integration's options:

| Script name | Script content |
|---|---|
| Update Proxmox Host | `sudo /usr/local/bin/update-proxmox-host.sh` |
| Update LXC Containers | `sudo /usr/local/bin/update-lxc-containers.sh` |

Each becomes a button entity you can press from the dashboard or trigger from an automation.

### Step 6 - Test

From your Proxmox host, verify both scripts run without a password prompt:

```bash
sudo -u homeassistant-ssh sudo /usr/local/bin/update-proxmox-host.sh
sudo -u homeassistant-ssh sudo /usr/local/bin/update-lxc-containers.sh
```

---

## Removing Scripts

1. Open the integration's options.
2. Select **Remove script**.
3. Pick the script from the list and confirm.
4. Select **Save and close**.

---

## Script Output

All output is written to the Home Assistant log:

- `stdout` is logged at **INFO** level.
- `stderr` is logged at **WARNING** level.
- A non-zero exit code is logged at **ERROR** level.
- Successful exit (code 0) is logged at **INFO** level.

To see script output, go to **Settings > System > Logs** or enable `debug` logging:

```yaml
logger:
  default: warning
  logs:
    custom_components.proxmox_ve_ssh_script: debug
```

---

## Security Notice

- Scripts are stored in Home Assistant's config entry storage (encrypted at rest, but readable by anyone with HA admin access).
- Scripts run with the privileges of the SSH user. Using a dedicated user with scoped `sudo` rules (see Recommended Proxmox Setup above) is strongly preferred over connecting as `root`.
- Host key verification is disabled (acceptable for trusted LAN hosts; not recommended over untrusted networks).

---

## Troubleshooting

**Cannot connect:** Verify the host IP is reachable from HA and that SSH is enabled on the Proxmox node (`/etc/ssh/sshd_config`).

**Invalid auth:** Confirm the username is a PAM user (not a PVE realm user like `root@pam` - use just `root` or `homeassistant-ssh`).

**Permission denied running script:** Make sure the sudoers entry exists and the script path matches exactly. Run `sudo -u homeassistant-ssh sudo -l` on the Proxmox host to verify.

**Script times out:** The default timeout is 30 seconds. Long-running scripts should be backgrounded (`nohup my_script.sh &`) or the script itself should handle execution asynchronously.

**Button does not appear after adding a script:** The integration reloads automatically. If the entity is missing, reload the integration manually via **Settings > Devices & Services**.

---

## License
© 2026 Mac O Kay
Free to use and modify for personal, non-commercial use.
Credit appreciated if you share or build upon this work.
Commercial use is not permitted.
