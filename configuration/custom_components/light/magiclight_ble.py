"""
Support for controlling MagicLight BLE/Bluetooth Smart light bulbs
"""
import logging
import colorsys
import random

import voluptuous as vol

import homeassistant.util as util
import homeassistant.util.color as color_util
from homeassistant.const import CONF_DEVICES, CONF_ID, CONF_NAME
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_EFFECT, ATTR_RGB_COLOR, ATTR_WHITE_VALUE,
    SUPPORT_BRIGHTNESS, SUPPORT_EFFECT, SUPPORT_RGB_COLOR, SUPPORT_WHITE_VALUE,
    EFFECT_RANDOM, Light, PLATFORM_SCHEMA)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['git+https://github.com/sbardua/MagicLightBLE.git@develop#magiclightble==0.0.1']

_LOGGER = logging.getLogger(__name__)

ATTR_MODE = 'mode'

DOMAIN = 'magiclight_ble'

SUPPORT_MAGICLIGHT_BLE = (SUPPORT_BRIGHTNESS | SUPPORT_RGB_COLOR | SUPPORT_WHITE_VALUE)

DEVICE_SCHEMA = vol.Schema({
    vol.Optional(CONF_ID): cv.string,
    vol.Optional(CONF_NAME): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_DEVICES, default={}): {cv.string: DEVICE_SCHEMA},
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the MagicLight lights."""
    lights = []
    for macaddr, device_config in config[CONF_DEVICES].items():
        device = {}
        device['id'] = device_config[CONF_ID]
        device['name'] = device_config[CONF_NAME]
        device['macaddr'] = macaddr
        light = MagicLight(device)
        if light.is_valid:
            lights.append(light)

    add_devices(lights)
    return


class MagicLight(Light):
    """Representation of a MagicLight light."""

    def __init__(self, device):
        """Initialize the light."""
        from magiclightble.magiclightble import MagicLightBLE

        self._id = device['id']
        self._name = device['name']
        self._macaddr = device['macaddr']
        self.is_valid = True
        self._bulb = None
        self._brightness = None
        try:
            self._bulb = MagicLightBLE(self._macaddr)
            self.update()
        except Exception:
            self.is_valid = False
            _LOGGER.error(
                "Failed to initialize %s, %s", self._macaddr, self._id)

    @property
    def unique_id(self):
        """Return the ID of this light."""
        return "{}.{}".format(self.__class__, self._macaddr)

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._bulb._power_on

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def rgb_color(self):
        """Return the color property."""
        return (self._bulb._red, self._bulb._green, self._bulb._blue)

    @property
    def white_value(self):
        """Return the white value of this light between 0..255."""
        return self._bulb._white

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_MAGICLIGHT_BLE

    def turn_on(self, **kwargs):
        """Turn the specified or all lights on."""
        self._bulb.connect()

        if not self.is_on:
            self._bulb.turn_on()

        (red, green, blue) = (self._bulb._red, self._bulb._green, self._bulb._blue)
        brightness = self._brightness
        white = self._bulb._white

        if ATTR_RGB_COLOR in kwargs:
            red = kwargs[ATTR_RGB_COLOR][0]
            green = kwargs[ATTR_RGB_COLOR][1]
            blue = kwargs[ATTR_RGB_COLOR][2]
            #_LOGGER.info("RGB: %d, %d, %d", red, green, blue)

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            #_LOGGER.info("Brightness: %d", brightness)

        if ATTR_WHITE_VALUE in kwargs:
            white = kwargs[ATTR_WHITE_VALUE]
            #_LOGGER.info("White: %d", white)

        if ATTR_WHITE_VALUE in kwargs:
            self._bulb.set_white(white)
        else:
            hsv = colorsys.rgb_to_hsv(red, green, blue)
            rgb = tuple(int(i) for i in colorsys.hsv_to_rgb(hsv[0], hsv[1], brightness))
            self._bulb.set_color(rgb[0], rgb[1], rgb[2])

        self._bulb.get_status()
        hsv = colorsys.rgb_to_hsv(self._bulb._red, self._bulb._green, self._bulb._blue)
        self._brightness = hsv[2]
        self._bulb.disconnect()

    def turn_off(self, **kwargs):
        """Turn the specified or all lights off."""
        self._bulb.connect()

        if self.is_on:
            self._bulb.turn_off()

        self._bulb.get_status()
        hsv = colorsys.rgb_to_hsv(self._bulb._red, self._bulb._green, self._bulb._blue)
        self._brightness = hsv[2]
        self._bulb.disconnect()

    def update(self):
        """Synchronize state with bulb."""
        self._bulb.connect()
        self._bulb.get_status()
        hsv = colorsys.rgb_to_hsv(self._bulb._red, self._bulb._green, self._bulb._blue)
        self._brightness = hsv[2]
        self._bulb.disconnect()
