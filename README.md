# Shelly TRV Firmware Investigation & Beacon Recovery Patch

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

---

## Project Status

Current status:

- Firmware 2.2.4 investigated
- Older firmware versions tested for comparison
- Firmware 2.1.3 and 2.2.4 statically analyzed with Ghidra
- RSSI-dependent beacon-skip logic identified
- Power-save state handler identified
- Additional beacon-recovery path in 2.2.4 identified
- Experimental one-byte firmware patch created
- Patched program image fully compared against the original
- GBL container structure analyzed
- Patched GBL rebuilt
- CRC32 recalculated and independently verified
- GBL header checked for signing/encryption flags
- OTA test of the patched firmware still pending

> **Important:** The current patch is experimental. It bypasses the identified recovery path, but it does not prove that the underlying cause of the beacon issue has been identified or fixed.

---

# 1. Initial Problem

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

The same recovery behavior was reproduced on another SHTRV-01 running firmware 2.2.4. With a weaker RSSI, that device used:

```text
Enter powersave state 3 (skip 15)
```

This confirms that the observed behavior is not limited to a single TRV.

---

# 2. Wi-Fi Tests

Several network configurations were tested to narrow down the cause.

## Main Wi-Fi Network

The recovery error was reproducible on the main Wi-Fi network.

It occurred even with a good RSSI of approximately:

```text
-56 to -62 dBm
```

Therefore, poor signal strength alone does not explain the behavior.

## Guest Wi-Fi Network

When the same TRV was connected to the guest Wi-Fi network, the recovery error did not occur during the observed test period.

The main and guest networks were transmitted by the same physical access points and on the same radio channels, but used different BSSIDs and network configurations.

This indicates that RF signal quality alone is unlikely to be the determining factor.

## CoIoT

CoIoT was disabled while the TRV remained connected to the main Wi-Fi network.

The recovery error continued to occur.

Therefore, CoIoT and the Home Assistant CoIoT peer were ruled out as direct causes.

## FRITZ!Box Mesh Steering

Automatic steering between frequency bands and FRITZ!Box Mesh access points was temporarily disabled.

The recovery error continued to occur.

Mesh/band steering therefore does not sufficiently explain the behavior.

---

# 3. Firmware Comparison

## Firmware 2.2.4

Firmware 2.2.4 reproducibly exhibits the recovery behavior.

The firmware also explicitly contains the string:

```text
Beacon skip error! Attempt recovery
```

## Firmware 2.1.0

An affected TRV was downgraded to firmware 2.1.0.

On the same main Wi-Fi network and during an extended observation period, the recurring recovery error was not observed.

This provides strong evidence that the behavior is firmware-dependent.

## Firmware 2.1.8

Another TRV running firmware 2.1.8 did not exhibit the same recurring recovery cycle during extended testing.

Messages such as:

```text
signal strength: -65, current beacon skip is 20
```

must not be confused with the recovery error. They only report the currently selected beacon-skip value.

## Firmware 2.1.3

Firmware 2.1.3 was additionally analyzed statically.

The string:

```text
Beacon skip error! Attempt recovery
```

was not found.

However, the basic RSSI-dependent beacon-skip selection logic is already present in firmware 2.1.3.

---

# 4. Beacon-Skip Logic

The RSSI-dependent selection of the desired beacon-skip value was identified in both firmware 2.1.3 and 2.2.4.

The logic is:

```text
RSSI >= -69 dBm     -> Beacon Skip 20
RSSI -79..-70 dBm   -> Beacon Skip 15
RSSI < -79 dBm      -> Beacon Skip 10
```

The basic RSSI-to-beacon-skip algorithm is therefore essentially unchanged between firmware 2.1.3 and 2.2.4.

This suggests that the observed regression is not caused simply by the selection of the desired beacon-skip value.

---

# 5. Power-Save State Handler

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

# 6. Firmware 2.1.3 vs. 2.2.4

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

# 7. Recovery Condition in Firmware 2.2.4

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
value == 0   -> skip recovery
value 1 or 2 -> execute recovery
value > 2    -> skip recovery
```

The exact semantic meaning of the value referenced through `DAT_0001e23c` has not yet been conclusively established.

It should therefore not currently be assigned a definitive name such as `real_beacon_skip`.

---

# 8. Experimental Patch

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

# 9. Binary Patch Verification

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

# 10. GBL Structure

The original firmware image:

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

## Program Block 1

```text
Flash address: 0x00000000
Program data:  1,049,548 bytes
```

## Program Block 2

```text
Flash address: 0x00130A98
Program data:  30,872 bytes
```

The firmware patch affects only Program Block 1.

---

# 11. Binary-to-GBL Mapping

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

# 12. GBL CRC32

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

In other words, CRC32 is calculated over the complete GBL including the end-tag header, but excluding the final four CRC bytes.

The patched GBL produces:

```text
0x432F734F
```

The stored CRC was then independently recalculated and verified:

```text
Stored:     0x432F734F
Calculated: 0x432F734F

CRC OK
```

---

# 13. Patched GBL

Generated file:

```text
SHTRV-01_build_2.2.4_beacon_patch.gbl
```

Size:

```text
1,106,384 bytes
```

SHA-256:

```text
AC7D85C8E9239BEBD3B134C4B93FC838859C613E59F7690650097DA984EA7222
```

A complete comparison between the original and patched GBL showed exactly five changed bytes:

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

---

# 14. GBL Header

The original GBL header payload is:

```text
00 00 00 03 00 00 00 00
```

Interpreted as:

```text
Version: 0x03000000
Type:    0x00000000
```

The container therefore uses the standard GBL format.

No GBL signing or encryption flags are set in the analyzed container.

---

# 15. Tools

The investigation uses:

- Ghidra
- Python 3
- PowerShell
- Git
- custom GBL inspector
- custom patched-GBL builder

## GBL Inspector

```text
scripts/inspect_gbl.py
```

Responsibilities:

- parse and list GBL tags
- identify program-data blocks
- extract flash addresses
- extract program images
- search extracted firmware for relevant strings

## Patched GBL Builder

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

---

# 16. Current Verification Status

Completed:

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
```

Still pending:

```text
[TODO] OTA installation on one test TRV
[TODO] Verify runtime behavior of patched firmware
[TODO] Verify that the recurring recovery cycle no longer occurs
[TODO] Monitor Wi-Fi stability
[TODO] Monitor for unexpected reboots or side effects
[TODO] Long-term battery-consumption test
[TODO] Determine the exact low-level root cause of the original beacon issue
```

---

# 17. Important Limitation

The current patch is an **experimental recovery bypass**.

It does not prove that the actual cause of the beacon-skip problem has been identified or corrected.

In particular, the exact meaning of the value used by the recovery condition has not yet been conclusively established.

The first hardware test is intended to answer one specific question:

> Does firmware 2.2.4 remain stable when its additional beacon-recovery cycle is prevented from executing?

Only runtime testing on real hardware can answer this.

---

# 18. Next Step

Perform a controlled OTA installation of the patched firmware on a single SHTRV-01 test device.

The test should specifically monitor:

- successful firmware boot
- Wi-Fi connectivity
- cloud connectivity
- thermostat operation
- valve motor operation
- power-save state transitions
- beacon-skip behavior
- debug log output
- unexpected reboots
- battery consumption over an extended period

Until the hardware test has been completed successfully, the patched firmware should be considered experimental and must not be treated as a stable or final solution.