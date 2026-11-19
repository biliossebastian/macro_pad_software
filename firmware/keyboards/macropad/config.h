// Pinout taken from the macro-pad Altium PCB netlist (macro_pad.PcbDoc).
//
// Rows R0..R2 reach GP3..GP5 through the 27R array R15. The 0R links R21..R24
// (GP8..GP11 -> R0..R3) are DNP in the 2026-10-27 BOM, so row 3 (the encoder
// push switches) is only connected if R24 has been fitted by hand.
#pragma once

#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET_TIMEOUT 500U
