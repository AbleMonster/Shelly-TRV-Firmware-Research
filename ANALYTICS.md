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