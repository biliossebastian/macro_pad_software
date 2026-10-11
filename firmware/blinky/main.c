/*
 * Blinky - BRINGUP.md Stage 0 test firmware for the custom RP2040 macro pad PCBA.
 *
 * Purpose: prove the external QSPI flash (W25Q16JVSSIQ) works. Enumerating as
 * the RPI-RP2 drive proves the rails, the 12 MHz crystal and USB routing, but
 * says nothing about flash, because the boot ROM runs from internal ROM/SRAM.
 * This image runs *from flash*, so if it runs at all, the flash is good.
 *
 * Two independent "it is alive" signals, deliberately:
 *   1. The RPI-RP2 drive unmounts and stays gone   <- the actual pass/fail
 *   2. The LED blinks + a USB serial heartbeat     <- corroboration
 *
 * Signal 1 is the one that matters. A dark LED with a healthy serial heartbeat
 * means the flash is fine and the LED net is the problem - which is exactly the
 * two-unknowns-at-once trap that Stage 0 exists to avoid.
 */

#include <stdio.h>
#include "pico/stdlib.h"

/*
 * GPIO25 == package pin 37 on the RP2040 QFN-56, so "toggle GPIO25" and
 * "blink the LED on pin 37" are the same net described two ways. If pin 37 on
 * your schematic turns out to be a header/connector pin rather than the package
 * pin, this #define is the only line that changes.
 */
#define LED_PIN 25

/*
 * A distinctive double-blink, not a symmetric 500/500. A stuck rail or a stray
 * pull-up can fake a steady half-second flash; nothing fakes this pattern.
 */
#define BLINK_ON_MS    120
#define BLINK_GAP_MS   120
#define BLINK_PAUSE_MS 700

int main(void) {
    stdio_init_all();

    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);

    uint32_t beat = 0;

    for (;;) {
        /* Blink unconditionally - never gate this on stdio_usb_connected(),
         * or the board looks dead whenever no terminal is attached. */
        for (int i = 0; i < 2; i++) {
            gpio_put(LED_PIN, 1);
            sleep_ms(BLINK_ON_MS);
            gpio_put(LED_PIN, 0);
            sleep_ms(BLINK_GAP_MS);
        }
        sleep_ms(BLINK_PAUSE_MS);

        printf("blinky: running from flash, beat %lu\n", (unsigned long)beat++);
    }
}
