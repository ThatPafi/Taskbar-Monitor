#!/usr/bin/env python3

import psutil
import subprocess
import os
import re
import argparse

def get_cpu_usage():
    return psutil.cpu_percent(interval=0.5)

def get_cpu_temp():
    try:
        output = subprocess.check_output(['sensors']).decode()
        matches = re.findall(r'(Tctl|Tdie|Package id \d+|Core \d+|temp\d+):\s+\+?([\d.]+)°C', output)
        if matches:
            return float(matches[0][1])
    except Exception:
        pass
    return None

def get_ram_usage():
    vm = psutil.virtual_memory()
    meminfo = {}
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                key, value = line.split(':')
                meminfo[key.strip()] = int(value.strip().split()[0])
        cached = meminfo.get("Cached", 0) + meminfo.get("SReclaimable", 0) - meminfo.get("Shmem", 0)
    except Exception:
        cached = vm.cached // 1024  # fallback if /proc/meminfo fails

    used_mb = (vm.total - vm.available) // (1024**2)
    cached_mb = cached // 1024
    total_mb = vm.total // (1024**2)

    return used_mb, total_mb, cached_mb  # all in MB

def get_zram_usage():
    total_used = 0
    total_orig = 0
    found = False
    for zram in os.listdir('/sys/block/'):
        if not zram.startswith('zram'):
            continue
        found = True
        base = f'/sys/block/{zram}'
        try:
            with open(f'{base}/compr_data_size') as f:
                used = int(f.read())
            with open(f'{base}/orig_data_size') as f:
                orig = int(f.read())
            total_used += used
            total_orig += orig
        except Exception:
            continue
    if found and total_orig > 0:

        return total_used // 1024, total_orig // 1024  # in KB
    try:
        with open('/proc/swaps') as f:
            lines = f.readlines()[1:]
        zram_lines = [l for l in lines if 'zram' in l]
        used_kb = sum(int(l.split()[3]) for l in zram_lines)
        total_kb = sum(int(l.split()[2]) for l in zram_lines)
        if total_kb > 0:
            return used_kb, total_kb
    except Exception:
        pass

    return None

def get_swap_usage():
    try:
        with open('/proc/swaps') as f:
            lines = f.readlines()[1:]  # skip header
        for line in lines:
            parts = line.split()
            if parts[0].endswith('swap') or parts[0] == '/swapfile' or '/swap/' in parts[0]:
                total = int(parts[2])
                used = int(parts[3])
                return used, total  # in KB
    except Exception:
        pass
    return None

def color(val, warn, crit, minimal=False):
    if minimal:
        return str(val)
    if val >= crit:
        return f"\x1b[31m{val}\x1b[0m"
    elif val >= warn:
        return f"\x1b[33m{val}\x1b[0m"
    return f"\x1b[32m{val}\x1b[0m"

def color_ratio(val, minimal=False):
    if minimal:
        return str(val)
    if val < 2:
        return f"\x1b[31m{val}\x1b[0m"
    elif val < 3:
        return f"\x1b[33m{val}\x1b[0m"
    else:
        return f"\x1b[32m{val}\x1b[0m"

def format_gb(kb):
    return round(kb / 1024 / 1024, 1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--minimal', action='store_true', help='Minimal output without icons or color')
    parser.add_argument('--ratio', action='store_true', help='Show ZRAM compression ratio if available')
    parser.add_argument('--saved', action='store_true', help='Show ZRAM saved percentage if available')
    parser.add_argument('--no-cpu', action='store_true', help='Hide CPU usage')
    parser.add_argument('--no-cpu-temp', action='store_true', help='Hide CPU temperature')
    parser.add_argument('--no-ram', action='store_true', help='Hide RAM usage')
    parser.add_argument('--no-ram-cache', action='store_true', help='Hide RAM cache usage')
    parser.add_argument('--no-zram', action='store_true', help='Hide ZRAM usage')
    parser.add_argument('--no-swap', action='store_true', help='Hide swap usage')
    args = parser.parse_args()

    minimal = args.minimal
    show_ratio = args.ratio
    show_saved = args.saved
    hide_cpu = args.no_cpu
    hide_cpu_temp = args.no_cpu_temp
    hide_ram = args.no_ram
    hide_ram_cache = args.no_ram_cache
    hide_zram = args.no_zram
    hide_swap = args.no_swap

    cpu = get_cpu_usage() if not hide_cpu else None
    temp = get_cpu_temp() if not hide_cpu_temp else None
    swap = get_swap_usage() if not hide_swap else None
    if not hide_ram:
        used_ram, total_ram, cached_ram = get_ram_usage()
    else:
        used_ram = total_ram = cached_ram = None

    zram = get_zram_usage() if not hide_zram else None

    icon = lambda label: label if minimal else {
        'cpu': '🧠', 'temp': '🌡', 'ram': '💾', 'zram': '📦'
    }[label]

    output_parts = []

    if cpu is not None:
        output_parts.append(f"{icon('cpu')} {color(cpu, 70, 90, minimal)}%")

    if temp is not None:
        output_parts.append(f"{icon('temp')} {color(int(temp), 70, 85, minimal)}°C")

    if used_ram is not None and total_ram is not None:
        used_gb = round(used_ram / 1024, 1)
        total_gb = round(total_ram / 1024, 1)
        cached_gb = round(cached_ram / 1024, 1)
        ram_str = f"{color(used_gb, total_gb*0.75, total_gb*0.9, minimal)}/{total_gb}GB"
        if not hide_ram_cache:
            ram_str += f" (cache {cached_gb}GB)"
        output_parts.append(f"{icon('ram')} {ram_str}")

    if zram is not None:
        z_used_kb, z_total_kb = zram
        z_used_gb = format_gb(z_used_kb)
        z_total_gb = format_gb(z_total_kb)
        zram_str = f"{z_used_gb}/{z_total_gb}GB"
        if show_ratio and z_used_kb > 0:
            ratio_val = round(z_total_kb / z_used_kb, 1)
            ratio_str = color_ratio(ratio_val, minimal)
            zram_str += f" ({ratio_str}:1)"
        if show_saved and z_used_kb > 0:
            saved = 100 * (1 - (z_used_kb / z_total_kb))
            zram_str += f" Saved {round(saved, 1)}%"
        output_parts.append(f"{icon('zram')} {zram_str}")
    elif not hide_zram:
        output_parts.append(f"{icon('zram')} -")

    if swap is not None:
        used_kb, total_kb = swap
        used_gb = format_gb(used_kb)
        total_gb = format_gb(total_kb)
        swap_str = f"{used_gb}/{total_gb}GB"
        if used_kb > 0:
            swap_str = f"\x1b[31m{swap_str}\x1b[0m" if not minimal else swap_str
        output_parts.append(f"{'💽' if not minimal else 'SWP'} {swap_str}")

    print(" ".join(output_parts))


if __name__ == "__main__":
    main()
