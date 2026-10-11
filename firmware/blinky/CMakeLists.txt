cmake_minimum_required(VERSION 3.13)

# Pulls in the SDK. Honours PICO_SDK_PATH from the environment, or -DPICO_SDK_PATH=...
include(pico_sdk_import.cmake)

project(blinky C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# PICO_BOARD=pico is deliberate, not a placeholder. Two things must match the
# custom PCBA and both do:
#   - PICO_FLASH_SIZE_BYTES = 2 MB, and the W25Q16JVSSIQ is 16 Mbit = 2 MB.
#   - It selects the boot2_w25q080 second stage, the generic Winbond QSPI
#     bootloader, which is correct for the W25Q16JV.
# A hand-rolled board header would need PICO_BOOT_STAGE2_CHOOSE_W25Q080 1
# explicitly, or it silently falls back to boot2_generic_03h - that still boots,
# but reads flash far more slowly. Add a real board header once the schematic
# pin definitions land; a blinky does not need one.
if(NOT PICO_BOARD)
    set(PICO_BOARD pico)
endif()

pico_sdk_init()

add_executable(blinky main.c)

target_link_libraries(blinky pico_stdlib)

# USB serial heartbeat: the second, independent "running from flash" signal.
# UART is off because the custom PCBA has no guaranteed debug header.
pico_enable_stdio_usb(blinky 1)
pico_enable_stdio_uart(blinky 0)

# Produces blinky.uf2 alongside the .elf - the drag-and-drop artefact.
pico_add_extra_outputs(blinky)
