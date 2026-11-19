// Bring-up test keymap.
//   keys      a b c / d e f / g h i
//   enc push  j k l          (needs R24 fitted)
//   enc turn  any encoder steps the LED hue down/up (ccw/cw)
//   LED1..9   SK6812 mini chain on GP24, light blue; red while any key is held
// Hold the top-left key while plugging in to enter the bootloader (bootmagic),
// or double-tap the reset button.
#include QMK_KEYBOARD_H

#define STATUS_LED_PIN GP25
#define HUE_STEP 8 // 256 / 8 = 32 detents per full colour wheel

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [0] = LAYOUT(
        KC_A, KC_B, KC_C,
        KC_D, KC_E, KC_F,
        KC_G, KC_H, KC_I,
        KC_J, KC_K, KC_L
    )
};

// Resting colour. Starts at HSV_AZURE (light blue); the encoders move the hue.
static uint8_t base_hue = 132;
static uint8_t held     = 0;

static void show_colour(void) {
    if (held > 0) {
        rgblight_sethsv_noeeprom(HSV_RED);
    } else {
        rgblight_sethsv_noeeprom(base_hue, 102, 120);
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
    rgblight_mode_noeeprom(RGBLIGHT_MODE_STATIC_LIGHT);
    show_colour();
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
    base_hue += clockwise ? HUE_STEP : -HUE_STEP; // uint8_t wraps around the colour wheel
    uprintf("enc %u %s hue %u\n", index, clockwise ? "cw" : "ccw", base_hue);
    show_colour();
    return false;
}

bool process_record_user(uint16_t keycode, keyrecord_t *record) {
    uprintf("row %u col %u %s\n", record->event.key.row, record->event.key.col, record->event.pressed ? "down" : "up");

    // Red while any key is held, back to the resting colour once all are
    // released. Counting rather than toggling keeps multi-key presses sane.
    if (record->event.pressed) {
        held++;
    } else if (held > 0) {
        held--;
    }
    show_colour();
    return true;
}
