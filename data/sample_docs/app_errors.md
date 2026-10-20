# Common Application Launch Error Troubleshooting

**Source:** IT Support Knowledge Base  
**Document ID:** KB-APP-001  
**Category:** Software Installation or Configuration  
**Last reviewed:** 2024-01-15

---

## Overview

This guide covers the most common errors that prevent corporate applications from launching
or running correctly. It does not cover installation of unapproved software.

---

## Error: "Application failed to start" or "DLL not found"

**Likely cause:** A required runtime library (such as Microsoft Visual C++ Redistributable
or .NET Framework) is missing or corrupted.

**Steps:**

1. Note the exact error message. If it mentions a specific `.dll` file, search for the
   corresponding runtime on the Microsoft download site.
2. Download and install the required Visual C++ Redistributable or .NET version.
3. Restart the computer.
4. If the error persists: use the **Programs and Features** control panel to repair or
   reinstall the application.

---

## Error: "Access denied" when launching an application

**Likely cause:** User account lacks the required permissions, or an administrator account
is required to run the application.

**Steps:**

1. Check whether right-clicking the application and selecting **Run as administrator**
   resolves the issue.
2. If administrator access resolves the issue: contact IT to review whether the application
   requires a permanent privilege adjustment.
3. Do not use a permanent administrator account for day-to-day work.

---

## Error: Application crashes immediately or freezes

**Likely cause:** Corrupted user profile data, insufficient memory, or a conflicting process.

**Steps:**

1. Close all other applications and try again.
2. Check available RAM: open **Task Manager → Performance → Memory**.
   - If memory usage is above 90%: restart the computer.
3. Clear the application cache:
   - Locate the application's cache folder, typically in `%LOCALAPPDATA%` or
     `%APPDATA%\[ApplicationName]`.
   - Delete or rename the `cache` subfolder.
4. Check the Windows Event Viewer for application error events:
   - **Windows + X → Event Viewer → Windows Logs → Application**.
   - Look for Error or Critical events at the time of the crash.
5. Note the faulting module name from the Event Viewer and include it when contacting IT.

---

## Error: "License not found" or "Activation required"

**Likely cause:** Software license is not assigned to the user account, or the license
server is unreachable.

**Steps:**

1. Confirm you are signed in with your corporate account.
2. Confirm you are connected to the corporate network or VPN.
3. Contact IT to verify the license assignment in the software portal.
4. Do not enter personal license keys in corporate applications.

---

## Error: Application update fails or is stuck

**Steps:**

1. Ensure you are not on a metered or restricted network connection.
2. Check whether a previous version of the application is still running in the background
   (check **Task Manager → Details**).
3. If a background process is running: end it, then retry the update.
4. If the update consistently fails: contact IT to push the update via the software
   management tool.

---

## Escalation

Escalate to the application support team if:
- The error is not covered above.
- The application error recurs after reinstallation.
- Multiple users experience the same error simultaneously.
- A crash dump file is generated (usually in `%LOCALAPPDATA%\CrashDumps`).

When escalating, provide: application name and version, Windows version, exact error text,
and relevant Event Viewer entries.
