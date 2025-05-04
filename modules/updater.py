import os
import json
import subprocess
import shutil
import threading
import gi
import sys
from pathlib import Path
import socket

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fabric.utils.helpers import get_relative_path
import config.data as data

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

# File locations
VERSION_FILE = get_relative_path("../utils/version.json")
REMOTE_VERSION_FILE = "/tmp/remote_version.json"
REMOTE_URL = "https://raw.githubusercontent.com/tr1xem/hyprfabricated/refs/heads/main/utils/version.json"
REPO_DIR = get_relative_path("../")


# Fetch the remote version file using wget (or use curl)
def fetch_remote_version():
    subprocess.run(["wget", "-q", "-O", REMOTE_VERSION_FILE, REMOTE_URL], check=False)


# Read local version
def get_local_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            data = json.load(f)
            return data.get("version", "0.0.0"), data.get("changelog", [])
    return "0.0.0", []


# Read remote version
def get_remote_version():
    if os.path.exists(REMOTE_VERSION_FILE):
        with open(REMOTE_VERSION_FILE, "r") as f:
            data = json.load(f)
            return (
                data.get("version", "0.0.0"),
                data.get("changelog", []),
                data.get("download_url", "#"),
            )
    return "0.0.0", [], "#"


# Replace local version file with remote version file
def update_local_version():
    if os.path.exists(REMOTE_VERSION_FILE):
        shutil.move(REMOTE_VERSION_FILE, VERSION_FILE)


def update_local_repo(progress_callback):
    subprocess.run(["git", "stash"], cwd=REPO_DIR, check=False)

    process = subprocess.Popen(
        ["git", "pull"],
        cwd=REPO_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    for line in process.stdout:
        progress_callback(line)
    process.wait()

    subprocess.run(["git", "stash", "apply"], cwd=REPO_DIR, check=False)


# Kill processes
def kill_processes():
    subprocess.run(["pkill", "hyprfabricated"], check=False)
    subprocess.run(["pkill", "cava"], check=False)


# Run a command in a disowned manner
def run_disowned_command():
    try:
        subprocess.Popen(
            f"killall {data.APP_NAME}; uwsm app -- python {data.HOME_DIR}/.config/{data.APP_NAME_CAP}/main.py",
            shell=True,
            start_new_session=True,
        )
        print("Hyprfabricated process restarted.")
    except Exception as e:
        print(f"Error restarting Hyprfabricated process: {e}")


# GTK window for updates
class UpdateWindow(Gtk.Window):
    def __init__(self, latest_version, changelog):
        super().__init__(title="Update Available")
        self.set_default_size(500, 450)
        self.set_resizable(False)

        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_border_width(10)
        self.add(vbox)

        title_label = Gtk.Label(label="HYPRFABRICATED UPDATER")
        title_label.set_xalign(0.5)
        title_label.set_markup(
            "<span size='xx-large' weight='bold'>HYPRFABRICATED UPDATER</span>"
        )
        vbox.pack_start(title_label, False, False, 0)

        label = Gtk.Label(label=f"A new version {latest_version} is available!")
        label.set_xalign(0)
        vbox.pack_start(label, False, False, 0)

        changelog_label = Gtk.Label(label="Changelog:")
        changelog_label.set_xalign(0)
        vbox.pack_start(changelog_label, False, False, 0)

        for change in changelog:
            change_label = Gtk.Label(label=f"- {change}")
            change_label.set_xalign(0)
            vbox.pack_start(change_label, False, False, 0)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_pulse_step(0.1)
        vbox.pack_start(self.progress_bar, False, False, 0)

        update_button = Gtk.Button(label="Update")
        update_button.connect("clicked", self.update_repo)
        vbox.pack_start(update_button, False, False, 0)

        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", lambda _: self.destroy())
        vbox.pack_start(close_button, False, False, 0)

        self.connect("destroy", Gtk.main_quit)

    def update_repo(self, _):
        update_local_version()
        self.progress_bar.set_text("Updating...")
        self.progress_bar.set_show_text(True)
        self.progress_bar.pulse()
        self.pulse_timeout_id = GLib.timeout_add(100, self.pulse_progress_bar)
        threading.Thread(target=self.run_git_pull).start()

    def pulse_progress_bar(self):
        self.progress_bar.pulse()
        return True

    def run_git_pull(self):
        def progress_callback(line):
            GLib.idle_add(self.progress_bar.pulse)
            print(line.strip())

        update_local_repo(progress_callback)
        GLib.idle_add(self.on_update_complete)

    def on_update_complete(self):
        if hasattr(self, "pulse_timeout_id"):
            GLib.source_remove(self.pulse_timeout_id)
        self.progress_bar.set_text("Update Complete")
        self.progress_bar.set_fraction(1.0)
        self.destroy()
        kill_processes()
        run_disowned_command()


# Check for updates


def is_connected():
    try:
        # Connect to the host -- tells us if the host is actually reachable
        print("Checking internet connection...")
        socket.create_connection(("www.google.com", 80))
        print("Internet connection is available.")
        return True
    except OSError:
        pass

    print("No internet connection.")
    return False


def check_for_updates():
    if not is_connected():
        # If not connected to the internet, do nothing
        return

    fetch_remote_version()

    current_version, _ = get_local_version()
    latest_version, changelog, _ = get_remote_version()

    if latest_version > current_version:
        win = UpdateWindow(latest_version, changelog)
        win.show_all()
        Gtk.main()


# Run update check
check_for_updates()
