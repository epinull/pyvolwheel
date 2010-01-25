#
# pyvolwheel
# Copyright (C) 2010 epinull <epinull at gmail dot com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from subprocess import Popen
import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pyvolwheel
from pyvolwheel import mixer
from pyvolwheel import hotkeys

_volume_icons = ('audio-volume-muted',
                 'audio-volume-low',
                 'audio-volume-medium',
                 'audio-volume-high')
_error_icon = 'dialog-warning'

def _get_vol_icon(volume):
    #      0% = Muted
    #   1-33% = Low
    #  34-67% = Medium
    # 68-100% = High
    if volume <= 0:
        return _volume_icons[0]
    elif volume <= 33:
        return _volume_icons[1]
    elif volume <= 67:
        return _volume_icons[2]
    elif volume <= 100:
        return _volume_icons[3]
    else:
        return _error_icon

def _idx(widget, text):
    try:
        return [r[0] for r in widget.get_model()].index(text)
    except:
        return -1

class ConfigDialog(gtk.Window):
    def _set_saveable(self, widget):
        # Enable/Disable the save button
        if len(widget.get_model()) == 0:
            self.save_button.set_sensitive(False)
        else:
            self.save_button.set_sensitive(True)

    def _fill_combos(self):
        self._filling = True
        # Current settings
        driver = self._main.config.mixer.driver
        device = self._main.config.mixer.device
        control = self._main.config.mixer.control
        # Fill the driver combo only
        self._fill_drivers(False)
        # Set active index to current driver
        self.driver_combo.set_active(_idx(self.driver_combo, driver))
        # Now fill the device combo
        self._fill_devices(False)
        self.device_combo.set_active(_idx(self.device_combo, device))
        # Lastly, fill the controls combo
        self._fill_controls()
        self.control_combo.set_active(_idx(self.control_combo, control))
        self._filling = False
        # See note in on_driver_changed()
        if self.driver_combo.get_active_text() == 'ALSA':
            self.inc_spinner.set_range(3, 99)
        else:
            self.inc_spinner.set_range(1, 99)

    def _fill_drivers(self, cascade=True):
        self._filling = True
        self.driver_combo.get_model().clear()
        for d in mixer.get_drivers():
            self.driver_combo.append_text(d)
        self.driver_combo.set_active(0)
        self._set_saveable(self.driver_combo)
        self._filling = False
        if cascade is True:
            self._fill_devices(True)

    def _fill_devices(self, cascade=True):
        self._filling = True
        self.device_combo.get_model().clear()
        driver = self.driver_combo.get_active_text()
        if driver is None: return
        for dev in mixer.get_devices(driver):
            self.device_combo.append_text(dev)
        self.device_combo.set_active(0)
        self._set_saveable(self.device_combo)
        self._filling = False
        if cascade is True:
            self._fill_controls()

    def _fill_controls(self):
        self._filling = True
        self.control_combo.get_model().clear()
        driver = self.driver_combo.get_active_text()
        device = self.device_combo.get_active_text()
        if driver is None or device is None: return
        for control in mixer.get_controls(driver, device):
            self.control_combo.append_text(control)
        self.control_combo.set_active(0)
        # Prevent saving if the device has no controls
        self._set_saveable(self.control_combo)
        self._filling = False

    def on_driver_changed(self, _):
        if self._filling is True: return False
        self._fill_devices()
        # For some reason when using an ALSA mixer, the inc. can't be less
        # than 3. Bug?
        if self.driver_combo.get_active_text() == 'ALSA':
            self.inc_spinner.set_range(3, 99)
        else:
            self.inc_spinner.set_range(1, 99)
        return True

    def on_device_changed(self, _):
        if self._filling is True: return False
        self._fill_controls()
        return True

    def on_save(self, _):
        # Save on typing, etc. :P
        new_vals = [x.get_active_text() for x in (self.driver_combo,
                                             self.device_combo,
                                             self.control_combo)]
        new_vals.append(self.inc_spinner.get_value_as_int())
        self._main.config.mixer.driver = new_vals[0]
        self._main.config.mixer.device = new_vals[1]
        self._main.config.mixer.control = new_vals[2]
        self._main.config.mixer.increment = new_vals[3]
        self._main.config.mixer.external = self.xm_tbox.get_text()
        self._main.config.restore.enabled = self.rest_check.get_active()
        self._main.config.hotkeys.enabled = self.hk_cb.get_active()
        self._main.config.hotkeys.up = self.hk_up_tbox.get_text()
        self._main.config.hotkeys.down = self.hk_down_tbox.get_text()
        self._main.config.hotkeys.mute = self.hk_mute_tbox.get_text()
        self._main.config.save()
        self._main.reload()
        self.destroy()
        return True

    def on_hk_toggled(self, wdg):
        self.hk_frame.set_sensitive(wdg.get_active())

    def __init__(self, main):
        super(ConfigDialog, self).__init__(gtk.WINDOW_TOPLEVEL)
        self._main = main
        title = "pyvolwheel v{0} Settings".format(pyvolwheel.__version__)
        self.set_title(title)
        self.set_border_width(10)
        self.set_position(gtk.WIN_POS_CENTER)
        # Flag to ignore combobox changes if they're being populated
        self._filling = False
        # Main VBox
        main_vbox = gtk.VBox(spacing=10)
        # Config Notebook
        notebook = gtk.Notebook()
        #### Mixer Settings Tab
        mixer_vbox = gtk.VBox(spacing=10)
        # Driver row
        driver_hbox = gtk.HBox(spacing=10)
        driver_label = gtk.Label("Driver")
        #driver_combo = gtk.ComboBox()
        self.driver_combo = gtk.combo_box_new_text()
        self.driver_combo.set_size_request(150, 30)
        self.driver_combo.connect('changed', self.on_driver_changed)
        driver_hbox.pack_start(driver_label, expand=False, padding=5)
        driver_hbox.pack_end(self.driver_combo, expand=False, padding=5)
        mixer_vbox.pack_start(driver_hbox, expand=False, padding=0)
        # Device Row
        device_hbox = gtk.HBox(spacing=10)
        device_label = gtk.Label("Device")
        self.device_combo = gtk.combo_box_new_text()
        self.device_combo.set_size_request(150, 30)
        self.device_combo.connect('changed', self.on_device_changed)
        device_hbox.pack_start(device_label, expand=False, padding=5)
        device_hbox.pack_end(self.device_combo, expand=False, padding=5)
        mixer_vbox.pack_start(device_hbox, expand=False, padding=0)
        # Control Row
        control_hbox = gtk.HBox(spacing=10)
        control_label = gtk.Label("Control")
        self.control_combo = gtk.combo_box_new_text()
        self.control_combo.set_size_request(150, 30)
        #self.control_combo.connect('changed', self.on_control_changed)
        control_hbox.pack_start(control_label, expand=False, padding=5)
        control_hbox.pack_end(self.control_combo, expand=False, padding=5)
        mixer_vbox.pack_start(control_hbox, expand=False, padding=0)
        # Volume Increment
        inc_hbox = gtk.HBox(spacing=10)
        inc_label = gtk.Label("Volume Increment")
        self.inc_spinner = gtk.SpinButton()
        self.inc_spinner.set_range(1, 99)
        self.inc_spinner.set_increments(1, 10)
        self.inc_spinner.set_numeric(True)
        self.inc_spinner.set_value(main.config.mixer.increment)
        inc_hbox.pack_start(inc_label, expand=False, padding=5)
        inc_hbox.pack_end(self.inc_spinner, expand=False, padding=5)
        mixer_vbox.pack_start(inc_hbox, expand=False, padding=0)
        # Restore
        rest_hbox = gtk.HBox(spacing=10)
        rest_label = gtk.Label("Restore volume at startup")
        self.rest_check = gtk.CheckButton()
        self.rest_check.set_active(main.config.restore.enabled)
        rest_hbox.pack_start(rest_label, expand=False, padding=5)
        rest_hbox.pack_end(self.rest_check, expand=False, padding=5)
        mixer_vbox.pack_start(rest_hbox, expand=False, padding=0)
        # External Mixer
        xm_hbox = gtk.HBox(spacing=10)
        xm_label = gtk.Label("External Mixer")
        self.xm_tbox = gtk.Entry()
        self.xm_tbox.set_text(main.config.mixer.external)
        # Set tooltips
        xm_tip = "Program to launch when the mixer button is pressed"
        xm_hbox.set_tooltip_text(xm_tip)
        xm_label.set_tooltip_text(xm_tip)
        self.xm_tbox.set_tooltip_text(xm_tip)
        xm_hbox.pack_start(xm_label, expand=False, padding=5)
        xm_hbox.pack_end(self.xm_tbox, expand=False, padding=5)
        mixer_vbox.pack_start(xm_hbox, expand=False, padding=0)
        # Add everything to the Mixer page
        notebook.append_page(mixer_vbox, gtk.Label("Mixer"))
        #### End Mixer Settings Tab
        #### Hotkeys Tab
        hk_vbox = gtk.VBox()
        hk_vbox.set_sensitive(hotkeys.available)
        if hotkeys.available is False:
            hk_vbox.set_tooltip_text("Install python-xlib to use hotkeys")
        # Enabled Checkbox
        hk_cb_hbox = gtk.HBox(spacing=10)
        hk_cb_label = gtk.Label("Global Hotkeys")
        self.hk_cb = gtk.CheckButton("Enabled")
        self.hk_cb.set_active(main.config.hotkeys.enabled)
        self.hk_cb.connect('toggled', self.on_hk_toggled)
        hk_cb_hbox.pack_start(hk_cb_label, expand=False, padding=5)
        hk_cb_hbox.pack_end(self.hk_cb, expand=False, padding=5)
        hk_vbox.pack_start(hk_cb_hbox, expand=False, padding=0)
        # Keybinds Frame
        self.hk_frame = gtk.Frame()
        self.hk_frame.set_sensitive(main.config.hotkeys.enabled)
        hk_frame_vbox = gtk.VBox(spacing=10)
        # Raise Volume Key
        hk_up_hbox = gtk.HBox(spacing=10)
        hk_up_label = gtk.Label("Raise Volume Key")
        self.hk_up_tbox = gtk.Entry()
        self.hk_up_tbox.set_text(main.config.hotkeys.up)
        hk_up_hbox.pack_start(hk_up_label, expand=False, padding=5)
        hk_up_hbox.pack_end(self.hk_up_tbox, expand=False, padding=5)
        hk_frame_vbox.pack_start(hk_up_hbox, expand=False, padding=0)
        # Lower Volume Key
        hk_down_hbox = gtk.HBox(spacing=10)
        hk_down_label = gtk.Label("Lower Volume Key")
        self.hk_down_tbox = gtk.Entry()
        self.hk_down_tbox.set_text(main.config.hotkeys.down)
        hk_down_hbox.pack_start(hk_down_label, expand=False, padding=5)
        hk_down_hbox.pack_end(self.hk_down_tbox, expand=False, padding=5)
        hk_frame_vbox.pack_start(hk_down_hbox, expand=False, padding=0)
        # Mute Volume Key
        hk_mute_hbox = gtk.HBox(spacing=10)
        hk_mute_label = gtk.Label("Mute Volume Key")
        self.hk_mute_tbox = gtk.Entry()
        self.hk_mute_tbox.set_text(main.config.hotkeys.mute)
        hk_mute_hbox.pack_start(hk_mute_label, expand=False, padding=5)
        hk_mute_hbox.pack_end(self.hk_mute_tbox, expand=False, padding=5)
        hk_frame_vbox.pack_start(hk_mute_hbox, expand=False, padding=0)
        # Add the vbox to the frame
        self.hk_frame.add(hk_frame_vbox)
        hk_vbox.pack_start(self.hk_frame)
        notebook.append_page(hk_vbox, gtk.Label("Hotkeys"))
        #### End Hotkeys Tab
        main_vbox.pack_start(notebook, expand=False)
        # Bottom Buttons (Save/Cancel)
        bottom_hbox = gtk.HBox(spacing=5)
        # Cancel Button
        cancel_button = gtk.Button(stock='gtk-cancel')
        cancel_button.connect_object('clicked', gtk.Widget.destroy, self)
        bottom_hbox.pack_start(cancel_button)
        # Save Button
        self.save_button = gtk.Button(stock='gtk-save')
        self.save_button.connect('clicked', self.on_save)
        bottom_hbox.pack_end(self.save_button)
        main_vbox.pack_start(bottom_hbox)
        # Add everything to the window
        self.add(main_vbox)
        # Populate the combo boxes
        self._fill_combos()
        self.show_all()
        self.present()

class MiniMixer(gtk.Window):
    def launch_mixer(self, button):
        Popen(self._main.config.mixer.external, shell=True)

    def update(self):
        control = self._main.mixer.get_control()
        self.label.set_text(control)
        vol = self._main.mixer.get_volume()[0]
        self.slider.set_value(vol)

    def on_change(self, wdg):
        self._main.mixer.set_volume(int(wdg.get_value()))
        # Force the tray icon to update
        self._main.icon.update()
        return True

    def __init__(self, main):
        super(MiniMixer, self).__init__(gtk.WINDOW_TOPLEVEL)
        self._main = main
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_position(gtk.WIN_POS_MOUSE)
        self.set_keep_above(True)
        self.set_border_width(5)
        # Main VBox
        vbox = gtk.VBox(0, 4)
        # Mixer Button
        btn_mixer = gtk.Button("Mixer")
        btn_mixer.connect('clicked', self.launch_mixer)
        vbox.pack_start(btn_mixer)
        # Separator
        vbox.pack_start(gtk.HSeparator())
        # Volume Slider
        self.slider = gtk.VScale()
        self.slider.set_range(0, 100)
        inc = self._main.config.mixer.increment
        self.slider.set_increments(inc, inc*2)
        self.slider.set_digits(0)
        self.slider.set_value_pos(gtk.POS_BOTTOM)
        self.slider.set_inverted(True)
        self.slider.set_size_request(0,120)
        vbox.pack_start(self.slider)
        # Control Name Label
        self.label = gtk.Label()
        vbox.pack_start(self.label)
        # Add main VBox to window
        self.add(vbox)
        # Update label and slider value
        self.update()
        # Connect after update() so we don't catch the signal(s) caused as a
        # result of update()'s call to set_value()
        self.slider.connect('value-changed', self.on_change)
        self.slider.grab_focus()
        self.show_all()
        self.present()

class TrayMenu(gtk.Menu):
    def on_about_click(self, item):
        dlg = gtk.AboutDialog()
        dlg.set_program_name("pyvolwheel")
        dlg.set_version(pyvolwheel.__version__)
        dlg.set_comments("Volume control tray icon")
        dlg.set_copyright(pyvolwheel.__copyright__)
        dlg.set_license(pyvolwheel.__license__)
        dlg.set_website(pyvolwheel.__url__)
        dlg.set_authors([pyvolwheel.__author__])
        dlg.set_logo_icon_name('multimedia-volume-control')
        # Website handler
        def launch_website(dialog, link):
            Popen(["xdg-open", link])
        gtk.about_dialog_set_url_hook(launch_website)
        # E-Mail handler
        def launch_email(dialog, address):
            Popen(["xdg-email", address])
        gtk.about_dialog_set_email_hook(launch_email)
        dlg.run()
        dlg.destroy()
        return True

    def on_prefs_click(self, item):
        ConfigDialog(self._main)
        return True

    def on_quit_click(self, _):
        gtk.main_quit()
        return True

    def __init__(self, main):
        super(TrayMenu, self).__init__()
        self._main = main
        item_prefs = gtk.ImageMenuItem('gtk-preferences')
        item_about = gtk.ImageMenuItem('gtk-about')
        item_sep1  = gtk.SeparatorMenuItem()
        item_quit  = gtk.ImageMenuItem('gtk-quit')
        self.append(item_prefs)
        self.append(item_about)
        self.append(item_sep1)
        self.append(item_quit)
        item_prefs.connect('activate', self.on_prefs_click)
        item_about.connect('activate', self.on_about_click)
        item_quit.connect('activate', self.on_quit_click)
        self.show_all()

class TrayIcon(gtk.StatusIcon):
    def update(self):
        try:
            control = self._main.mixer.get_control()
            volume = self._main.mixer.get_volume()[0]
            is_muted = self._main.mixer.get_mute()
        except mixer.MixerError as e:
            self.set_error(str(e))
        else:
            self.set_level(control, volume, is_muted)
        return True

    def reload(self):
        # Reset timer for new value in config
        if self._timeout is not None:
            gobject.source_remove(self._timeout)
        interval = self._main.config.mixer.update_interval
        self._timeout = gobject.timeout_add(interval, self.update)
        self.update()

    def set_error(self, tooltip):
        self.set_tooltip(tooltip)
        if self._last_icon != _error_icon:
            self.set_from_icon_name(_error_icon)
            self._last_icon = _error_icon

    def set_level(self, control, level, muted=False):
        if muted is True:
            self.set_tooltip("{0}: Muted".format(control))
            icon = _get_vol_icon(0)
        else:
            icon = _get_vol_icon(level)
            self.set_tooltip("{0}: {1}%".format(control, level))
        # Don't change the icon if it's already set to the one we want
        if self._last_icon != icon:
            self.set_from_icon_name(icon)
            self._last_icon = icon
        # Update the minimixer, if it's open
        if self.minimixer is not None:
            self.minimixer.update()

    def on_scroll(self, wdgt, event):
        if event.direction == gtk.gdk.SCROLL_UP:
            self._main.change_volume('up')
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            self._main.change_volume('down')
        else:
            return False
        return True

    def on_button_release(self, wdgt, event):
        if event.button == 2:   # Middle click
            self._main.toggle_mute()
            return True

    def on_mm_focus_out(self, wdgt, event):
        self.minimixer.destroy()
        self.minimixer = None
        pass

    def on_activate(self, wdgt):
        if self.minimixer is None:
            # Create it
            self.minimixer = MiniMixer(self._main)
            self.minimixer.connect('focus-out-event', self.on_mm_focus_out)
        else:
            # Destroy it >:)
            self.minimixer.destroy()
            del self.minimixer
            self.minimixer = None
        return False

    def __init__(self, main):
        super(TrayIcon, self).__init__()
        self._main = main
        self._last_icon = None
        self._timeout = None
        self.menu = TrayMenu(main)
        self.minimixer = None
        self.connect('activate', self.on_activate)
        self.connect('scroll-event', self.on_scroll)
        self.connect('button-release-event', self.on_button_release)
        def popup_menu(sicon, button, a_time):
            self.menu.popup(None, None, gtk.status_icon_position_menu,
                            button, a_time, sicon)
        self.connect('popup-menu', popup_menu)

# vim: filetype=python:et:sw=4:ts=4:sts=4:tw=79
