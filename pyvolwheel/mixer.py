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

import os
# Try importing the driver modules
available_drivers = []
try:
    import ossaudiodev
    available_drivers.append('OSS')
except ImportError:
    pass
try:
    import alsaaudio
    available_drivers.append('ALSA')
except ImportError:
    pass

# Exception classes
class MixerError(Exception):
    pass

def get_drivers():
    """Return a list of available drivers"""
    return available_drivers

def get_devices(driver):
    """Return a list if valid devices for the given driver"""
    if driver == 'ALSA':
        return alsaaudio.cards()
    elif driver == 'OSS':
        # If AUDIODEV is not set, we filter it from the list
        return [x for x in [os.getenv('AUDIODEV'), "/dev/mixer"]
                if x is not None]
    else:
        raise MixerError("Invalid driver '{0}'".format(str(driver)))

def get_available_dict():
    """Returns a dict containing all of the available drivers, devices and
    controls.
    
    Format: Each driver contains a dictionary of the available devices for
    that driver. Each device contains a list of available controls for that
    device.

    Example: {'OSS':
              {'/dev/mixer':
               ['Vol', 'Pcm', ...]
             {'ALSA':
              {'UART':
               ['Master', 'Master Mono', ...]

    """
    lst = {}
    for driver in get_drivers():
        lst[driver] = {}
        for dev in get_devices(driver):
            lst[driver][dev] = []
            for cntrl in open_mixer(driver, dev).get_controls():
                lst[driver][dev].append(cntrl)
    return lst

def open_mixer(driver, device=None):
    """Factory function that returns an instance for the given driver"""
    if driver not in available_drivers:
        raise MixerError("Invalid driver: '{0}'".format(str(driver)))
    elif driver == 'ALSA':
        return ALSAMixer(device)
    elif driver == 'OSS':
        return OSSMixer(device)

class Mixer(object):
    def __init__(self):
        self._mixer = None
        self._mute_cache = {}

    def __del__(self):
        self.close()

    def _check_mixer(self):
        """Make sure the mixer isn't closed."""
        if self._mixer is None:
            raise MixerError("Device is closed")

    def close(self):
        """Closes the mixer device."""
        if self._mixer is not None:
            self._mixer.close()
            self._mixer = None

    def _set_fake_mute(self, control, flag):
        # Muting for controls that don't support it
        if flag is True:
            # Mute
            # If the channel has already been muted, we return so we don't
            # overwrite the mute cache with the muted values (0)
            if self.get_mute(control) is True: return
            self._mute_cache[control] = self.get_volume(control)
            self.set_volume(control, 0)
        elif flag is False:
            # Unmute
            # That which is not muted cannot be unmuted
            if self.get_mute(control) is False: return
            # We only use the value of the first channel
            self.set_volume(control, self._mute_cache[control][0])
            del self._mute_cache[control]

    def _get_fake_mute(self, control):
        if control in self._mute_cache:
            return True
        else:
            return False

if 'ALSA' in available_drivers:
    class ALSAMixer(Mixer):
        """A very simple ALSA mixer class"""
        def __init__(self, device=None):
            Mixer.__init__(self)
            if isinstance(device, str):
                # If device (card) is a string, try to match it to it's index
                try:
                    self._device = get_devices('ALSA').index(device)
                except ValueError:
                    # Raise a more helpful error
                    raise MixerError("Invalid device '{0}'".format(str(device)))
            # If device is an int, assume it's a control index
            elif isinstance(device, int):
                self._device = device
            else:
                # Otherwise default to the first card.
                self._device = 0

        def _switch_control(self, control='Master'):
            if self._mixer is not None:
                # If the mixer is already opened for the given control, we don't
                # need to do anything
                # We need to reopen the mixer before calling getvolume() even
                # if the mixer is already open for the given control. This is
                # because getvolume() will return incorrect values if another
                # program changes the volume. 
                # if control == self._mixer.mixer(): return
                self._mixer.close()
                del self._mixer
                self._mixer = None
            try:
                self._mixer = alsaaudio.Mixer(control, cardindex=self._device)
            except alsaaudio.ALSAAudioError as ae:
                raise MixerError("Error opening mixer: {0}".format(str(ae)))

        def get_device(self):
            """Return the currently controlled device."""
            #self._check_mixer()
            return get_devices('ALSA')[self._device]

        def get_controls(self):
            """Return a list of controls on the device"""
            #self._check_mixer()
            # Filter out the controls that can't control the volume
            valid = []
            for c in alsaaudio.mixers(self._device):
                m = alsaaudio.Mixer(c, cardindex=self._device)
                if len(m.volumecap()) > 0:
                    valid.append(c)
                m.close()
            return valid
        
        def get_volume(self, control):
            self._switch_control(control)
            self._check_mixer()
            return self._mixer.getvolume()
        
        def set_volume(self, control, volume):
            """Set the volume of the control"""
            self._switch_control(control)
            self._check_mixer()
            volume = _clamp(volume)
            self._mixer.setvolume(volume)

        def change_volume(self, control, delta):
            """Increase or decrease the volume of the control by delta"""
            self._switch_control(control)
            self._check_mixer()
            cur_vol = self._mixer.getvolume()
            self._mixer.setvolume(_clamp(cur_vol[1] + delta))

        def set_mute(self, control, flag):
            """Mute/Unmute the control (True/False)"""
            if not isinstance(flag, bool): return
            self._switch_control(control)
            self._check_mixer()
            try:
                self._mixer.setmute(int(flag))
            except alsaaudio.ALSAAudioError:
                self._set_fake_mute(control, flag)

        def get_mute(self, control):
            """Returns whether the control is muted or not."""
            self._switch_control(control)
            self._check_mixer()
            try:
                mute = bool(self._mixer.getmute()[0])
            except alsaaudio.ALSAAudioError:
                mute = self._get_fake_mute(control)
            return mute

if 'OSS' in available_drivers:
    class OSSMixer(Mixer):
        """A very simple OSS mixer class"""
        def __init__(self, device=None):
            Mixer.__init__(self)
            if device is None:
                # If no device is given, use the first one on the device list
                self._device = get_devices('OSS')[0]
            elif isinstance(device, str):
                self._device = device
            else:
                raise ValueError("Invalid device '{0}'".format(str(device)))
            # Try to open the mixer
            try:
                self._mixer = ossaudiodev.openmixer(self._device)
            except (IOError, ossaudiodev.OSSAudioError) as oe:
                raise MixerError("Error opening mixer: {0}".format(str(oe)))

        def get_device(self):
            """Returns the currently controlled device."""
            self._check_mixer()
            return self._device
        
        def get_controls(self):
            """Returns a list of controls on the device"""
            self._check_mixer()
            ctrl_list = []
            bitmask = self._mixer.controls()
            # Convert the bitmask into it's string components
            return [ossaudiodev.control_labels[c].rstrip()
                     for c in range(len(ossaudiodev.control_labels))
                     if bitmask & (1 << c)]

        def _control_to_id(self, control):
            """Returns the integer value of the control string"""
            labels = [x.lower() for x in self.get_controls()]
            if control.lower() in labels:
                return labels.index(control.lower())
            else:
                raise MixerError("Invalid control '{0}'".format(str(control)))

        def get_volume(self, control):
            """Returns a list of the current values of each channel"""
            self._check_mixer()
            try:
                vol = self._mixer.get(self._control_to_id(control))
            except ossaudiodev.OSSAudioError as e:
                raise MixerError(str(e))
            return vol

        def set_volume(self, control, volume):
            """Set the volume of the control"""
            self._check_mixer()
            volume = _clamp(volume)
            try:
                self._mixer.set(self._control_to_id(control), (volume, volume))
            except ossaudiodev.OSSAudioError as e:
                raise MixerError(str(e))

        def change_volume(self, control, delta):
            """Increase or decrease the volume of the control by delta"""
            self._check_mixer()
            cur_vol = self.get_volume(control)
            try:
                self._mixer.set(self._control_to_id(control),
                        (_clamp(cur_vol[0] + delta), _clamp(cur_vol[1] + delta)))
            except ossaudiodev.OSSAudioError as e:
                raise MixerError(str(e))

        def set_mute(self, control, flag):
            """Mute/Unmute the control (True/False)"""
            self._check_mixer()
            self._set_fake_mute(control, flag)

        def get_mute(self, control):
            """Returns whether the control is muted or not."""
            self._check_mixer()
            return self._get_fake_mute(control)

def _clamp(val, min=0, max=100):
    if val < min: return min
    if val > max: return max
    return val

# vim: filetype=python:et:sw=4:ts=4:sts=4:tw=79
