# Taskbar-Monitor
KDE Plasma 6 - Command output widget

Tested on :
```
Arch Linux x86_64
Linux 6.14.6-2-cachyos
KDE Plasma 6.3.5 - Wayland
```

## Usage
```
sysinfo_widget.py [-h] [--minimal] [--ratio] [--saved] [--no-cpu] [--no-cpu-temp] [--no-ram] [--no-ram-cache] [--no-zram] [--no-swapfile]

options:
  -h, --help      show this help message and exit
  --minimal       Minimal output without icons or color
  --ratio         Show ZRAM compression ratio if available
  --saved         Show ZRAM saved percentage if available
  --no-cpu        Hide CPU usage
  --no-cpu-temp   Hide CPU temperature
  --no-ram        Hide RAM usage
  --no-ram-cache  Hide RAM cache usage
  --no-zram       Hide ZRAM usage
  --no-swapfile   Hide swapfile usage 
```
