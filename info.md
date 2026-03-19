# Proxmox VE SSH Script

Run bash scripts on your Proxmox VE node directly from Home Assistant.

Each script you configure becomes a **button entity** — press it from the dashboard, use it in automations, or trigger it from a script.

**Features:**
- SSH password authentication (PAM users)
- Multiline bash script support
- stdout/stderr logged to the HA log
- Add and remove scripts at any time via the integration's options
- Groups all buttons under a single Proxmox VE device

See the [README](https://github.com/macokay/hacs-proxmox-ve-ssh-script) for setup instructions.
