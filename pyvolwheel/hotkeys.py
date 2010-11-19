#
# pyvolwheel
# Copyright (C) 2010 epinull <epinull at gmail dot com>
#
# This software is provided 'as-is', without any express or implied
# warranty. In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
#    1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
#
#    2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
#
#    3. This notice may not be removed or altered from any source
#    distribution.
#

try:
    from Xlib import X
    from Xlib.display import Display
except ImportError:
    available = False
else:
    available = True

import select
import threading
import gtk.gdk
import gobject

def parse_key(key):
    # Returns a (keycode, modifiers) tuple
    keymap = gtk.gdk.keymap_get_default()
    # Parse
    keyval, mods = gtk.accelerator_parse(key)
    if gtk.accelerator_valid(keyval, mods):
        keycode = keymap.get_entries_for_keyval(keyval)[0][0]
        return keycode, int(mods)

def get_known_modifiers():
    gdk_modifiers = (gtk.gdk.CONTROL_MASK, gtk.gdk.SHIFT_MASK,
                     gtk.gdk.MOD1_MASK, gtk.gdk.MOD2_MASK,
                     gtk.gdk.MOD3_MASK, gtk.gdk.MOD4_MASK,
                     gtk.gdk.MOD5_MASK, gtk.gdk.SUPER_MASK,
                     gtk.gdk.HYPER_MASK)
    mask = 0
    for modifier in gdk_modifiers:
        if "Mod" not in gtk.accelerator_name (0, modifier):
            mask |= modifier
    return mask

class HotKeyListener(gobject.GObject, threading.Thread):
    __gsignals__ = {
            'key-press': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                          (gobject.TYPE_STRING,))
            }

    def __init__(self, keybinds):
        gobject.GObject.__init__(self)
        threading.Thread.__init__(self)
        self.display = Display()
        self.screen = self.display.screen()
        self.root = self.screen.root
        self._mod_mask = get_known_modifiers()
        self._keys = {}
        # Parse and load the keybinds:
        for act, key in keybinds.iteritems():
            km = parse_key(key)
            if km is not None:
                self._keys[km] = act

    def _grab(self):
        for keycode, _ in self._keys.keys():
            self.root.grab_key(keycode, X.AnyModifier, True,
                               X.GrabModeAsync,
                               X.GrabModeSync)

    def _ungrab(self):
        for keycode, _ in self._keys.keys():
            self.root.ungrab_key(keycode, X.AnyModifier, self.root)

    def _emit(self, key):
        gtk.gdk.threads_enter()
        self.emit('key-press', key)
        gtk.gdk.threads_leave()

    def _key_pressed_action(self, keycode, modifiers):
        modifiers &= self._mod_mask
        for km,act in self._keys.iteritems():
            if keycode == km[0] and modifiers == km[1]:
                return act

    def run(self):
        self._running = True
        self._grab()
        while self._running is True:
            # Wait for new events
            select.select([self.display], [], [], 1)
            # Pump events
            while self.display.pending_events() > 0:
                event = self.display.next_event()
                if event.type == X.KeyPress:
                    act = self._key_pressed_action(event.detail, event.state)
                    if act is not None:
                        gobject.idle_add(self._emit, act)
                        self.display.allow_events(X.AsyncKeyboard, event.time)
                    else:
                        self.display.allow_events(X.ReplayKeyboard, event.time)
        self.display.close()

    def stop(self):
        self._ungrab()
        self._running = False

# vim: filetype=python:et:sw=4:ts=4:sts=4:tw=79
