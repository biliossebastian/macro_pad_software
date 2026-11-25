"""Global F20 hotkey: focus VS Code, then cycle through its windows.

The macro pad's bottom-middle key sends F20. VS Code keybindings only fire while
VS Code already has focus, so this runs as a small background process instead:

  - VS Code not focused        -> focus the most recently used VS Code window
  - VS Code focused            -> switch to the previously used VS Code window
  - pressed again within
    CYCLE_TIMEOUT seconds      -> keep walking the remaining VS Code windows, wrapping

Like Alt+Tab: quick presses walk the whole list, a press after a pause goes back
to the previous window.

Run without a console (stdlib only, Windows only):
    pythonw -m macropad.vscode_cycler
List the windows it would cycle through, for checking the filters:
    python -m macropad.vscode_cycler --list
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from ctypes import wintypes
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

# Presses closer together than this continue the current cycle; a slower press
# starts over from the most recently used window.
CYCLE_TIMEOUT = 2.0

VK_F20 = 0x83
VSCODE_EXES = {"code.exe", "code - insiders.exe"}


# --- cycle logic (pure, unit-tested) -----------------------------------------

@dataclass
class CycleState:
    order: List[int]  # VS Code windows, snapshotted when the cycle started
    last_target: int  # window this helper last activated
    last_press: float


def choose_target(
    foreground: int,
    windows: Sequence[int],
    state: Optional[CycleState],
    now: float,
    timeout: float = CYCLE_TIMEOUT,
) -> Tuple[Optional[int], Optional[CycleState]]:
    """Pick the window to activate for one press.

    `windows` are the live VS Code windows in z-order, most recently used first.
    Returns (window to activate or None, state to keep for the next press).
    """
    alive = set(windows)
    continuing = (
        state is not None
        and foreground == state.last_target
        and now - state.last_press <= timeout
    )

    if continuing:
        order = [h for h in state.order if h in alive]
        order += [h for h in windows if h not in order]  # opened mid-cycle: append
        if len(order) < 2:
            return None, None
        target = order[(order.index(foreground) + 1) % len(order)]
    else:
        order = list(windows)
        if foreground in alive:
            order.remove(foreground)
            order.insert(0, foreground)
            if len(order) < 2:
                return None, None
            target = order[1]
        elif order:
            target = order[0]
        else:
            return None, None

    return target, CycleState(order, target, now)


# --- Win32 -------------------------------------------------------------------

if sys.platform == "win32":
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    dwmapi = ctypes.WinDLL("dwmapi")

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _sig(fn, restype, *argtypes):
        fn.restype = restype
        fn.argtypes = argtypes

    _sig(user32.EnumWindows, wintypes.BOOL, WNDENUMPROC, wintypes.LPARAM)
    _sig(user32.IsWindowVisible, wintypes.BOOL, wintypes.HWND)
    _sig(user32.IsWindow, wintypes.BOOL, wintypes.HWND)
    _sig(user32.IsIconic, wintypes.BOOL, wintypes.HWND)
    _sig(user32.GetWindow, wintypes.HWND, wintypes.HWND, wintypes.UINT)
    _sig(user32.GetWindowLongPtrW, ctypes.c_ssize_t, wintypes.HWND, ctypes.c_int)
    _sig(user32.GetWindowTextLengthW, ctypes.c_int, wintypes.HWND)
    _sig(user32.GetWindowTextW, ctypes.c_int, wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    _sig(user32.GetWindowThreadProcessId, wintypes.DWORD, wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    _sig(user32.GetForegroundWindow, wintypes.HWND)
    _sig(user32.SetForegroundWindow, wintypes.BOOL, wintypes.HWND)
    _sig(user32.BringWindowToTop, wintypes.BOOL, wintypes.HWND)
    _sig(user32.ShowWindow, wintypes.BOOL, wintypes.HWND, ctypes.c_int)
    _sig(user32.AttachThreadInput, wintypes.BOOL, wintypes.DWORD, wintypes.DWORD, wintypes.BOOL)
    _sig(user32.RegisterHotKey, wintypes.BOOL, wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
    _sig(user32.GetMessageW, wintypes.BOOL, ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
    _sig(user32.MessageBoxW, ctypes.c_int, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT)
    _sig(kernel32.OpenProcess, wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    _sig(kernel32.CloseHandle, wintypes.BOOL, wintypes.HANDLE)
    _sig(kernel32.QueryFullProcessImageNameW, wintypes.BOOL, wintypes.HANDLE, wintypes.DWORD,
         wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
    _sig(kernel32.GetCurrentThreadId, wintypes.DWORD)
    _sig(dwmapi.DwmGetWindowAttribute, ctypes.c_long, wintypes.HWND, wintypes.DWORD,
         ctypes.c_void_p, wintypes.DWORD)

GW_OWNER = 4
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
DWMWA_CLOAKED = 14
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SW_RESTORE = 9
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
MB_ICONERROR = 0x10


def _hwnd(h) -> int:
    """HWNDs come back as int or None; compare them as plain ints."""
    return h or 0


def _exe_name(hwnd: int) -> str:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buf))
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return ""
        return os.path.basename(buf.value).lower()
    finally:
        kernel32.CloseHandle(handle)


def _is_switchable(hwnd: int) -> bool:
    """Roughly what Alt+Tab shows: visible, unowned, not a tool window, not
    cloaked (cloaked covers windows on other virtual desktops), has a title."""
    if not user32.IsWindowVisible(hwnd) or _hwnd(user32.GetWindow(hwnd, GW_OWNER)):
        return False
    if user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
        return False
    cloaked = wintypes.DWORD()
    if dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)) == 0 \
            and cloaked.value:
        return False
    return user32.GetWindowTextLengthW(hwnd) > 0


def vscode_windows() -> List[int]:
    """VS Code windows in z-order, most recently used first."""
    found: List[int] = []

    def visit(hwnd, _lparam):
        hwnd = _hwnd(hwnd)
        if _is_switchable(hwnd) and _exe_name(hwnd) in VSCODE_EXES:
            found.append(hwnd)
        return True

    user32.EnumWindows(WNDENUMPROC(visit), 0)
    return found


def _title(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(user32.GetWindowTextLengthW(hwnd) + 1)
    user32.GetWindowTextW(hwnd, buf, len(buf))
    return buf.value


def activate(hwnd: int) -> bool:
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    if _hwnd(user32.GetForegroundWindow()) == hwnd:
        return True

    # Windows refused the switch. Borrow the foreground thread's input state
    # for a moment, which lifts the foreground lock for this call.
    fg_thread = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
    me = kernel32.GetCurrentThreadId()
    attached = bool(fg_thread) and fg_thread != me and user32.AttachThreadInput(me, fg_thread, True)
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(me, fg_thread, False)
    return _hwnd(user32.GetForegroundWindow()) == hwnd


def run() -> int:
    if not user32.RegisterHotKey(None, 1, MOD_NOREPEAT, VK_F20):
        user32.MessageBoxW(
            None,
            "Could not register F20. Is another copy of vscode_cycler already running?",
            "VS Code cycler",
            MB_ICONERROR,
        )
        return 1

    state: Optional[CycleState] = None
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message != WM_HOTKEY:
            continue
        target, state = choose_target(
            _hwnd(user32.GetForegroundWindow()), vscode_windows(), state, time.monotonic()
        )
        if target:
            activate(target)
    return 0


def main(argv: Sequence[str]) -> int:
    if sys.platform != "win32":
        print("vscode_cycler is Windows only", file=sys.stderr)
        return 1
    if "--list" in argv:
        for hwnd in vscode_windows():
            print(f"{hwnd:#010x}  {_title(hwnd)}")
        return 0
    return run()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
