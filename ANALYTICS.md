2026_10_07_1

Firmware reverse-engineering checkpoint for Shelly TRV firmware 2.2.4.

Current findings:

- Reproduced recurring "Beacon skip error! Attempt recovery" behavior on firmware 2.2.4.
- Older firmware versions show significantly different beacon/power-save behavior.
- Main WLAN triggers the recovery behavior reproducibly, while guest WLAN did not in previous tests.
- CoIoT and FRITZ!Box Mesh steering were ruled out as direct causes in controlled tests.
- RSSI-dependent desired beacon skip logic identified:
    RSSI >= -69 dBm  -> skip 20
    -79..-70 dBm     -> skip 15
    RSSI < -79 dBm   -> skip 10
- Identified power-save state handler FUN_0001f100().
- State 3 applies the current beacon-skip value to the lower WLAN stack.
- Traced the relevant call chain:

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

- FUN_00058b64 prepares parameters for the lower WLAN stack.
- For the traced path, param_1 == 2.
- FUN_00058b64 maintains a wrapping counter from 0..31 and constructs:
      (counter << 7) | 0x08
  before passing it to FUN_00058750().
- FUN_00058750 is the next function to analyze.

Current assessment:
The failure is strongly associated with the beacon-skip / Wi-Fi power-save handling introduced or changed in firmware 2.2.4. Exact low-level root cause and final patch location are not yet confirmed.

No firmware modifications have been made yet.



2026_10_07_2

Firmware reverse-engineering checkpoint for Shelly TRV firmware 2.1.3 vs. 2.2.4.

Additional findings:

- Firmware 2.1.3 was imported and analyzed separately in Ghidra.
- The RSSI-dependent beacon-skip logic in firmware 2.1.3 was identified in:

    FUN_0001b584()

- The corresponding function in firmware 2.2.4 is:

    FUN_0001d694()

- Direct comparison shows that the desired beacon-skip selection logic is effectively unchanged between 2.1.3 and 2.2.4:

    RSSI >= -69 dBm  -> skip 20
    -79..-70 dBm     -> skip 15
    RSSI < -79 dBm   -> skip 10

- Both versions also suppress beacon-skip changes for small RSSI changes.

- Firmware 2.1.3 applies a changed beacon-skip configuration using:

    FUN_0001c9f0(3)

- Firmware 2.2.4 applies the corresponding configuration using:

    FUN_0001f100(3)

This comparison indicates that the basic RSSI -> desired beacon-skip algorithm itself is not the relevant regression in firmware 2.2.4.


Firmware 2.2.4 recovery logic
--------------------------------

A separate recovery mechanism was identified in:

    FUN_0001d918()

Relevant decompiled condition:

    if ((*DAT_0001e23c != 0) &&
        (*DAT_0001e23c < 3)) {
        ...
    }

The corresponding Thumb instructions are:

    0001e1b8  21 4b        ldr     r3,[DAT_0001e23c]
    0001e1ba  93 f9 00 30  ldrsb.w r3,[r3,#0]
    0001e1be  00 2b        cmp     r3,#0x0
    0001e1c0  36 d0        beq     LAB_0001e22e

    0001e1c2  1e 4b        ldr     r3,[DAT_0001e23c]
    0001e1c4  93 f9 00 30  ldrsb.w r3,[r3,#0]
    0001e1c8  02 2b        cmp     r3,#0x2
    0001e1ca  31 dc        bgt     LAB_0001e22e

Therefore:

    value == 0  -> recovery skipped
    value == 1  -> recovery executed
    value == 2  -> recovery executed
    value >= 3  -> recovery skipped

The exact semantic meaning of DAT_0001e23c has not yet been proven.
It must therefore not yet be treated as definitively equivalent to
"real_beacon_skip".


Recovery path
-------------

For values 1 or 2, firmware 2.2.4 enters a recovery block containing:

    "Beacon skip error! Attempt recovery"

The recovery block also performs:

    *(... + 0x0e) = 5;
    FUN_0001f100(1);

and increments a counter.

This corresponds directly to the behavior observed in the runtime logs:

    Beacon skip error! Attempt recovery
    Enter powersave state 1

followed later by a return to power-save state 3.


Recovery exit
-------------

The recovery block ends with an unconditional branch:

    0001e220  05 e0        b       LAB_0001e22e

LAB_0001e22e is also the target used when the recovery condition is not met.

The common path begins with:

    0001e22e  12 4b        ldr     r3,[DAT_0001e244]
    0001e230  00 22        movs    r2,#0
    0001e232  1a 60        str     r2,[r3,#0]

    0001e234  0a 4b        ldr     r3,[DAT_0001e23c]
    0001e236  00 22        movs    r2,#0
    0001e238  1a 70        strb    r2,[r3,#0]

This confirms that LAB_0001e22e is a common cleanup/continuation path and
not code exclusively associated with the recovery operation.


Current patch candidate
-----------------------

A minimal patch candidate has now been identified.

Original instruction:

    Address:      0x0001E1CA
    Bytes:        31 DC
    Instruction:  bgt LAB_0001e22e

Candidate replacement:

    Bytes:        30 E0
    Instruction:  b LAB_0001e22e

This would force execution directly to the existing common continuation
path and prevent entry into the "Beacon skip error" recovery block.

The normal RSSI-dependent beacon-skip calculation and normal
power-save state 3 handling would remain untouched.


Current assessment
------------------

The comparison with firmware 2.1.3 substantially narrows the suspected
regression.

The normal RSSI-based desired beacon-skip logic is present in both
firmware versions and uses the same thresholds and skip values.

Firmware 2.2.4 contains an additional recovery path that is triggered
when the monitored value stored through DAT_0001e23c is 1 or 2.

This recovery path matches the recurring behavior observed on affected
TRVs running firmware 2.2.4.

The current leading patch strategy is therefore to bypass only this
recovery path rather than modifying the normal beacon-skip or
power-save implementation.

Important:

- The exact semantic meaning of DAT_0001e23c is still under investigation.
- The proposed patch has NOT yet been applied.
- GBL integrity/checksum/signature handling has NOT yet been investigated.
- OTA acceptance of a modified GBL has NOT been tested.
- No modified firmware has been installed on a TRV.


Next steps
----------

1. Create a Git checkpoint of the current unmodified analysis.
2. Work only on a copy of firmware 2.2.4.
3. Apply the candidate branch modification in the analysis copy.
4. Verify the resulting Thumb instruction and control flow.
5. Investigate GBL container integrity/checksum/signature requirements.
6. Generate a testable patched firmware image if possible.
7. Test OTA acceptance.
8. Only after successful validation, test runtime behavior on one TRV.
9. Verify that the recurring recovery event disappears.
10. Perform longer-term battery consumption comparison.