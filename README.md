# Shelly TRV 2.2.4 Beacon Skip Recovery Fix

Reverse engineering and experimental firmware patch for the **Shelly TRV (SHTRV-01)**.

The goal of this project is to investigate a reproducible Wi-Fi / power-save issue observed with firmware **2.2.4**, where the following message repeatedly appears:

```text
Beacon skip error! Attempt recovery
```

This is typically followed by:

```text
Enter powersave state 1
```

and a few seconds later:

```text
Enter powersave state 3 (skip N)
```

The behavior has been reproduced on multiple SHTRV-01 devices running firmware 2.2.4.

> **Project status:** An experimental one-byte patch has been successfully installed and booted on a test device. Initial runtime testing indicates that normal beacon-skip operation continues while the recurring recovery cycle is no longer observed. Long-term stability and battery-consumption testing are still in progress.

---

## Legal and Distribution Notice

This project is an independent technical investigation of the Shelly TRV (SHTRV-01).

It is **not affiliated with, endorsed by, sponsored by, or supported by Shelly or its manufacturer**.

Shelly, SHTRV-01, and any other referenced product or company names may be trademarks of their respective owners. They are used solely for product identification and technical documentation.

### Firmware

This repository is not intended to distribute:

- original Shelly firmware
- modified Shelly firmware
- extracted Shelly firmware images
- substantial binary portions of Shelly firmware

Any original firmware required for analysis or use of the tools in this repository must be obtained independently by the user from a source from which the user is legally entitled to obtain and use it.

The experimental modification documented by this project is represented by independently written source code, patching tools, technical analysis, offsets, hashes, and documentation.

Where a patching tool is provided, it is intended to modify a compatible firmware image supplied separately and locally by the user.

The resulting modified firmware should remain on the user's own system and is not intended to be redistributed through this repository.

Any license applied to this project applies only to original source code and documentation for which the project authors hold the necessary rights.

It does **not** grant rights to Shelly firmware, trademarks, or other third-party intellectual property.

### No Firmware Redistribution

Please do not submit original or modified Shelly firmware images to this repository.

Issues, test results, logs, independently written source code, hashes, offsets, patching tools, and technical analysis may be submitted only where the contributor has the necessary rights to provide them.

The intended distribution model is:

1. The user obtains the supported original firmware independently.
2. A locally executed patching tool verifies that the input exactly matches the supported firmware version.
3. The patching tool applies the documented modification locally.
4. The modified GBL is generated on the user's computer.
5. The resulting modified firmware remains on the user's system and is not distributed by this repository.

### Experimental Status and Risk

The firmware modification described by this project is experimental.

It bypasses a specific beacon-recovery path identified during analysis of firmware 2.2.4.

It has not yet been established that this recovery path is the underlying cause of increased battery consumption, and long-term stability has not yet been established.

Firmware modification or installation can potentially result in:

- loss of configuration
- loss of network connectivity
- unexpected device behavior
- incorrect thermostat operation
- unexpected valve operation
- increased battery consumption
- failure to boot
- failed firmware updates
- incompatibility with future updates
- permanent loss of device functionality

Users perform firmware modification and installation at their own risk.

Users are responsible for ensuring that their acquisition and use of firmware, modification tools, and resulting firmware images comply with applicable laws, contractual terms, warranty conditions, and device-safety requirements.

No warranty is provided that the tools or documented modifications are suitable for any particular device or purpose.

### Warranty and Manufacturer Support

Installing modified firmware may affect manufacturer warranty, support, update compatibility, or future operation of the device.

This project provides no manufacturer support and cannot guarantee compatibility with future firmware versions, hardware revisions, bootloaders, or devices other than the exact versions that have been investigated and tested.

### Legal Notice

This section describes the intended scope and distribution model of the project and is not legal advice.

Applicable rights and restrictions may depend on jurisdiction, how the original firmware was obtained, contractual terms, and how the tools or resulting firmware are used or distributed.

---

## 1. Initial Problem

With firmware:

```text
20240619-130912/v2.2.4@ee290818
```

the following pattern repeatedly occurs on the normal Wi-Fi network:

```text
minutes_tick: Beacon skip error! Attempt recovery
set_powersave_state: Enter powersave state 1

...

set_powersave_state: Enter powersave state 3 (skip 20)
```

The sequence can occur approximately once per minute.

The same recovery behavior was reproduced on another SHTRV-01 running firmware 2.2.4.

With a weaker RSSI, that device used:

```text
Enter powersave state 3 (skip 15)
```

This confirms that the observed behavior is not limited to a single TRV.

---

## 2. Wi-Fi Tests

Several network configurations were tested to narrow down the cause.

### Main Wi-Fi Network

The recovery error was reproducible on the main Wi-Fi network.

It occurred even with a good RSSI of approximately:

```text
-56 to -62 dBm
```

Therefore, poor signal strength alone does not explain the behavior.

### Guest Wi-Fi Network

When the same TRV was connected to the guest Wi-Fi network, the recovery error did not occur during the observed test period.

The main and guest networks were transmitted by the same physical access points and on the same radio channels, but used different BSSIDs and network configurations.

This indicates that RF signal quality alone is unlikely to be the determining factor.

### CoIoT

CoIoT was disabled while the TRV remained connected to the main Wi-Fi network.

The recovery error continued to occur.

Therefore, CoIoT and the Home Assistant CoIoT peer were ruled out as direct causes.

### FRITZ!Box Mesh Steering

Automatic steering between frequency bands and FRITZ!Box Mesh access points was temporarily disabled.

The recovery error continued to occur.

Mesh/band steering therefore does not sufficiently explain the behavior.

---

## 3. Firmware Comparison

### Firmware 2.2.4

Firmware 2.2.4 reproducibly exhibits the recovery behavior.

The firmware explicitly contains the string:

```text
Beacon skip error! Attempt recovery
```

### Firmware 2.1.0

An affected TRV was downgraded to firmware 2.1.0.

On the same main Wi-Fi network and during an extended observation period, the recurring recovery error was not observed.

This provides strong evidence that the behavior is firmware-dependent.

### Firmware 2.1.8

Another TRV running firmware 2.1.8 did not exhibit the same recurring recovery cycle during the extended test period.

Messages such as:

```text
signal strength: -65, current beacon skip is 20
```

must not be confused with the recovery error.

They only report the currently selected beacon-skip value.

### Firmware 2.1.3

Firmware 2.1.3 was additionally analyzed statically.

The string:

```text
Beacon skip error! Attempt recovery
```

was not found.

However, the basic RSSI-dependent beacon-skip selection logic is already present in firmware 2.1.3.

---

## 4. Beacon-Skip Logic

The RSSI-dependent selection of the desired beacon-skip value was identified in both firmware 2.1.3 and 2.2.4.

The logic is:

```text
RSSI >= -69 dBm      -> Beacon Skip 20
RSSI -79..-70 dBm    -> Beacon Skip 15
RSSI < -79 dBm       -> Beacon Skip 10
```

The basic RSSI-to-beacon-skip algorithm is therefore essentially unchanged between firmware 2.1.3 and 2.2.4.

This suggests that the observed regression is not caused simply by the selection of the desired beacon-skip value.

---

## 5. Power-Save State Handler

The following function in firmware 2.2.4 was identified as the relevant power-save state handler:

```text
FUN_0001f100()
```

State 3 passes the current beacon-skip value to the lower-level Wi-Fi stack.

The relevant call chain was traced as:

```text
FUN_0001d694
  -> FUN_0001f100
  -> FUN_00001b8c
  -> FUN_00001e90
  -> FUN_00001f90
  -> FUN_00057d6c
  -> FUN_00000b8
  -> FUN_000009c4
  -> FUN_00058b64
  -> FUN_00058750
```

`FUN_00058b64` prepares parameters for the lower-level Wi-Fi stack.

For the analyzed path:

```text
param_1 == 2
```

The function also maintains a wrapping counter from `0..31` and constructs:

```text
(counter << 7) | 0x08
```

before passing the value to:

```text
FUN_00058750()
```

The exact low-level cause of the beacon problem has not yet been determined.

---

## 6. Firmware 2.1.3 vs. 2.2.4

Analysis of firmware 2.1.3 revealed RSSI/beacon-skip logic very similar to firmware 2.2.4.

However, no equivalent recurring recovery routine was found in firmware 2.1.3.

In firmware 2.2.4, the relevant additional recovery path is located in:

```text
FUN_0001d918()
```

Under certain conditions this function logs:

```text
Beacon skip error! Attempt recovery
```

and subsequently calls:

```text
FUN_0001f100(1)
```

This switches the device into power-save state 1.

The firmware later returns to power-save state 3.

---

## 7. Recovery Condition in Firmware 2.2.4

The relevant code is located around:

```text
0x0001E1B6
```

The critical branch is:

```asm
0001e1b6  ldr      r3,[DAT_0001e23c]
0001e1b8  ldrsb.w  r3,[r3,#0]
0001e1bc  cmp      r3,#0
0001e1be  beq      LAB_0001e22e

0001e1c0  ldr      r3,[DAT_0001e23c]
0001e1c2  ldrsb.w  r3,[r3,#0]
0001e1c6  cmp      r3,#2
0001e1c8  bgt      LAB_0001e22e
```

The resulting condition is:

```text
value == 0    -> skip recovery
value 1 or 2  -> execute recovery
value > 2     -> skip recovery
```

The exact semantic meaning of the value referenced through `DAT_0001e23c` has not yet been conclusively established.

It should therefore not currently be assigned a definitive name such as `real_beacon_skip`.

---

## 8. Experimental Patch

The purpose of the first experimental patch is **not** to modify the unknown low-level cause.

Instead, it prevents the additional recovery block from executing.

Original instruction:

```asm
0x0001E1C8:

31 DC    bgt LAB_0001e22e
```

Patched instruction:

```asm
0x0001E1C8:

31 E0    b LAB_0001e22e
```

The patched instruction always branches directly to the existing common continuation:

```text
LAB_0001e22e
```

This bypasses the recovery block containing:

```text
Beacon skip error! Attempt recovery
```

and the transition to:

```text
Power-Save State 1
```

The existing common continuation code remains intact.

---

## 9. Binary Patch Verification

The original program image:

```text
program_1_0x00000000.bin
```

has a size of:

```text
1,049,548 bytes
```

The patched program image has exactly the same size.

A complete byte-by-byte comparison showed exactly one changed byte:

```text
Offset 0x0001E1C9:

DC -> E0
```

No other modifications were introduced by the Ghidra export.

---

## 10. GBL Structure

The analyzed original firmware image:

```text
SHTRV-01_build.gbl
```

has a size of:

```text
1,106,384 bytes
```

The parsed tag structure is:

```text
01: Offset 0x000000 | Tag 0x03A617EB | Length 8
02: Offset 0x000010 | Tag 0xF40A0AF4 | Length 28
03: Offset 0x000034 | Tag 0xF50909F5 | Length 25,868
04: Offset 0x006548 | Tag 0xFD0303FD | Length 1,049,552
05: Offset 0x106920 | Tag 0xFD0303FD | Length 30,876
06: Offset 0x10E1C4 | Tag 0xFC0404FC | Length 4
```

The two `0xFD0303FD` tags contain program data.

### Program Block 1

```text
Flash address: 0x00000000
Program data:  1,049,548 bytes
```

### Program Block 2

```text
Flash address: 0x00130A98
Program data:  30,872 bytes
```

The firmware patch affects only Program Block 1.

---

## 11. Binary-to-GBL Mapping

The actual program data of the first program tag starts at GBL offset:

```text
0x00006554
```

The modified byte in the extracted binary is located at:

```text
0x0001E1C9
```

Therefore, its corresponding location in the GBL container is:

```text
0x00006554 + 0x0001E1C9
= 0x0002471D
```

This mapping was verified directly:

```text
Original GBL:
0x0002471D = DC

Patched program image:
0x0001E1C9 = E0
```

---

## 12. GBL CRC32

The final GBL tag is:

```text
Tag:    0xFC0404FC
Length: 4 bytes
```

The original CRC32 is:

```text
0xDC7BAB58
```

The CRC calculation was independently verified against the unmodified original GBL.

The calculation is:

```python
zlib.crc32(gbl[:-4])
```

CRC32 is therefore calculated over the complete GBL including the end-tag header, but excluding the final four CRC bytes.

The patched GBL produces:

```text
0x432F734F
```

The stored CRC was independently recalculated and verified:

```text
Stored:     0x432F734F
Calculated: 0x432F734F

CRC OK
```

---

## 13. Patched GBL Verification

For local testing, an experimental patched GBL was generated.

The generated test image had a size of:

```text
1,106,384 bytes
```

SHA-256 of the locally generated experimental test image:

```text
AC7D85C8E9239BEBD3B134C4B93FC838859C613E59F7690650097DA984EA7222
```

A complete comparison between the original and locally generated patched GBL showed exactly five changed bytes:

```text
Firmware:

0x0002471D: DC -> E0

CRC32:

0x0010E1CC: 58 -> 4F
0x0010E1CD: AB -> 73
0x0010E1CE: 7B -> 2F
0x0010E1CF: DC -> 43
```

The complete container modification therefore consists of:

```text
1 byte of firmware code
+
4 bytes of updated CRC32
```

No other differences were found.

> The patched GBL described here was generated locally for testing and is not distributed through this repository.

---

## 14. GBL Header

The original GBL header payload is:

```text
00 00 00 03 00 00 00 00
```

Interpreted as:

```text
Version: 0x03000000
Type:    0x00000000
```

The analyzed container therefore uses the standard GBL format.

No GBL signing or encryption flags were observed in the analyzed container header.

This observation only describes the analyzed GBL container and should not be interpreted as a general statement about all Shelly firmware or device security mechanisms.

---

## 15. Local OTA Investigation

The Shelly TRV OTA mechanism retrieves firmware through an HTTP URL.

During testing, the OTA client was observed sending:

```http
GET /SHTRV-01_build_2.2.4_beacon_patch.gbl HTTP/1.1
Host: Mallow-Design
Accept: */*
User-Agent: Shelly
Range: bytes=0-
```

### Initial HTTP Server

The first diagnostic HTTP server did not implement Range requests correctly.

It responded to:

```http
Range: bytes=0-
```

with:

```http
HTTP/1.1 200 OK
```

During that test the transfer stopped after approximately:

```text
49,152 bytes
```

and the firmware was not installed.

### Range-Supporting OTA Server

The local diagnostic OTA server was then modified to support HTTP byte-range requests.

For the Shelly request:

```http
Range: bytes=0-
```

the server responds with:

```http
HTTP/1.1 206 Partial Content
Content-Range: bytes 0-1106383/1106384
Content-Length: 1106384
Accept-Ranges: bytes
Connection: close
```

The server additionally logs:

- client address
- HTTP request
- request headers
- requested byte range
- firmware size
- number of bytes written
- transfer progress
- interrupted transfers
- transfer duration

Following implementation of Range support, the experimental patched GBL was accepted and the test TRV subsequently booted firmware 2.2.4.

The local OTA server is intended only as a diagnostic and testing tool.

---

## 16. First Hardware Runtime Test

The first controlled installation was performed on one SHTRV-01 test device.

Before installation, the device was running:

```text
20220202-080736/v2.1.3@d255ad74
```

After installation of the locally generated experimental patched GBL, the device booted as:

```text
20240619-130912/v2.2.4@ee290818
```

The updated firmware initialized:

```text
FMAC Driver version    3.7.0
WF200 Firmware version 3.16.1
WF200 initialization successful
```

After an initial Wi-Fi connection retry, the device connected successfully.

The normal RSSI-dependent beacon-skip mechanism remained functional:

```text
signal strength: -65, will change beacon skip
Enter powersave state 3 (skip 20)
```

During subsequent minute cycles the firmware reported:

```text
signal strength: -59, current beacon skip is 20
```

and later:

```text
signal strength: -60, current beacon skip is 20
```

The normal beacon-skip value therefore remained active.

During the initial observation period, the previously recurring message:

```text
Beacon skip error! Attempt recovery
```

was not observed.

Likewise, the previously recurring recovery transition:

```text
Enter powersave state 1
```

was not observed during those minute cycles.

Wi-Fi remained operational and Shelly Cloud connectivity was successfully established.

### Interpretation

This is the first runtime evidence that the experimental branch modification behaves as intended:

```text
Firmware 2.2.4 boots
        |
        v
normal beacon-skip selection operates
        |
        v
power-save state 3 remains functional
        |
        v
additional recovery block is not observed
```

This result does **not** yet establish that:

- the underlying Wi-Fi issue has been corrected
- battery consumption has returned to normal
- the modification is stable over long periods
- every network configuration behaves identically
- there are no delayed side effects

Long-term testing is therefore still required.

---

## 17. Tools

The investigation uses:

- Ghidra
- Python 3
- PowerShell
- Git
- custom GBL inspector
- custom patched-GBL builder
- custom diagnostic OTA HTTP server

### GBL Inspector

```text
scripts/inspect_gbl.py
```

Responsibilities:

- parse and list GBL tags
- identify program-data blocks
- extract flash addresses
- extract program images
- search extracted firmware for relevant strings

### Patched GBL Builder

```text
scripts/build_patched_gbl.py
```

Responsibilities:

- load the original GBL
- locate the program tag for flash address `0x00000000`
- verify the patched binary size
- verify the expected patch byte
- replace the program block
- recalculate CRC32
- write the patched GBL
- calculate its SHA-256 hash

### Diagnostic OTA Server

```text
scripts/ota_server.py
```

Responsibilities:

- serve a local test firmware image
- use HTTP/1.1
- process Shelly HTTP Range requests
- return `206 Partial Content` where appropriate
- provide `Content-Range`
- provide `Content-Length`
- log incoming request headers
- log requested byte ranges
- monitor transfer progress
- detect interrupted transfers
- report transferred byte count

The OTA server does not contain firmware. A firmware image must be supplied separately by the user.

---

## 18. Current Verification Status

### Completed

```text
[OK] Reproduced beacon-recovery behavior on firmware 2.2.4
[OK] Compared behavior with older firmware versions
[OK] Identified RSSI-to-beacon-skip logic
[OK] Identified power-save state handler
[OK] Identified 2.2.4 recovery path
[OK] Verified patch instruction
[OK] Changed exactly one firmware byte
[OK] Parsed GBL structure
[OK] Replaced the correct program block
[OK] Verified CRC32 algorithm against original GBL
[OK] Verified patched GBL CRC32
[OK] Performed complete original-vs-patched GBL comparison
[OK] Checked GBL header type
[OK] Identified HTTP Range request used by OTA client
[OK] Implemented Range-capable diagnostic OTA server
[OK] Performed OTA installation on one test TRV
[OK] Patched firmware booted as firmware 2.2.4
[OK] Wi-Fi connectivity verified
[OK] Shelly Cloud connectivity verified
[OK] Normal beacon-skip 20 behavior verified
[OK] No recurring beacon-recovery cycle observed during initial runtime test
```

### Still Pending

```text
[TODO] Overnight runtime test
[TODO] Extended multi-day runtime test
[TODO] Monitor Wi-Fi stability
[TODO] Monitor for unexpected reboots
[TODO] Monitor thermostat and valve behavior
[TODO] Test different RSSI conditions / beacon-skip values
[TODO] Long-term battery-consumption comparison
[TODO] Test patch on additional SHTRV-01 devices
[TODO] Determine the exact low-level root cause of the original beacon issue
```

---

## 19. Important Limitations

The current patch is an **experimental recovery bypass**.

It does not prove that the actual cause of the beacon-skip problem has been identified or corrected.

In particular, the exact meaning of the value used by the recovery condition has not yet been conclusively established.

The modification changes the control flow so that the additional 2.2.4 recovery block is bypassed while execution continues at the firmware's existing common continuation.

The initial hardware test answers one specific question positively:

> Can firmware 2.2.4 boot and continue normal Wi-Fi, cloud, thermostat, and beacon-skip operation when the identified additional beacon-recovery block is bypassed?

During the initial test period, the answer was **yes**.

This is not sufficient to classify the modification as a stable or final fix.

---

## 20. Next Steps

The current patched test device should remain unchanged during the next observation period.

The next test phase should specifically monitor:

- continuous uptime
- Wi-Fi connectivity
- cloud connectivity
- thermostat operation
- valve motor operation
- power-save state transitions
- beacon-skip behavior
- recurrence of `Beacon skip error! Attempt recovery`
- unexpected transitions to power-save state 1
- unexpected reboots
- battery voltage
- reported battery percentage
- battery consumption over an extended period

If the device remains stable, testing should subsequently be repeated on additional SHTRV-01 devices.

Before any broader public use is considered, the project should provide a standalone local patching tool that:

1. accepts an original firmware image supplied by the user
2. verifies the exact supported original firmware using a cryptographic hash
3. verifies the expected firmware structure and patch location
4. refuses unknown or modified input images
5. applies only the documented modification
6. recalculates the required GBL CRC32
7. independently verifies the generated output
8. stores the resulting patched firmware only on the user's local system

The repository should continue to distribute only independently created source code, documentation, analysis, and tooling — **not original or modified Shelly firmware images**.
