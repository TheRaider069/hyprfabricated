import os
import json
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib  # noqa: E402
from fabric.utils.helpers import get_relative_path  # noqa: E402


gi.require_version("Gtk", "3.0")

APP_NAME = "hyprfabricated"
APP_NAME_CAP = "hyprfabricated"

CACHE_DIR = str(GLib.get_user_cache_dir()) + f"/{APP_NAME}"

USERNAME = os.getlogin()
HOSTNAME = os.uname().nodename
HOME_DIR = os.path.expanduser("~")

CONFIG_DIR = os.path.expanduser(f"~/.config/{APP_NAME}")

screen = Gdk.Screen.get_default()
CURRENT_WIDTH = screen.get_width()
CURRENT_HEIGHT = screen.get_height()

# Rename to match what's being imported in config.py
WALLPAPERS_DIR_DEFAULT = get_relative_path("../assets/wallpapers_example")
CONFIG_FILE = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/config.json")


# Default value for the new setting
BAR_WORKSPACE_USE_CHINESE_NUMERALS = False


def load_config():
    """Load the configuration from config.json"""
    config_path = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/config.json")
    config = {}

    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")

    return config


if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    WALLPAPERS_DIR = config.get("wallpapers_dir", WALLPAPERS_DIR_DEFAULT)
    VERTICAL = config.get("vertical", False)  # Use saved value or False as default
    CENTERED_BAR = config.get("centered_bar", False)  # Load centered bar setting
    TERMINAL_COMMAND = config.get(
        "terminal_command", "kitty -e"
    )  # Load terminal command
    DOCK_ENABLED = config.get("dock_enabled", True)  # Load dock visibility setting
    DOCK_ALWAYS_OCCLUDED = config.get(
        "dock_always_occluded", False
    )  # Load dock hover-only setting
    DOCK_ICON_SIZE = config.get("dock_icon_size", 28)  # Load dock icon size setting
    UPDATER = config.get("misc_updater", True)
    OTHERPLAYERS = config.get("misc_otherplayers", False)

    DESKTOP_WIDGETS = config.get("bar_desktop_widgets_visible", True)
    WEATHER_FORMAT = config.get("widgets_weather_format", "C")
    WEATHER_LOCATION = config.get("widgets_weather_location", "")
    QUOTE_TYPE = config.get("widgets_quotetype", "stoic")
    BAR_WORKSPACE_SHOW_NUMBER = config.get(
        "bar_workspace_show_number", False
    )  # Load workspace number visibility
    BAR_WORKSPACE_USE_CHINESE_NUMERALS = config.get(
        "bar_workspace_use_chinese_numerals", False
    )  # Load Chinese numeral setting
    # Load bar component visibility settings
    BAR_COMPONENTS_VISIBILITY = {
        "button_apps": config.get("bar_button_apps_visible", True),
        "systray": config.get("bar_systray_visible", True),
        "control": config.get("bar_control_visible", True),
        "network": config.get("bar_network_visible", True),
        "button_tools": config.get("bar_button_tools_visible", True),
        "button_overview": config.get("bar_button_overview_visible", True),
        "ws_container": config.get("bar_ws_container_visible", True),
        "weather": config.get("bar_weather_visible", False),
        "battery": config.get("bar_battery_visible", True),
        "metrics": config.get("bar_metrics_visible", False),
        "language": config.get("bar_language_visible", False),
        "date_time": config.get("bar_date_time_visible", True),
        "sysprofiles": config.get("bar_sysprofiles_visible", False),
        "button_power": config.get("bar_button_power_visible", True),
        "displaytype": config.get("widgets_displaytype_visible", True),
        "activation": config.get("widgets_activation_visible", False),
        "date": config.get("widgets_date_visible", True),
        "clock": config.get("widgets_clock_visible", True),
        "quote": config.get("widgets_quote_visible", True),
        "weatherwid": config.get("widgets_weather_visible", True),
        "sysinfo": config.get("widgets_sysinfo_visible", True),
    }

    BAR_METRICS_DISKS = config.get("bar_metrics_disks", ["/"])
    METRICS_VISIBLE = config.get(
        "metrics_visible", {"cpu": True, "ram": True, "disk": True, "gpu": True}
    )
    METRICS_SMALL_VISIBLE = config.get(
        "metrics_small_visible", {"cpu": True, "ram": True, "disk": True, "gpu": True}
    )
else:
    WALLPAPERS_DIR = WALLPAPERS_DIR_DEFAULT
    VERTICAL = False  # Default value when no config exists
    CENTERED_BAR = False  # Default value for centered bar
    DOCK_ENABLED = True  # Default value for dock visibility
    DOCK_ALWAYS_OCCLUDED = False  # Default value for dock hover-only mode
    TERMINAL_COMMAND = "ghostty -e"  # Default terminal command when no config
    DOCK_ICON_SIZE = 28  # Default dock icon size when no config
    UPDATER = True
    OTHERPLAYERS = False
    DESKTOP_WIDGETS = True
    WEATHER_FORMAT = "C"
    WEATHER_LOCATION = ""

    QUOTE_TYPE = "stoic"
    BAR_WORKSPACE_SHOW_NUMBER = False  # Default workspace number visibility
    BAR_WORKSPACE_USE_CHINESE_NUMERALS = False  # Default Chinese numeral setting

    # Default values for component visibility (all visible)
    BAR_COMPONENTS_VISIBILITY = {
        "button_apps": True,
        "systray": True,
        "control": True,
        "network": True,
        "button_tools": True,
        "button_overview": True,
        "ws_container": True,
        "weather": False,
        "battery": True,
        "metrics": False,
        "language": False,
        "date_time": True,
        "button_power": True,
        "displaytype": True,
        "activation": False,
        "date": True,
        "clock": True,
        "quote": True,
        "weatherwid": True,
        "sysinfo": True,
        "sysprofiles": False,
    }

    BAR_METRICS_DISKS = ["/"]
    METRICS_VISIBLE = {"cpu": True, "ram": True, "disk": True, "gpu": True}
    METRICS_SMALL_VISIBLE = {"cpu": True, "ram": True, "disk": True, "gpu": True}
