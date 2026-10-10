# Shelly TRV Gen1 Firmware Investigation & Beacon Recovery Patch

Reverse engineering, runtime investigation, and experimental firmware patch for the **Shelly TRV Gen1 (SHTRV-01)**.

The goal of this project is to investigate abnormal battery consumption reported with the Shelly TRV Gen1 and a reproducible Wi-Fi / power-save behavior observed with firmware **2.2.4**, where the following message repeatedly appears:

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

The behavior has been reproduced on multiple physical SHTRV-01 devices running stock firmware 2.2.4.

> **Project status:** The experimental one-byte patch has now been installed and tested on multiple physical SHTRV-01 devices. It suppresses the targeted recurring `Beacon skip error! Attempt recovery` sequence while normal RSSI-dependent beacon-skip selection, Wi-Fi, Shelly Cloud, thermostat calibration, and physical valve movement have continued to operate in the tested devices.
>
> One patched device completed a first uninterrupted run of approximately **39 h 22 min** without an observed recurrence of the targeted recovery sequence. A second patched device installed on a radiator reached approximately **32 h 08 min** while continuing normal thermostat and valve operation.
>
> These results provide increasingly strong evidence that the targeted 2.2.4 recovery path can be bypassed without immediately disrupting normal TRV operation under the tested conditions.
>
> **However, it has not yet been established that the patch reduces the underlying battery drain.**
>
> Historical observations indicate that relatively fast battery consumption was already present on at least one device running firmware **2.1.8**, even though the regularly recurring 2.2.4 recovery loop is not present in the currently analyzed 2.1.8 log. The battery-drain problem and the 2.2.4 recovery loop must therefore currently be treated as related research questions rather than assumed to be the same defect.
>
> A standalone local patcher and Range-capable OTA server are available in the separate [Shelly TRV Gen1 2.2.4 Firmware Patcher](https://github.com/AbleMonster/Shelly-TRV-Gen1-2.2.4-patcher) project. The current experimental release is **v0.1.0**.

---

## Legal and Distribution Notice

This project is an independent technical investigation of the Shelly TRV Gen1 (SHTRV-01).

It is **not affiliated with, endorsed by, sponsored by, or supported by Shelly or its manufacturer**.

Shelly, SHTRV-01, and any other referenced product or company names may be trademarks of their respective owners. They are used solely for product identification and technical documentation.

### Firmware

This repository is not intended to distribute:

- original Shelly firmware
- modified Shelly firmware
- extracted Shelly firmware images
- substantial binary portions of Shelly firmware

Any original firmware required for analysis or use of the tools in this project must be obtained independently by the user from a source from which the user is legally entitled to obtain and use it.

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

It has not yet been established that this recovery path is the underlying cause of increased battery consumption.

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

the following pattern repeatedly occurs on affected devices connected to the normal Wi-Fi network:

```text
minutes_tick: Beacon skip error! Attempt recovery

set_powersave_state: Enter powersave state 1

...

set_powersave_state: Enter powersave state 3 (skip 20)
```

On clearly affected devices, this sequence can occur approximately once per minute.

The same recovery behavior was reproduced on multiple physical SHTRV-01 devices running stock firmware 2.2.4.

With weaker RSSI, one device used:

```text
Enter powersave state 3 (skip 15)
```

The valve motor did not repeatedly move with every recovery event.

The behavior therefore appears primarily related to the Wi-Fi / power-save / beacon-skip subsystem rather than repeated thermostat motor activity.

### Important distinction

The recurring 2.2.4 recovery loop is reproducible and is the specific behavior targeted by the experimental patch.

It must not currently be treated as synonymous with the complete Shelly TRV Gen1 battery-drain problem.

Historical battery behavior and newer measurements indicate that abnormal battery consumption may also exist without the regularly recurring 2.2.4 recovery sequence.

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

When the same TRV was connected to the guest Wi-Fi network, the recovery error did not occur during the observed multi-hour test period.

The main and guest networks were transmitted by the same physical access points and on the same radio channels, but used different BSSIDs and network configurations.

This indicates that RF signal quality alone is unlikely to be the determining factor.

The exact network-side difference responsible for the behavior has not yet been identified.

### CoIoT

CoIoT was disabled while the TRV remained connected to the main Wi-Fi network.

The recovery error continued to occur.

Therefore, CoIoT and the Home Assistant CoIoT peer do not sufficiently explain the behavior.

### FRITZ!Box Mesh Steering

Automatic steering between FRITZ!Box Mesh access points was temporarily disabled.

The recovery error continued to occur.

Mesh steering therefore does not sufficiently explain the behavior.

### AP / BSSID Selection

Additional testing has revealed another potentially relevant variable.

Two different physical SHTRV-01 devices placed in approximately the same location can report substantially different RSSI values and may associate with different access points / BSSIDs.

For example, a device running firmware 2.1.0 was observed at approximately:

```text
-81 to -84 dBm
```

while another device running patched 2.2.4 placed in the same general location reported approximately:

```text
-62 to -65 dBm
```

The 2.1.0 device had been restarted specifically to allow a fresh Wi-Fi association.

This observation is not yet understood.

Possible factors include:

- different BSSID / access-point association
- antenna orientation
- device-to-device RF variation
- firmware-dependent association behavior
- differences in the Wi-Fi stack

No causal conclusion is currently drawn from this observation.

AP/BSSID selection and RSSI behavior are now part of the ongoing investigation.

---

## 3. Firmware Comparison

Several firmware versions are relevant to the investigation.

### Firmware 2.2.4

Firmware 2.2.4 reproducibly exhibits the recurring recovery behavior on multiple physical devices.

The firmware explicitly contains the string:

```text
Beacon skip error! Attempt recovery
```

The additional recovery path has been located and analyzed.

### Firmware 2.1.0

Firmware 2.1.0 does not show the same regularly recurring 2.2.4 recovery cycle in the analyzed runtime logs.

The normal RSSI-dependent beacon-skip mechanism is already present.

At weak signal strength, the device was observed selecting:

```text
signal strength: -83, will change beacon skip
Enter powersave state 3 (skip 10)
```

One documented 2.1.0 runtime point showed:

```text
uptime: 355568 s
battery: 100 %
voltage: 3.886 V
RSSI: approximately -81 dBm
calibrated: true
```

This corresponds to approximately:

```text
98 h 46 min
```

of uptime.

This is useful as a long-runtime reference, but battery percentage and voltage alone do not establish actual battery capacity or consumption rate.

The age and condition of the battery used in this device are not controlled.

### Firmware 2.1.3

Firmware 2.1.3 was analyzed statically.

The string:

```text
Beacon skip error! Attempt recovery
```

was not found.

However, the basic RSSI-dependent beacon-skip selection logic is already present in firmware 2.1.3.

The desired beacon-skip algorithm therefore predates the additional 2.2.4 recovery behavior.

### Firmware 2.1.8

Another physical SHTRV-01 running:

```text
20220811-152343/v2.1.8@5afc928c
```

was examined.

The currently analyzed long log does not show the regularly recurring 2.2.4-style:

```text
Beacon skip error! Attempt recovery
```

cycle.

At weak RSSI around approximately:

```text
-78 to -80 dBm
```

the device continued normal periodic signal-strength checking and RSSI-dependent beacon-skip operation.

A documented measurement before the planned stock-2.2.4 control test showed approximately:

```text
uptime: 13 h 48 min
battery: 100 %
voltage: 4.157 V
RSSI: -79 dBm
cloud: disabled
```

However, this device is particularly important because historical operation indicated relatively fast battery consumption while running firmware 2.1.8.

Therefore:

> The absence of the regularly recurring 2.2.4 recovery loop does not imply that firmware 2.1.8 is free from abnormal battery consumption.

This is a major reason why the battery-drain problem and the later recovery loop are now being investigated separately.

### Current Firmware Timeline Hypothesis

A current working hypothesis is that more than one firmware change may be relevant.

The versions of particular interest are:

```text
2.1.0
  |
2.1.3
  |
2.1.6
  |
2.1.7
  |
2.1.8
  |
2.2.x
```

The investigation now asks two separate questions:

1. At what point did the underlying Wi-Fi / power-save behavior potentially change in a way that could affect battery consumption?
2. At what point was the additional `Beacon skip error! Attempt recovery` mechanism introduced?

These changes may have occurred in different firmware versions.

No version boundary is currently claimed as proven.

---

## 4. Beacon-Skip Logic

The RSSI-dependent selection of the desired beacon-skip value was identified in older firmware and in firmware 2.2.4.

The observed logic is:

```text
RSSI >= -69 dBm      -> Beacon Skip 20
RSSI -79..-70 dBm    -> Beacon Skip 15
RSSI < -79 dBm       -> Beacon Skip 10
```

The basic RSSI-to-beacon-skip algorithm is therefore not unique to firmware 2.2.4.

This suggests that the observed regression is not caused simply by the selection of the desired beacon-skip value.

A higher desired beacon-skip value allows the client to remain asleep across more access-point beacon intervals.

The beacon-skip setting should not be interpreted as a direct transmit-power setting.

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

This additional recovery path is therefore a meaningful firmware difference between the analyzed older implementation and 2.2.4.

It does not, by itself, establish that this difference is responsible for the full battery-drain problem.

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

It should therefore not currently be assigned a definitive name such as:

```text
real_beacon_skip
```

Tracing all reads and writes to this value remains an important reverse-engineering task.

---

## 8. Experimental Patch

The purpose of the experimental patch is **not** to modify the unknown low-level cause.

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

The normal RSSI-dependent desired beacon-skip selection remains functional.

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

The successful transfer does not by itself prove that Range support was the sole reason the earlier transfer failed.

---

## 16. Patched Hardware Runtime Validation

The experimental patch has now been tested on multiple physical SHTRV-01 devices.

### Device .228 — Patched 2.2.4

The first extended patched run produced the following battery/runtime observations:

| Runtime | Battery | Voltage | Steps | Reconnects | desired / real | beacon_err |
|---|---:|---:|---:|---:|---:|---:|
| ~1 h | 99 % | 4.069 V | - | - | - | - |
| >9 h | 99 % | 4.038 V | - | - | - | - |
| 34 h 39 min | 99 % | 3.940 V | 34331 | 2 | 20 / 1 | 0 |
| ~39 h 22 min | 99 % | 3.925 V | 34331 | 2 | 20 / 1 | 0 |

During this first extended run:

- no targeted `Beacon skip error! Attempt recovery` sequence was observed
- no recurring `Enter powersave state 1` recovery transition was observed
- Wi-Fi remained operational
- Shelly Cloud remained operational
- normal beacon-skip operation remained active
- at 34 h 39 min, 30 occurrences of `current beacon skip is 20` were present in the analyzed log
- between 34 h 39 min and approximately 39 h 22 min, no additional motor steps were recorded
- reconnect count remained unchanged during that interval

The voltage change must not be interpreted as a linear battery-consumption rate.

#### Second .228 Run

The device was subsequently restarted.

The second run must therefore be treated separately.

A measurement approximately two hours into the second run showed:

```text
uptime_counter: approximately 7253 s
battery: 99 %
voltage: 3.865 V
steps_counter: 16605
reboot_counter: 2
reconnect_counter: 4
desired_beacon_skip: 20
real_beacon_skip: 1
beacon_err_counter: 0
```

The high step count in this run is strongly influenced by the automatic calibration sequence after reboot.

This particular device was not mounted on a radiator valve during this test, so automatic calibration failure after restart is expected and must not be interpreted as evidence of a patch failure or battery drain.

The current log continued to show normal:

```text
current beacon skip is 20
```

messages without an observed recurrence of the targeted recovery sequence in the analyzed excerpt.

### Device .88 — Patched 2.2.4 on Radiator

A second patched device remained installed on a radiator and therefore provides a more representative thermostat/motor test.

Measurements included:

| Runtime | Battery | Voltage | Steps | Reconnects | desired / real | beacon_err |
|---|---:|---:|---:|---:|---:|---:|
| 8 h 31 min | 94 % | 3.817 V | 8098 | 1 | 20 / 3 | 0 |
| ~13 h 10 min | 94 % | 3.813 V | 9118 | 1 | 20 / 6 | 0 |
| ~32 h 08 min | 91 % | 3.795 V | 13898 | 1 | 20 / 5 | 0 |

Between approximately 13 h 10 min and 32 h 08 min:

```text
runtime increase: approximately 18 h 58 min
battery: 94 % -> 91 %
voltage: 3.813 V -> 3.795 V
motor steps: +4780
reconnects: unchanged
beacon_err_counter: 0
```

The percentage decrease is noteworthy but cannot currently be classified as evidence of remaining abnormal battery drain.

Important uncontrolled variables include:

- battery age
- actual remaining battery capacity
- battery internal resistance
- previous charge/discharge history
- previous deep discharge
- temperature
- motor load
- number of valve movements

### Physical Valve Test

Real thermostat valve movement was tested on the patched `.88` device.

Opening and closing were both physically confirmed.

For the observed movement:

```text
requested steps: 68
executed steps:  68
```

for each direction.

This confirms that the experimental recovery bypass does not prevent normal valve actuation under the tested conditions.

### Current Runtime Interpretation

The patched runtime data now provide stronger evidence than the original short test:

```text
patched 2.2.4
      |
      v
boots normally
      |
      v
Wi-Fi and cloud operate
      |
      v
RSSI-dependent beacon-skip selection operates
      |
      v
thermostat calibration operates on mounted hardware
      |
      v
physical valve movement operates
      |
      v
targeted recurring recovery loop remains absent
```

This is evidence for the behavior of the control-flow patch.

It is **not yet evidence that battery life has been restored to normal**.

---

## 17. Battery-Drain Investigation

Battery behavior is now being treated as a separate experimental question from suppression of the 2.2.4 recovery loop.

### Battery Data Source

During testing, Home Assistant and the TRV's own `/status` endpoint were observed reporting different battery percentages for the same device.

For example, device `.229` reported:

```text
TRV /status: 100 %
Home Assistant: 91 %
```

at approximately the same time.

For the remainder of this investigation, the authoritative battery values are therefore taken directly from the TRV:

```text
bat.value
bat.voltage
```

Home Assistant battery percentage is not used for battery-consumption calculations.

### Battery Age as a Confounding Variable

The batteries in the physical test devices are not known to be identical in age or condition.

Unknown variables include:

- number of charge cycles
- remaining usable capacity
- internal resistance
- previous deep-discharge events
- storage conditions
- battery aging

Absolute discharge behavior from different physical TRVs therefore cannot be directly compared as if all devices contained identical new batteries.

### Voltage Interpretation

Battery voltage is useful as an additional measurement but is not a direct capacity meter.

Voltage depends on factors including:

- load
- cell relaxation
- temperature
- motor activity
- internal resistance
- battery chemistry and state of charge

For this reason, isolated voltage differences must not be converted directly into consumption rates.

The strongest future comparisons will use:

1. the same physical TRV
2. the same battery
3. controlled charging
4. comparable network conditions
5. comparable thermostat/motor workload
6. stock firmware vs. patched firmware over extended periods

---

## 18. Older Firmware Battery References

Older firmware versions are important because battery drain may predate the recurring 2.2.4 recovery mechanism.

### Device .11 — Original Firmware 2.1.0

The `.11` reference device has been observed running original firmware:

```text
20211223-144805/v2.1.0@d30148ec
```

One documented long-runtime point showed:

```text
uptime: 355568 s
battery: 100 %
voltage: 3.886 V
RSSI: approximately -81 dBm
```

or approximately:

```text
98 h 46 min
```

No regularly recurring 2.2.4-style recovery loop was observed in the analyzed log.

At weak signal strength the normal RSSI-dependent beacon-skip logic selected:

```text
skip 10
```

This device therefore demonstrates that older firmware already contained adaptive beacon skipping while lacking the regularly observed 2.2.4 recovery cycle.

The battery condition of this device is not controlled, so the 100 % indication after this runtime must not be treated as a precise battery-capacity measurement.

### Device .229 — Original Firmware 2.1.8

Before the planned stock-2.2.4 control test, `.229` was running:

```text
20220811-152343/v2.1.8@5afc928c
```

A documented point showed:

```text
uptime: approximately 13 h 48 min
battery: 100 %
voltage: 4.157 V
RSSI: -79 dBm
cloud: disabled
```

The analyzed 2.1.8 log does not show a regularly recurring 2.2.4-style recovery loop.

However, historical use of this device indicates that relatively fast battery drain was already present on firmware 2.1.8.

This makes 2.1.8 particularly important for the root-cause investigation.

A possible interpretation is that:

```text
underlying power-save / Wi-Fi inefficiency
               |
               | may already exist
               v
             2.1.x
               |
               | later firmware change
               v
additional recovery mechanism
               |
               v
             2.2.x
```

This is only a working model.

The current evidence does not establish when an underlying battery-related regression occurred or whether the two behaviors share the same root cause.

---

## 19. Stock 2.2.4 Control Test

Device `.229` is planned as an unpatched stock-2.2.4 control device.

The intended procedure is:

```text
finish 2.1.8 reference measurements
        |
        v
fully charge battery
        |
        v
install original stock 2.2.4
        |
        v
record initial T0 values
        |
        v
collect repeated runtime measurements
        |
        v
compare with patched-device behavior
```

The new stock-2.2.4 run must be treated as a separate measurement series.

Important values include:

```text
uptime
bat.value
bat.voltage
RSSI
steps_counter
reconnect_counter
desired_beacon_skip
real_beacon_skip
beacon_err_counter
recovery messages
power-save state transitions
```

Time intervals should primarily be derived from TRV uptime rather than wall-clock estimates.

The stock control is intended to help answer two different questions:

1. How frequently does the original 2.2.4 recovery sequence occur on this physical device?
2. Does battery behavior differ materially from patched operation when tested over a sufficiently long period?

---

## 20. Runtime Diagnostic Fields

Firmware 2.2.4 exposes several useful runtime statistics.

Observed fields include:

```text
desired_beacon_skip
real_beacon_skip
beacon_err_counter
beacon_rx_count
beacon_rx_missed_count
beacon_tbtt_diff
reboot_counter
reconnect_counter
steps_counter
sleep_ratio
```

### desired_beacon_skip

This field correlates with the known RSSI-dependent target selection:

```text
>= -69 dBm       -> 20
-79..-70 dBm     -> 15
< -79 dBm        -> 10
```

### real_beacon_skip

Observed patched-device values have included:

```text
1
3
5
6
```

while `desired_beacon_skip` remained:

```text
20
```

At the same time, runtime logging can continue to report:

```text
current beacon skip is 20
```

The exact semantics of `real_beacon_skip` have therefore not been established.

It must not currently be assumed that:

```text
real_beacon_skip
```

directly equals the configured hardware beacon-skip value.

It also must not currently be assumed that `real_beacon_skip` is the same variable as the value referenced through:

```text
DAT_0001e23c
```

in the recovery condition.

Tracing the implementation of these diagnostic fields is an important reverse-engineering target.

### beacon_err_counter

The observed patched devices have reported:

```text
beacon_err_counter: 0
```

during several measurement points.

The exact semantics of this counter are not yet fully established.

It should therefore not automatically be described as a direct count of the user-visible recovery sequence without further code analysis.

---

## 21. Wi-Fi Stack Versions

The investigation should not focus only on Shelly's higher-level application code.

Changes in the lower Wi-Fi stack may also be relevant.

For example, firmware 2.1.0 reports:

```text
FMAC Driver version    3.3.2
WF200 Firmware version 3.12.2
```

while firmware 2.1.8 reports:

```text
FMAC Driver version    3.4.1
WF200 Firmware version 3.14.0
```

and firmware 2.2.4 reports:

```text
FMAC Driver version    3.7.0
WF200 Firmware version 3.16.1
```

These version changes do **not** establish that the Wi-Fi stack is responsible for battery drain.

They do, however, provide additional version boundaries that should be considered when comparing:

```text
2.1.0
2.1.3
2.1.6
2.1.7
2.1.8
2.2.x
```

Future firmware-diff work should therefore consider both:

- Shelly application-level power-save/recovery logic
- FMAC / WF200 version changes

---

## 22. Standalone Firmware Patcher

The research findings have been implemented as a separate user-facing project:

**[Shelly TRV Gen1 2.2.4 Firmware Patcher](https://github.com/AbleMonster/Shelly-TRV-Gen1-2.2.4-patcher)**

The standalone patcher:

- accepts an original firmware image supplied locally by the user
- verifies the exact supported firmware using SHA-256
- validates the expected GBL structure
- validates the original CRC32
- validates the expected program block and patch location
- refuses unknown or modified input images
- applies only the documented one-byte modification
- rebuilds the GBL
- recalculates and verifies CRC32
- verifies the expected patched hashes and binary differences
- provides read-only analysis and dry-run modes
- does not automatically flash a device

The companion `ota_server.py` provides a local HTTP/1.1 server with Range support for transferring the locally generated firmware to a Shelly TRV.

The first public experimental release is:

```text
v0.1.0
```

Neither repository distributes original or modified Shelly firmware.

---

## 23. Tools

The investigation uses:

- Ghidra
- Python 3
- PowerShell
- Git
- custom GBL analysis tools
- custom patched-GBL builder
- custom diagnostic OTA HTTP server
- standalone fail-closed firmware patcher

Further reverse-engineering tooling may also be used to assist with:

- string-to-function cross references
- call-graph analysis
- data-reference tracing
- comparison of firmware versions
- tracing writes to unknown state variables
- tracing `/stats` diagnostic fields

Manual verification in Ghidra remains important for security-critical or patch-critical conclusions.

---

## 24. Current Evidence

The current evidence supports the following statements with different levels of confidence.

| Statement | Current status |
|---|---|
| Stock 2.2.4 can repeatedly trigger the beacon-skip recovery sequence on multiple physical SHTRV-01 devices | Well supported |
| Poor RSSI alone explains the recovery behavior | Not supported |
| CoIoT alone explains the recovery behavior | Not supported |
| Mesh steering alone explains the recovery behavior | Not supported |
| The one-byte patch suppresses the targeted recovery sequence on multiple tested devices | Increasingly well supported |
| Normal Wi-Fi operation continues with the patch | Confirmed under tested conditions |
| Shelly Cloud operation continues with the patch | Confirmed under tested conditions |
| RSSI-dependent desired beacon-skip selection continues with the patch | Confirmed |
| Thermostat calibration works on mounted patched hardware | Confirmed |
| Physical valve movement works on patched hardware | Confirmed |
| The patch reduces abnormal battery consumption | Open |
| The recurring recovery sequence is the complete cause of the battery-drain problem | Not proven |
| Battery drain may exist without the regularly recurring 2.2.4 recovery loop | Supported by historical 2.1.8 observation, requires further controlled testing |
| `real_beacon_skip` directly represents the hardware beacon-skip setting | Not proven / questionable |
| The internal recovery-condition value equals `real_beacon_skip` | Not proven |
| Device/AP/BSSID selection may influence observed behavior | Under investigation |

---

## 25. Current Verification Status

### Completed

```text
[OK] Reproduced beacon-recovery behavior on multiple devices running stock firmware 2.2.4

[OK] Compared runtime behavior with older firmware versions

[OK] Analyzed firmware 2.1.0 runtime behavior

[OK] Analyzed firmware 2.1.8 runtime behavior

[OK] Identified RSSI-to-desired-beacon-skip logic

[OK] Confirmed RSSI-dependent beacon-skip behavior exists in older firmware

[OK] Identified power-save state handler

[OK] Identified additional 2.2.4 recovery path

[OK] Identified recovery condition around 0x0001E1B6

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

[OK] Performed OTA installation on multiple physical SHTRV-01 devices

[OK] Patched firmware booted as firmware 2.2.4

[OK] Wi-Fi connectivity verified

[OK] Shelly Cloud connectivity verified

[OK] Normal RSSI-dependent beacon-skip selection verified

[OK] Extended patched runtime beyond 39 hours on one device

[OK] Extended patched runtime beyond 32 hours on a radiator-mounted device

[OK] Thermostat calibration verified on mounted patched hardware

[OK] Physical valve opening verified

[OK] Physical valve closing verified

[OK] No recurring targeted beacon-recovery cycle observed during monitored patched-firmware periods

[OK] Created fail-closed standalone firmware patcher

[OK] Added deterministic firmware, structure, CRC32 and hash validation

[OK] Added standalone local HTTP/1.1 OTA server with Range support

[OK] Tested complete local patch -> OTA -> boot workflow

[OK] Tested upgrade from original firmware 2.1.3 to patched firmware 2.2.4

[OK] Published experimental patcher release v0.1.0

[OK] Established TRV /status as primary battery-data source for this investigation

[OK] Identified battery age/condition as a major uncontrolled comparison variable
```

### Still Pending

```text
[TODO] Multi-day and multi-week patched runtime testing

[TODO] Multi-day stock 2.2.4 control measurement

[TODO] Controlled stock-vs-patch battery comparison

[TODO] Additional long-term Wi-Fi stability monitoring

[TODO] Additional monitoring for unexpected reboots

[TODO] Test additional RSSI conditions / desired beacon-skip values

[TODO] Quantify any battery-life difference between patched and unpatched firmware

[TODO] Control battery age/capacity where practical

[TODO] Test additional SHTRV-01 devices / hardware revisions where available

[TODO] Determine when battery-related behavior changed across older firmware versions

[TODO] Compare firmware 2.1.3, 2.1.6, 2.1.7, 2.1.8 and 2.2.x

[TODO] Determine when the additional recovery mechanism was introduced

[TODO] Determine the exact low-level root cause of the original beacon issue

[TODO] Determine the exact semantics of the internal recovery-condition value

[TODO] Determine the exact semantics of real_beacon_skip

[TODO] Determine the exact semantics of beacon_err_counter

[TODO] Determine the exact semantics of beacon_tbtt_diff

[TODO] Trace AP/BSSID association behavior

[TODO] Compare FMAC/WF200 changes across relevant firmware versions
```

---

## 26. Important Limitations

The current patch is an **experimental recovery bypass**.

It does not prove that the actual cause of the beacon-skip problem has been identified or corrected.

In particular, the exact meaning of the value used by the recovery condition has not yet been conclusively established.

The modification changes the control flow so that the additional 2.2.4 recovery block is bypassed while execution continues at the firmware's existing common continuation.

Physical-device testing now answers the following question positively under the tested conditions:

> Can firmware 2.2.4 boot and continue normal Wi-Fi, cloud, thermostat, valve, and RSSI-dependent beacon-skip operation when the identified additional beacon-recovery block is bypassed?

Under the currently tested conditions, the answer is **yes**.

The evidence now includes:

- multiple physical SHTRV-01 devices
- a patched runtime exceeding approximately 39 hours
- another patched radiator-mounted device exceeding approximately 32 hours
- Wi-Fi connectivity
- Shelly Cloud connectivity
- thermostat calibration
- physical valve opening and closing
- continued RSSI-dependent desired beacon-skip selection
- no observed recurrence of the targeted recurring recovery sequence during the analyzed patched runs

However, this is not sufficient to classify the modification as a final battery-drain fix.

The current evidence does **not** establish that:

- the original low-level WLAN issue has been identified
- the recovery path was the primary cause of battery consumption
- the recovery path was the only cause of battery consumption
- battery life is improved by a specific amount
- firmware 2.1.8 is free from abnormal battery consumption
- long-term operation is free of delayed side effects
- every network configuration behaves identically
- every SHTRV-01 hardware revision behaves identically
- every battery has comparable usable capacity
- the patch is safe under every possible network or hardware condition

In particular:

> Historical battery-drain behavior on firmware 2.1.8 means that the absence of the recurring 2.2.4 recovery sequence cannot be used as proof of normal battery consumption.

---

## 27. Next Steps

The project has moved beyond initial patch construction.

The immediate focus is now controlled validation and root-cause analysis.

### Stock 2.2.4 Control

Device `.229` will be fully charged and used for an unmodified stock-2.2.4 measurement series.

The purpose is to compare:

```text
stock 2.2.4
vs.
patched 2.2.4
```

while collecting:

- uptime
- `bat.value`
- `bat.voltage`
- RSSI
- motor steps
- reconnects
- desired beacon skip
- real beacon skip
- beacon error counter
- recovery frequency
- power-save transitions

### Older Firmware Analysis

The firmware timeline should be investigated more systematically:

```text
2.1.0
  |
2.1.3
  |
2.1.6
  |
2.1.7
  |
2.1.8
  |
2.2.x
```

The analysis should attempt to identify separately:

1. changes to normal beacon/power-save behavior
2. changes to FMAC/WF200 components
3. changes intended to improve reachability
4. introduction of the additional recovery mechanism

### Recovery Variable

The value referenced through:

```text
DAT_0001e23c
```

should be traced through all read/write references.

The main questions are:

- where is it written?
- under what conditions does it become `1` or `2`?
- what resets it?
- is it derived from missed beacons?
- is it related to TBTT timing?
- is it related to an observed beacon-skip metric?
- is it related in any way to `real_beacon_skip`?

No equivalence should be assumed before the data flow is established.

### Runtime Diagnostic Fields

The implementation of the following fields should be traced:

```text
desired_beacon_skip
real_beacon_skip
beacon_err_counter
beacon_rx_count
beacon_rx_missed_count
beacon_tbtt_diff
```

Particular attention should be given to how these values are updated and whether they originate in Shelly application code, the FMAC layer, or the WF200 interface.

### AP / BSSID Behavior

The unexpected RSSI difference between physical devices placed in the same general location should be investigated.

Future measurements should record:

- connected BSSID
- visible BSSIDs
- RSSI of each candidate AP
- selected AP after reboot
- firmware version
- desired beacon skip

This may help determine whether association behavior contributes to power-save conditions or battery consumption.

### Battery Testing

Battery testing should prioritize controlled comparisons using the same physical hardware and battery where possible.

No conclusion about battery-life improvement should be published until sufficient stock-vs-patch runtime data are available.

---

## 28. Feedback and Test Results

External test results are welcome.

Useful reports include:

- exact SHTRV-01 firmware version
- stock or patched firmware
- uptime
- direct TRV `/status` battery percentage
- direct TRV `/status` battery voltage
- RSSI
- `desired_beacon_skip`
- `real_beacon_skip`
- `beacon_err_counter`
- motor step count
- reconnect count
- frequency of `Beacon skip error! Attempt recovery`
- router / access-point environment
- approximate time since full charge
- whether the device is installed on a radiator valve
- whether calibration and valve movement work normally

Older firmware observations are particularly valuable.

If you still have an SHTRV-01 running an older firmware version, consider documenting its current version and runtime behavior before updating it.

Please sanitize logs before publishing them.

Logs may contain information such as:

- MAC addresses
- local IP addresses
- SSIDs
- public IP information
- location-related cloud data
- cloud/session identifiers
- keys or initialization values

Do not upload original or modified Shelly firmware images.

Use the repository's GitHub Discussions or Issues for technical observations and reproducible test results.

---

## 29. Current Scientific Interpretation

The current evidence supports the following conservative interpretation:

> The experimental one-byte patch suppresses the recurring beacon-skip recovery sequence observed on multiple physical SHTRV-01 devices running firmware 2.2.4. Patched devices have continued normal observed Wi-Fi, cloud, thermostat, calibration, valve, and RSSI-dependent beacon-skip operation during the current test periods.
>
> The patch therefore appears to behave as intended as a control-flow experiment targeting the additional 2.2.4 recovery mechanism.
>
> It has **not** yet been established that suppressing this recovery mechanism reduces the underlying battery drain.
>
> Historical battery behavior on firmware 2.1.8 suggests that abnormal battery consumption may predate the regularly recurring 2.2.4 recovery loop. The underlying battery-drain mechanism and the later recovery behavior must therefore remain separate research questions until controlled measurements and further reverse engineering establish their relationship.

---

## 30. Research Direction

The patch itself is currently considered stable enough for continued experimental validation.

The next priority is therefore not to expand the patch unnecessarily.

The research priority is:

```text
Patch no more than necessary.
Measure.
Compare.
Trace the firmware.
Understand the root cause.
```

The most important unresolved question is no longer simply:

```text
Can the 2.2.4 recovery loop be suppressed?
```

Current hardware testing increasingly indicates that it can.

The more important questions are now:

```text
Why does the firmware enter the recovery path?

What does the internal recovery value actually represent?

When was this recovery mechanism introduced?

What changed in the power-save/Wi-Fi behavior between older firmware versions?

Why was battery drain already observed on 2.1.8?

Are the battery-drain behavior and the 2.2.4 recovery mechanism causally related,
or are they separate consequences of a deeper Wi-Fi/power-save issue?
```

Until those questions are answered, the one-byte modification should be described as an:

**experimental beacon-recovery bypass**

and not as a proven battery-drain fix.

---

## Repository Scope

This repository should continue to distribute only independently created:

- source code
- documentation
- technical analysis
- hashes
- offsets
- patching logic
- test results
- sanitized logs where appropriate

It should **not** distribute original or modified Shelly firmware images.

For the user-facing local patching workflow, see:

**[Shelly TRV Gen1 2.2.4 Firmware Patcher](https://github.com/AbleMonster/Shelly-TRV-Gen1-2.2.4-patcher)**

Current experimental patcher release:

```text
v0.1.0
```