// Bring-up test keymap.
//   keys      a b c / d e f / g h i
//   enc push  j k l          (needs R24 fitted)
//   enc turn  encoder 0 steps system volume, encoders 1-2 step LED brightness (ccw down / cw up)
//   LED1..9   SK6812 mini chain on GP24, full-saturation rainbow wave; red while any key is held
// Hold the top-left key while plugging in to enter the bootloader (bootmagic),
// or double-tap the reset button.
#include QMK_KEYBOARD_H

#define STATUS_LED_PIN GP25
// rainbow_swirl spreads the full hue wheel along the chain (LED1..LED9) and
// rotates it. +4 is the fastest speed: one hue step per 20 ms, ~5 s per lap.
#define RAINBOW_MODE (RGBLIGHT_MODE_RAINBOW_SWIRL + 4)

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [0] = LAYOUT(
        KC_A, KC_B, KC_C,
        KC_D, KC_E, KC_F,
        KC_G, KC_H, KC_I,
        KC_J, KC_K, KC_L
    )
};

static uint8_t held = 0;

static void show_colour(void) {
    if (held > 0) {
        rgblight_mode_noeeprom(RGBLIGHT_MODE_STATIC_LIGHT);
        rgblight_sethsv_noeeprom(0, 255, rgblight_get_val()); // red, at the current brightness
    } else if (rgblight_get_mode() != RAINBOW_MODE) {
        rgblight_sethsv_noeeprom(rgblight_get_hue(), 255, rgblight_get_val());
        rgblight_mode_noeeprom(RAINBOW_MODE);
    }
}

void keyboard_pre_init_user(void) {
    // Alternate row routes via the DNP 0R links; keep them high-Z in case they get fitted.
    gpio_set_pin_input(GP8);
    gpio_set_pin_input(GP9);
    gpio_set_pin_input(GP10);
    gpio_set_pin_output(STATUS_LED_PIN);
}

// Force the SK6812 chain on regardless of what the previous firmware left in
// EEPROM; _noeeprom so this test never writes RGB state to flash.
void keyboard_post_init_user(void) {
    rgblight_enable_noeeprom();
    rgblight_sethsv_noeeprom(0, 255, RGBLIGHT_LIMIT_VAL);
    rgblight_mode_noeeprom(RAINBOW_MODE);
}

// Heartbeat on the status LED so "firmware is running" is visible without a host.
void housekeeping_task_user(void) {
    static uint32_t last = 0;
    if (timer_elapsed32(last) > 500) {
        last = timer_read32();
        gpio_toggle_pin(STATUS_LED_PIN);
    }
}

bool encoder_update_user(uint8_t index, bool clockwise) {
    if (index == 0) {
        tap_code(clockwise ? KC_VOLU : KC_VOLD);
    } else if (clockwise) {
        rgblight_increase_val_noeeprom();
    } else {
        rgblight_decrease_val_noeeprom();
    }
    uprintf("enc %u %s val %u\n", index, clockwise ? "cw" : "ccw", rgblight_get_val());
    return false;
}

bool process_record_user(uint16_t keycode, keyrecord_t *record) {
    uprintf("row %u col %u %s\n", record->event.key.row, record->event.key.col, record->event.pressed ? "down" : "up");

    // Red while any key is held, back to the rainbow once all are released.
    // Counting rather than toggling keeps multi-key presses sane.
    if (record->event.pressed) {
        held++;
    } else if (held > 0) {
        held--;
    }
    show_colour();
    return true;
}
