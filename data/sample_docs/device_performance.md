# Device Performance Troubleshooting Guide

**Source:** IT Support Knowledge Base  
**Document ID:** KB-HW-001  
**Category:** Device and Performance Issues  
**Last reviewed:** 2024-01-15

---

## Overview

This guide helps diagnose and resolve common performance problems on corporate laptops and
desktops, such as slow startup, high CPU usage, and application lag.

---

## Step 1 — Check current resource usage

1. Press **Ctrl + Shift + Esc** to open Task Manager.
2. Click the **Performance** tab to see CPU, memory, disk, and network usage.
3. Click the **Processes** tab, sorted by CPU or Memory, to identify high-usage processes.
4. Note the process names; look for unfamiliar applications.

---

## Step 2 — Check available disk space

1. Open **File Explorer → This PC**.
2. Ensure the system drive (usually C:) has at least **10% free space**.
3. If disk space is below 10%:
   - Empty the Recycle Bin.
   - Delete files in `%TEMP%` (press **Windows + R**, type `%temp%`, press Enter, and
     delete all files you are able to).
   - Uninstall unused applications via **Settings → Apps**.
   - Do not delete system files or files you cannot identify.

---

## Step 3 — Check for Windows updates

1. Open **Settings → Windows Update** and install pending updates.
2. Restart after updates if prompted.
3. Some performance issues, including GPU driver issues, are resolved by updates.

---

## Step 4 — Check startup programs

1. Open Task Manager → **Startup** tab.
2. Review the list of programs that start automatically.
3. Right-click and **Disable** any non-essential startup programs.
4. Do not disable security software, VPN clients, or IT management agents.
5. Restart and test performance.

---

## Step 5 — Run a malware scan

1. Open **Windows Security → Virus & Threat Protection**.
2. Run a **Full scan**.
3. If threats are detected: follow the prompts and contact IT immediately.
4. Do not attempt to remove threats manually from system directories.

---

## Step 6 — Check hardware health

**Thermal throttling (laptop runs hot and slows down):**
1. Ensure the laptop vents are not blocked.
2. Place the laptop on a hard surface, not a bed or cushion.
3. If the fan is unusually loud or hot air is not expelled: schedule hardware maintenance.

**Failing hard drive:**
1. Open **Windows Security → Device Security → Core Isolation** and review Drive Health
   if available, or use the manufacturer's drive diagnostic tool.
2. Back up data immediately if drive errors are detected.
3. Report to IT for drive replacement.

---

## Escalation

Escalate to hardware support if:
- CPU or memory usage is persistently above 90% with no obvious cause after all steps above.
- The device is more than 4 years old and performance has degraded significantly.
- Unusual sounds (clicking, grinding) come from the device.
- The device fails to complete startup consistently.

When escalating, provide: device model and serial number, Windows version, and a screenshot
or description of what Task Manager shows during the slowdown.
