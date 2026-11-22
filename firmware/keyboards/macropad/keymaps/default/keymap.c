// Default keymap: Claude Code in VS Code.
// The pad only sends F13..F24, which nothing else uses; what each one does lives in
// vscode/keybindings.json, so behaviour can change without reflashing.
//   key 0,0    F13      new Claude tab
//   enc 0      volume down/up, push mute
//   enc 1      F14/F15  previous/next Claude tab (first turn jumps to the Claude tabs), push F16 focus Claude input
//   enc 2      F17/F18  previous/next file in Source Control or Explorer, opened as a preview
//                       (first turn focuses Source Control), push F19 keep the preview open
// Hold the top-left key while plugging in to enter the bootloader (bootmagic),
// or double-tap the reset button.
#include QMK_KEYBOARD_H

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [0] = LAYOUT(
        KC_F13,  KC_NO,  KC_NO,
        KC_NO,   KC_NO,  KC_NO,
        KC_NO,   KC_NO,  KC_NO,
        KC_MUTE, KC_F16, KC_F19
    )
};

void keyboard_pre_init_user(void) {
    // Alternate row routes via the DNP 0R links; keep them high-Z in case they get fitted.
    gpio_set_pin_input(GP8);
    gpio_set_pin_input(GP9);
    gpio_set_pin_input(GP10);
}

bool encoder_update_user(uint8_t index, bool clockwise) {
    switch (index) {
        case 0: tap_code(clockwise ? KC_VOLU : KC_VOLD); break;
        case 1: tap_code(clockwise ? KC_F15 : KC_F14); break;
        case 2: tap_code(clockwise ? KC_F18 : KC_F17); break;
    }
    return false;
}
