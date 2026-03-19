# Changelog

## [1.0.1] - 2026-03-19

### Changed
- README: Added full Recommended Proxmox Setup guide covering dedicated `homeassistant-ssh` user, scoped sudoers config, wrapper scripts, and step-by-step integration configuration
- README: Updated example scripts and security notice to reflect least-privilege approach
- README: Added troubleshooting entry for permission denied errors

## [1.0.0] - 2026-03-19

### Added
- Initial release
- SSH password authentication (PAM users)
- Config flow: host, port, username, password with connection test
- Options flow with menu: add script, remove script, save and close
- Button platform: one button entity per configured script
- Multiline bash script editor in the UI
- stdout/stderr logged to the Home Assistant log at appropriate levels
- Non-zero exit codes logged at ERROR level
- All buttons grouped under a single Proxmox VE device per host
- Support for multiple Proxmox hosts via multiple config entries
- English and Danish translations
- HACS compatible (`hacs.json`, `info.md`)
