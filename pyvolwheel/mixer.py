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
    if driver not in available_drivers:
        raise MixerError("Invalid driver: '{0}'".format(str(driver)))
    if driver == 'ALSA':
        return alsaaudio.cards()
    elif driver == 'OSS':
        # If AUDIODEV is not set, we filter it from the list
        return [x for x in [os.getenv('AUDIODEV'), "/dev/mixer"]
                if x is not None]

def get_controls(driver, device):
    """Return a list of available controls on the device"""
    if driver not in available_drivers:
        raise MixerError("Invalid driver: '{0}'".format(str(driver)))
    if driver == "ALSA":
        # Convert device to index
        dev = _alsa_device_to_idx(device)
        # Filter out the controls that can't control the volume
        valid = []
        for c in alsaaudio.mixers():
            try:
                m = alsaaudio.Mixer(c, cardindex=dev)
                if len(m.volumecap()) > 0:
                    valid.append(c)
                m.close()
            except alsaaudio.ALSAAudioError:
                pass
        return valid
    elif driver == "OSS":
        try:
            om = ossaudiodev.openmixer(device)
        except (IOError, ossaudiodev.OSSAudioError) as oe:
            raise MixerError("Error opening mixer: {0}".format(str(oe)))
        bitmask = om.controls()
        om.close()
        # Filter out unavailable controls
        return [ossaudiodev.control_labels[c].rstrip() for
                c in range(len(ossaudiodev.control_labels))
                if bitmask & (1 << c)]

def open_mixer(driver, device, control):
    if driver not in available_drivers:
        raise MixerError("Invalid driver: '{0}'".format(str(driver)))
    elif driver == 'ALSA':
        return ALSAMixer(device, control)
    elif driver == 'OSS':
        return OSSMixer(device, control)

class Mixer(object):
    def __init__(self):
        self._mixer = None
        self._mute_cache = None

    def __del__(self):
        self.close()

    def _check_mixer(self):
        if self._mixer is None:
            raise MixerError("Device is closed")

    def close(self):
        if self._mixer is not None:
            self._mixer.close()
            self._mixer = None

    def _set_fake_mute(self, flag):
        # Muting for controls that don't support it
        if flag is True:
            # Mute
            # If the channel has already been muted, we return so we don't
            # overwrite the mute cache with the muted values (0)
            if self.get_mute() is True: return
            last_vol = self.get_volume()
            self.set_volume(0)
            self._mute_cache = last_vol
        elif flag is False:
            # Unmute
            # That which is not muted cannot be unmuted
            if self.get_mute() is False: return
            # We only use the value of the first channel
            premute_vol = self._mute_cache[0]
            self._mute_cache = None
            self.set_volume(premute_vol)

    def _get_fake_mute(self):
        if self._mute_cache is None:
            return False
        else:
            return True

if 'ALSA' in available_drivers:
    def _alsa_device_to_idx(device):
        if isinstance(device, str):
            # If device (card) is a string, try to match it to it's index
            try:
                idx = get_devices('ALSA').index(device)
            except ValueError:
                # Raise a more helpful error
                raise MixerError("Invalid device '{0}'".format(str(device)))
        # If device is an int, assume it's a control index
        elif isinstance(device, int):
            idx = device
        else:
            raise MixerError("Invalid device '{0}'".format(str(device)))
        return idx

    class ALSAMixer(Mixer):
        """A very simple ALSA mixer class"""
        def __init__(self, device=0, control=None):
            Mixer.__init__(self)
            self._device = _alsa_device_to_idx(device)
            self._control = control
            # Try to open the mixer
            try:
                self._mixer = alsaaudio.Mixer(control, cardindex=self._device)
            except alsaaudio.ALSAAudioError as ae:
                raise MixerError("Error opening mixer: {0}".format(str(ae)))

        def get_device(self):
            #self._check_mixer()
            return get_devices('ALSA')[self._device]

        def get_control(self):
            return self._control

        def get_volume(self):
            self._check_mixer()
            return self._mixer.getvolume()

        def set_volume(self, volume):
            self._check_mixer()
            volume = _clamp(volume)
            self._mixer.setvolume(volume)

        def change_volume(self, delta):
            self._check_mixer()
            cur_vol = self._mixer.getvolume()
            self._mixer.setvolume(_clamp(cur_vol[0] + delta))

        def get_mute(self):
            self._check_mixer()
            try:
                mute = bool(self._mixer.getmute()[0])
            except alsaaudio.ALSAAudioError:
                mute = self._get_fake_mute()
            return mute

        def set_mute(self, flag):
            if not isinstance(flag, bool): return
            self._check_mixer()
            try:
                self._mixer.setmute(int(flag))
            except alsaaudio.ALSAAudioError:
                # Assume the control doesn't support muting, so fake it
                self._set_fake_mute(flag)

if 'OSS' in available_drivers:
    class OSSMixer(Mixer):
        """A very simple OSS mixer class"""
        def __init__(self, device=None, control='Vol'):
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
            # Set the control
            self._control = control
            self._control_idx = self._control_to_idx(control)

        def _control_to_idx(self, control):
            """Returns the integer value of the control string"""
            self._check_mixer()
            bitmask = self._mixer.controls()
            # Filter out unavailable controls & convert to lowercase for
            # comparison
            ctrls = [ossaudiodev.control_labels[c].rstrip().lower() for
                     c in range(len(ossaudiodev.control_labels))
                     if bitmask & (1 << c)]
            if control.lower() in ctrls:
                return ctrls.index(control.lower())
            else:
                raise MixerError("Invalid control '{0}'".format(str(control)))

        def get_device(self):
            return self._device

        def get_control(self):
            return self._control

        def get_volume(self):
            self._check_mixer()
            if self._mute_cache is not None:
                return self._mute_cache
            try:
                vol = self._mixer.get(self._control_idx)
            except ossaudiodev.OSSAudioError as e:
                raise MixerError(str(e))
            return vol

        def set_volume(self, volume):
            self._check_mixer()
            volume = _clamp(volume)
            # If the control is muted, update the mute cache and return
            if self._mute_cache is not None:
                self._mute_cache = (volume, volume)
                return
            try:
                self._mixer.set(self._control_idx, (volume, volume))
            except ossaudiodev.OSSAudioError as e:
                raise MixerError(str(e))

        def change_volume(self, delta):
            self._check_mixer()
            # If the control is muted, update the mute cache and return
            if self._mute_cache is not None:
                cur_vol = self._mute_cache
                self._mute_cache = (_clamp(cur_vol[0] + delta),
                                    _clamp(cur_vol[1] + delta))
                return
            cur_vol = self.get_volume()
            try:
                self._mixer.set(self._control_idx,(_clamp(cur_vol[0] + delta),
                                                   _clamp(cur_vol[1] + delta)))
            except ossaudiodev.OSSAudioError as e:
                raise MixerError(str(e))

        def set_mute(self, flag):
            self._check_mixer()
            self._set_fake_mute(flag)

        def get_mute(self):
            self._check_mixer()
            return self._get_fake_mute()

def _clamp(val, min=0, max=100):
    if val < min: return min
    if val > max: return max
    return val

# vim: filetype=python:et:sw=4:ts=4:sts=4:tw=79
