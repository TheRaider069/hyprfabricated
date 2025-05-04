import os
import hashlib
import shutil
from gi.repository import GdkPixbuf, Gtk, GLib, Gio, Gdk
from fabric.widgets.box import Box
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.entry import Entry
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.label import Label
from fabric.utils.helpers import exec_shell_command_async
import modules.icons as icons
import config.data as data
from PIL import Image
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

class WallpaperSelector(Box):
    CACHE_DIR = f"{data.CACHE_DIR}/thumbs"  # Changed from wallpapers to thumbs

    def __init__(self, **kwargs):
        # Delete the old cache directory if it exists
        old_cache_dir = f"{data.CACHE_DIR}/wallpapers"
        if os.path.exists(old_cache_dir):
            shutil.rmtree(old_cache_dir)

        super().__init__(name="wallpapers", spacing=4, orientation="v", h_expand=False, v_expand=False, **kwargs)
        os.makedirs(self.CACHE_DIR, exist_ok=True)

        # Process old wallpapers: use os.scandir for efficiency and only loop
        # over image files that actually need renaming (they're not already lowercase
        # and with hyphens instead of spaces)
        with os.scandir(data.WALLPAPERS_DIR) as entries:
            for entry in entries:
                if entry.is_file() and self._is_image(entry.name):
                    # Check if the file needs renaming: file should be lowercase and have hyphens instead of spaces
                    if entry.name != entry.name.lower() or " " in entry.name:
                        new_name = entry.name.lower().replace(" ", "-")
                        full_path = os.path.join(data.WALLPAPERS_DIR, entry.name)
                        new_full_path = os.path.join(data.WALLPAPERS_DIR, new_name)
                        try:
                            os.rename(full_path, new_full_path)
                            print(f"Renamed old wallpaper '{full_path}' to '{new_full_path}'")
                        except Exception as e:
                            print(f"Error renaming file {full_path}: {e}")

        # Refresh the file list after potential renaming
        self.files = sorted([f for f in os.listdir(data.WALLPAPERS_DIR) if self._is_image(f)])
        self.thumbnails = []
        self.thumbnail_queue = []
        self.executor = ThreadPoolExecutor(max_workers=4)  # Shared executor

        # Variable to control the selection (similar to AppLauncher)
        self.selected_index = -1

        # Initialize UI components
        self.viewport = Gtk.IconView(name="wallpaper-icons")
        self.viewport.set_model(Gtk.ListStore(GdkPixbuf.Pixbuf, str))
        self.viewport.set_pixbuf_column(0)
        # Hide text column so only the image is shown
        self.viewport.set_text_column(-1)
        self.viewport.set_item_width(0)
        self.viewport.connect("item-activated", self.on_wallpaper_selected)
        # self.viewport.connect("selection-changed", self._on_selection_changed) # Removed connection

        self.scrolled_window = ScrolledWindow(
            name="scrolled-window",
            spacing=10,
            h_expand=True,
            v_expand=True,
            child=self.viewport,
        )

        self.search_entry = Entry(
            name="search-entry-walls",
            placeholder="Search Wallpapers...",
            h_expand=True,
            notify_text=lambda entry, *_: self.arrange_viewport(entry.get_text()),
            on_key_press_event=self.on_search_entry_key_press,
        )
        self.search_entry.props.xalign = 0.5
        self.search_entry.connect("focus-out-event", self.on_search_entry_focus_out)

        self.schemes = {
            "scheme-tonal-spot": "Tonal Spot",
            "scheme-content": "Content",
            "scheme-expressive": "Expressive",
            "scheme-fidelity": "Fidelity",
            "scheme-fruit-salad": "Fruit Salad",
            "scheme-monochrome": "Monochrome",
            "scheme-neutral": "Neutral",
            "scheme-rainbow": "Rainbow",
        }

        self.scheme_dropdown = Gtk.ComboBoxText()
        self.scheme_dropdown.set_name("scheme-dropdown")
        self.scheme_dropdown.set_tooltip_text("Select color scheme")
        for key, display_name in self.schemes.items():
            self.scheme_dropdown.append(key, display_name)
        self.scheme_dropdown.set_active_id("scheme-tonal-spot")
        self.scheme_dropdown.connect("changed", self.on_scheme_changed)

        # Create a switcher to enable/disable Matugen (enabled by default)
        self.matugen_switcher = Gtk.Switch(name="matugen-switcher")
        self.matugen_switcher.set_vexpand(False)
        self.matugen_switcher.set_hexpand(False)
        self.matugen_switcher.set_valign(Gtk.Align.CENTER)
        self.matugen_switcher.set_halign(Gtk.Align.CENTER)
        self.matugen_switcher.set_active(True)

        self.mat_icon = Label(name="mat-label", markup=icons.palette)

        # Add the switcher to the header_box's start_children
        self.header_box = CenterBox(
            name="header-box",
            spacing=8,
            orientation="h",
            start_children=[self.matugen_switcher, self.mat_icon],
            center_children=[self.search_entry],
            end_children=[self.scheme_dropdown],
        )

        self.add(self.header_box)
        self.add(self.scrolled_window)
        self._start_thumbnail_thread()
        self.setup_file_monitor()  # Initialize file monitoring
        self.show_all()
        # Ensure the search entry gets focus when starting
        self.search_entry.grab_focus()

    def setup_file_monitor(self):
        gfile = Gio.File.new_for_path(data.WALLPAPERS_DIR)
        self.file_monitor = gfile.monitor_directory(Gio.FileMonitorFlags.NONE, None)
        self.file_monitor.connect("changed", self.on_directory_changed)

    def on_directory_changed(self, monitor, file, other_file, event_type):
        file_name = file.get_basename()
        if event_type == Gio.FileMonitorEvent.DELETED:
            if file_name in self.files:
                self.files.remove(file_name)
                cache_path = self._get_cache_path(file_name)
                if os.path.exists(cache_path):
                    try:
                        os.remove(cache_path)
                    except Exception as e:
                        print(f"Error deleting cache {cache_path}: {e}")
                self.thumbnails = [(p, n) for p, n in self.thumbnails if n != file_name]
                GLib.idle_add(self.arrange_viewport, self.search_entry.get_text())
        elif event_type == Gio.FileMonitorEvent.CREATED:
            if self._is_image(file_name):
                # Convert filename to lowercase and replace spaces with "-"
                new_name = file_name.lower().replace(" ", "-")
                full_path = os.path.join(data.WALLPAPERS_DIR, file_name)
                new_full_path = os.path.join(data.WALLPAPERS_DIR, new_name)
                if new_name != file_name:
                    try:
                        os.rename(full_path, new_full_path)
                        file_name = new_name
                        print(f"Renamed file '{full_path}' to '{new_full_path}'")
                    except Exception as e:
                        print(f"Error renaming file {full_path}: {e}")
                if file_name not in self.files:
                    self.files.append(file_name)
                    self.files.sort()
                    self.executor.submit(self._process_file, file_name)
        elif event_type == Gio.FileMonitorEvent.CHANGED:
            if self._is_image(file_name) and file_name in self.files:
                cache_path = self._get_cache_path(file_name)
                if os.path.exists(cache_path):
                    try:
                        os.remove(cache_path)
                    except Exception as e:
                        print(f"Error deleting cache for changed file {file_name}: {e}")
                self.executor.submit(self._process_file, file_name)

    def arrange_viewport(self, query: str = ""):
        model = self.viewport.get_model()
        model.clear()
        filtered_thumbnails = [
            (thumb, name)
            for thumb, name in self.thumbnails
            if query.casefold() in name.casefold()
        ]
        filtered_thumbnails.sort(key=lambda x: x[1].lower())
        for pixbuf, file_name in filtered_thumbnails:
            model.append([pixbuf, file_name])
        # If the search entry is empty, no icon is selected; otherwise, select the first one.
        if query.strip() == "":
            self.viewport.unselect_all()
            self.selected_index = -1
        elif len(model) > 0:
            self.update_selection(0)

    def on_wallpaper_selected(self, iconview, path):
        model = iconview.get_model()
        file_name = model[path][1]
        full_path = os.path.join(data.WALLPAPERS_DIR, file_name)
        selected_scheme = self.scheme_dropdown.get_active_id()
        current_wall = os.path.expanduser(f"~/.current.wall")
        if os.path.isfile(current_wall):
            os.remove(current_wall)
        os.symlink(full_path, current_wall)
        if self.matugen_switcher.get_active():
            # Matugen is enabled: run the normal command.
            exec_shell_command_async(f'matugen image {full_path} -t {selected_scheme}')
        else:
            # Matugen is disabled: run the alternative swww command.
            exec_shell_command_async(
                f'swww img {full_path} -t outer --transition-duration 1.5 --transition-step 255 --transition-fps 60 -f Nearest'
            )

    def on_scheme_changed(self, combo):
        selected_scheme = combo.get_active_id()
        print(f"Color scheme selected: {selected_scheme}")

    def on_search_entry_key_press(self, widget, event):
        if event.state & Gdk.ModifierType.SHIFT_MASK:
            if event.keyval in (Gdk.KEY_Up, Gdk.KEY_Down):
                schemes_list = list(self.schemes.keys())
                current_id = self.scheme_dropdown.get_active_id()
                current_index = schemes_list.index(current_id) if current_id in schemes_list else 0
                new_index = (current_index - 1) % len(schemes_list) if event.keyval == Gdk.KEY_Up else (current_index + 1) % len(schemes_list)
                self.scheme_dropdown.set_active(new_index)
                return True
            elif event.keyval == Gdk.KEY_Right:
                self.scheme_dropdown.popup()
                return True

        if event.keyval in (Gdk.KEY_Up, Gdk.KEY_Down, Gdk.KEY_Left, Gdk.KEY_Right):
            self.move_selection_2d(event.keyval)
            return True
        elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if self.selected_index != -1:
                path = Gtk.TreePath.new_from_indices([self.selected_index])
                self.on_wallpaper_selected(self.viewport, path)
            return True
        return False

    # Removed _on_selection_changed method

    def move_selection_2d(self, keyval):
        model = self.viewport.get_model()
        total_items = len(model)
        if total_items == 0:
            return

        # --- Determine Column Count ---
        columns = self.viewport.get_columns()

        # If get_columns returns 0 or -1 (auto), try to estimate by checking item rows
        if columns <= 0 and total_items > 0:
            estimated_cols = 0
            try:
                # Check the row of the first item (should be 0)
                first_item_path = Gtk.TreePath.new_from_indices([0])
                base_row = self.viewport.get_item_row(first_item_path)

                # Find the index of the first item in the *next* row
                for i in range(1, total_items):
                    path = Gtk.TreePath.new_from_indices([i])
                    row = self.viewport.get_item_row(path)
                    if row > base_row:
                        estimated_cols = i # The number of items in the first row
                        break

                # If loop finished without finding a new row, all items are in one row
                if estimated_cols == 0:
                    estimated_cols = total_items

                columns = max(1, estimated_cols)
            except Exception:
                # Fallback if get_item_row fails (e.g., widget not realized)
                columns = 1
        elif columns <= 0 and total_items == 0:
             columns = 1 # Should not happen due to early return, but safe

        # Ensure columns is at least 1 after all checks
        columns = max(1, columns)

        # --- Navigation Logic ---
        current_index = self.selected_index
        new_index = current_index

        if current_index == -1:
            # If nothing is selected, select the first or last item based on direction
            if keyval in (Gdk.KEY_Down, Gdk.KEY_Right):
                new_index = 0
            elif keyval in (Gdk.KEY_Up, Gdk.KEY_Left):
                new_index = total_items - 1
            if total_items == 0: new_index = -1 # Handle edge case

        else:
            # Calculate potential new index based on key press
            if keyval == Gdk.KEY_Up:
                potential_new_index = current_index - columns
                # Only update if the new index is valid (>= 0)
                if potential_new_index >= 0:
                    new_index = potential_new_index
            elif keyval == Gdk.KEY_Down:
                potential_new_index = current_index + columns
                # Only update if the new index is valid (< total_items)
                if potential_new_index < total_items:
                    new_index = potential_new_index
            elif keyval == Gdk.KEY_Left:
                # Only update if not already in the first column (index % columns != 0)
                # and the index is greater than 0
                if current_index > 0 and current_index % columns != 0:
                    new_index = current_index - 1
            elif keyval == Gdk.KEY_Right:
                # Only update if not in the last column ((index + 1) % columns != 0)
                # and not the very last item (index < total_items - 1)
                if current_index < total_items - 1 and (current_index + 1) % columns != 0:
                    new_index = current_index + 1

        # Only update if the index actually changed and is valid
        if new_index != self.selected_index and 0 <= new_index < total_items:
             self.update_selection(new_index)
        elif total_items > 0 and self.selected_index == -1 and 0 <= new_index < total_items:
             # Handle selecting the first item when starting from -1
             self.update_selection(new_index)

    def update_selection(self, new_index: int):
        self.viewport.unselect_all()
        path = Gtk.TreePath.new_from_indices([new_index])
        self.viewport.select_path(path)
        self.viewport.scroll_to_path(path, False, 0.5, 0.5)  # Ensure the selected icon is visible
        self.selected_index = new_index

    def _start_thumbnail_thread(self):
        thread = GLib.Thread.new("thumbnail-loader", self._preload_thumbnails, None)

    def _preload_thumbnails(self, _data):
        futures = [self.executor.submit(self._process_file, file_name) for file_name in self.files]
        concurrent.futures.wait(futures)
        GLib.idle_add(self._process_batch)

    def _process_file(self, file_name):
        full_path = os.path.join(data.WALLPAPERS_DIR, file_name)
        cache_path = self._get_cache_path(file_name)
        if not os.path.exists(cache_path):
            try:
                with Image.open(full_path) as img:
                    width, height = img.size
                    side = min(width, height)
                    left = (width - side) // 2
                    top = (height - side) // 2
                    right = left + side
                    bottom = top + side
                    img_cropped = img.crop((left, top, right, bottom))
                    img_cropped.thumbnail((96, 96), Image.Resampling.LANCZOS)
                    img_cropped.save(cache_path, "PNG")
            except Exception as e:
                print(f"Error processing {file_name}: {e}")
                return
        self.thumbnail_queue.append((cache_path, file_name))
        GLib.idle_add(self._process_batch)

    def _process_batch(self):
        batch = self.thumbnail_queue[:10]
        del self.thumbnail_queue[:10]
        for cache_path, file_name in batch:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(cache_path)
                self.thumbnails.append((pixbuf, file_name))
                self.viewport.get_model().append([pixbuf, file_name])
            except Exception as e:
                print(f"Error loading thumbnail {cache_path}: {e}")
        if self.thumbnail_queue:
            GLib.idle_add(self._process_batch)
        return False

    def _get_cache_path(self, file_name: str) -> str:
        file_hash = hashlib.md5(file_name.encode("utf-8")).hexdigest()
        return os.path.join(self.CACHE_DIR, f"{file_hash}.png")

    @staticmethod
    def _is_image(file_name: str) -> bool:
        return file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'))

    def on_search_entry_focus_out(self, widget, event):
        if self.get_mapped():
            widget.grab_focus()
        return False
