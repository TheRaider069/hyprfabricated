import os
import subprocess
import setproctitle
from fabric import Application
from fabric.utils import exec_shell_command_async, get_relative_path
from config.data import (
    APP_NAME,
    APP_NAME_CAP,
    CACHE_DIR,
    CONFIG_FILE,
    DOCK_ICON_SIZE,
    HOME_DIR,
    VERTICAL,
    UPDATER,
    DESKTOP_WIDGETS,
)
from modules.bar import Bar
from modules.corners import Corners
from modules.dock import Dock
from modules.notch import Notch
from modules.deskwidgets import Deskwidgets

fonts_updated_file = f"{CACHE_DIR}/fonts_updated"
hyprconf = get_relative_path("config.json")


def run_updater():
    try:
        subprocess.Popen(
            f"python {HOME_DIR}/.config/{APP_NAME_CAP}/modules/updater.py",
            shell=True,
            start_new_session=True,
        )
        print("Updater process restarted.")
    except Exception as e:
        print(f"Error restarting Updater process: {e}")


if __name__ == "__main__":
    setproctitle.setproctitle(APP_NAME)

    if not os.path.isfile(CONFIG_FILE):
        exec_shell_command_async(f"python {get_relative_path('../config/config.py')}")

    current_wallpaper = os.path.expanduser("~/.current.wall")
    if not os.path.exists(current_wallpaper):
        example_wallpaper = os.path.expanduser(
            f"~/.config/{APP_NAME_CAP}/assets/wallpapers_example/example-1.jpg"
        )
        os.symlink(example_wallpaper, current_wallpaper)

    from config.data import load_config

    config = load_config()

    if UPDATER:
        run_updater()

    corners = Corners()
    bar = Bar()
    notch = Notch()
    dock = Dock()
    bar.notch = notch
    notch.bar = bar
    widgets = Deskwidgets()
    # Set corners visibility based on config

    widgetsvisible = DESKTOP_WIDGETS
    widgets.set_visible(widgetsvisible)
    corners_visible = config.get("corners_visible", True)
    corners.set_visible(corners_visible)

    app = Application(
        f"{APP_NAME}", bar, notch, dock, corners, widgets
    )  # Make sure corners is added to the app

    def set_css():
        from config.data import CURRENT_HEIGHT, CURRENT_WIDTH

        app.set_stylesheet_from_file(
            get_relative_path("main.css"),
            exposed_functions={
                "overview_width": lambda: f"min-width: {CURRENT_WIDTH * 0.1 * 5 + 92}px;",
                "overview_height": lambda: f"min-height: {CURRENT_HEIGHT * 0.1 * 2 + 32 + 64}px;",
                "dock_nmargin": lambda: (
                    f"margin-bottom: -{32 + DOCK_ICON_SIZE}px;"
                    if not VERTICAL
                    else f"margin-right: -{32 + DOCK_ICON_SIZE}px;"
                ),
                "ws_width": lambda: (
                    "min-width: 48px;" if not VERTICAL else "min-width: 8px;"
                ),
                "ws_height": lambda: (
                    "min-height: 8px;" if not VERTICAL else "min-height: 48px;"
                ),
                "dock_sep": lambda: (
                    "margin: 8px 0;" if not VERTICAL else "margin: 0 8px;"
                ),
            },
        )

    app.set_css = set_css

    app.set_css()
    app.run()
