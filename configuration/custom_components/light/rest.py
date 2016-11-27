"""
Support for controlling RESTful lights (e.g., ESP8266 controlling RGBW LEDS
"""
import logging
import requests
import colorsys
import random

import voluptuous as vol

import homeassistant.util as util
import homeassistant.util.color as color_util
from homeassistant.const import (CONF_ID, CONF_NAME, CONF_RESOURCE, CONF_TIMEOUT)
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_EFFECT, ATTR_RGB_COLOR, ATTR_WHITE_VALUE,
    SUPPORT_BRIGHTNESS, SUPPORT_EFFECT, SUPPORT_RGB_COLOR, SUPPORT_WHITE_VALUE,
    EFFECT_RANDOM, Light, PLATFORM_SCHEMA)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.template import Template

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'rest'

ATTR_MODE = 'mode'
CONF_BODY_OFF = 'body_off'
CONF_BODY_ON = 'body_on'
DEFAULT_BODY_OFF = Template('OFF')
DEFAULT_BODY_ON = Template('ON')
DEFAULT_NAME = 'REST Switch'
DEFAULT_TIMEOUT = 10
CONF_IS_ON_TEMPLATE = 'is_on_template'

LIGHT_OFF = 0
LIGHT_ON = 1

LIGHT_COLOR = 0
LIGHT_WHITE = 1

SUPPORT_RESTLIGHT = (SUPPORT_BRIGHTNESS | SUPPORT_RGB_COLOR | SUPPORT_WHITE_VALUE)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_RESOURCE): cv.url,
    vol.Optional(CONF_BODY_OFF, default=DEFAULT_BODY_OFF): cv.template,
    vol.Optional(CONF_BODY_ON, default=DEFAULT_BODY_ON): cv.template,
    vol.Optional(CONF_ID): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_IS_ON_TEMPLATE): cv.template,
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
})


# pylint: disable=unused-argument,
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the RESTful light."""
    device_id = config.get(CONF_ID)
    name = config.get(CONF_NAME)
    resource = config.get(CONF_RESOURCE)
    body_on = config.get(CONF_BODY_ON)
    body_off = config.get(CONF_BODY_OFF)
    is_on_template = config.get(CONF_IS_ON_TEMPLATE)

    if is_on_template is not None:
        is_on_template.hass = hass
    if body_on is not None:
        body_on.hass = hass
    if body_off is not None:
        body_off.hass = hass
    timeout = config.get(CONF_TIMEOUT)

    try:
        requests.get(resource, timeout=10)
    except requests.exceptions.MissingSchema:
        _LOGGER.error("Missing resource or schema in configuration. Add http:// or https:// to your URL")
        return False
    except requests.exceptions.ConnectionError:
        _LOGGER.error("No route to resource/endpoint: %s", resource)
        return False

    add_devices(
        [RestLight(
            hass, device_id, name, resource, body_on, body_off, is_on_template, timeout)])


class RestLight(Light):
    """Representation of a light that can be controlled using REST."""

    def __init__(self, hass, device_id, name, resource, body_on, body_off, is_on_template, timeout):
        """Initialize the REST light."""
        self._state = None
        self._hass = hass
        self._id = device_id
        self._name = name
        self._resource = resource
        self._body_on = body_on
        self._body_off = body_off
        self._is_on_template = is_on_template
        self._timeout = timeout
        self.is_valid = True
        self._mode = None
        self._red = None
        self._green = None
        self._blue = None
        self._brightness = None
        self._white = None
        try:
            self.update()
        except Exception:
            self.is_valid = False
            _LOGGER.error(
                "Failed to initialize %s", self._id)

    #@property
    #def unique_id(self):
    #    """Return the ID of this light."""
    #    return "{}.{}".format(self.__class__, self._macaddr)

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def rgb_color(self):
        """Return the color property."""
        return (self._red, self._green, self._blue)

    @property
    def white_value(self):
        """Return the white value of this light between 0..255."""
        return self._white

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_RESTLIGHT

    def turn_on(self, **kwargs):
        """Turn the light on."""
        (red, green, blue) = (self._red, self._green, self._blue)
        brightness = self._brightness
        white = self._white

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
            self._mode = LIGHT_WHITE
        else:
            self._mode = LIGHT_COLOR

        hsv = colorsys.rgb_to_hsv(red, green, blue)
        rgb = tuple(int(i) for i in colorsys.hsv_to_rgb(hsv[0], hsv[1], brightness))

        payload = {'state': LIGHT_ON, 'mode': self._mode, 'color': {'red': rgb[0], 'green': rgb[1], 'blue': rgb[2]}, 'whitelevel': white}
        request = requests.post(self._resource, json=payload, timeout=self._timeout)
        if request.status_code == 200:
            self._state = LIGHT_ON
        else:
            _LOGGER.error("Can't turn on %s. Is resource/endpoint offline?", self._resource)

        #hsv = colorsys.rgb_to_hsv(self._bulb._red, self._bulb._green, self._bulb._blue)
        #self._brightness = hsv[2]


    def turn_off(self, **kwargs):
        """Turn the light off."""
        payload = {'state': LIGHT_OFF, 'mode': self._mode, 'color': {'red': self._red, 'green': self._green, 'blue': self._blue}, 'whitelevel': self._white}
        request = requests.post(self._resource, json=payload, timeout=self._timeout)
        if request.status_code == 200:
            self._state = LIGHT_OFF
        else:
            _LOGGER.error("Can't turn off %s. Is resource/endpoint offline?", self._resource)

        #hsv = colorsys.rgb_to_hsv(self._bulb._red, self._bulb._green, self._bulb._blue)
        #self._brightness = hsv[2]


    def update(self):
        """Get the latest data from REST API and update the state."""
        request = requests.get(self._resource, timeout=self._timeout)
        json = request.json()

        self._state = json['state']
        self._mode = json['mode']
        self._red = json['color']['red']
        self._green = json['color']['green']
        self._blue = json['color']['blue']
        self._white = json['whitelevel']

        hsv = colorsys.rgb_to_hsv(self._red, self._green, self._blue)
        self._brightness = hsv[2]
