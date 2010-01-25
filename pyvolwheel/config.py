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
import ConfigParser

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
         super(AttrDict, self).__init__(*args, **kwargs)
    def __getattr__(self, name):
         return self[name]
    def __setattr__(self, name, value):
         self[name] = value

# Default settings if no valid setting is given in the config file
# Format:
# {'section':
#   {'option': default_value,
#   ...
# {'section':
#   ...
_DefaultSettings = {'mixer':
            AttrDict({'driver':          None,
                      'device':          None,
                      'control':         None,
                      'increment':       3,
                      'external':        "xterm -e 'alsamixer'",
                      'update_interval': 1000}),
                    'restore':
            AttrDict({'enabled':   False,
                      'level':     0,
                      'muted':     False}),
                    'hotkeys':
            AttrDict({'enabled':   True,
                      'up':     "XF86AudioRaiseVolume",
                      'down':     "XF86AudioLowerVolume",
                      'mute':      "XF86AudioMute"})}

# If the env. variable XDG_CONFIG_HOME is set, use it for the config directory,
# otherwise, default to ~/.config
_xdg_config_home = os.getenv('XDG_CONFIG_HOME',
                             os.path.join(os.path.expanduser("~"), ".config"))
# Default: $XDG_CONFIG_HOME/pyvolwheel
_default_config_path = os.path.join(_xdg_config_home, "pyvolwheel")

class Config(AttrDict):
    def __init__(self, path=None):
        if path is None: path = _default_config_path
        self.__dict__['_path'] = path   # Avoids AttrDict.__setattr__
        super(Config, self).__init__()
        # Load
        self.load()

    def load(self, path=None):
        if path is None: path = self._path
        parser = ConfigParser.RawConfigParser()
        #try:
        # Make sure the parser can load the file okay before we clobber the
        # current settings.
        parser.read(path)
        #except ConfigParser.ParsingError as e:
        #    pass
        #self._path = path
        self.__dict__['_path'] = path
        self.clear()
        for sect,opts in _DefaultSettings.iteritems():
            self[sect] = AttrDict()
            for opt, default in opts.iteritems():
                try:
                    # If the config doesn't contain the current section, all the
                    # options in the section will be set to their defaults
                    if not parser.has_section(sect):
                        value = default
                    elif isinstance(default, bool):
                        value = parser.getboolean(sect, opt)
                    elif isinstance(default, int):
                        value = parser.getint(sect, opt)
                    elif isinstance(default, float):
                        value = parser.getfloat(sect, opt)
                    else:
                        value = parser.get(sect, opt)
                        if default is None and value == 'None':
                            value = None
                # If anything went wrong, use the default
                except (ConfigParser.NoOptionError,
                        ConfigParser.NoSectionError, ValueError):
                    value = default
                self[sect][opt] = value
        return self

    def save(self, path=None):
        # If using the default path, make sure the XDG_CONFIG_HOME directory exists
        # If not, create it first
        if path is None: path = self._path
        if path == _default_config_path and not os.path.isdir(_xdg_config_home):
            os.makedirs(_xdg_config_home, mode=0700)
        parser = ConfigParser.RawConfigParser()
        for sect,opts in self.iteritems():
            parser.add_section(sect)
            for opt, value in opts.iteritems():
                parser.set(sect, opt, value)
        with open(path, 'w') as f:
            parser.write(f)
        #self._path = path
        self.__dict__['_path'] = path
        return self

# vim: filetype=python:et:sw=4:ts=4:sts=4:tw=79
