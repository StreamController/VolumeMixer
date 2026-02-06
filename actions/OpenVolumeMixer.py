from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

import globals as gl
from loguru import logger as log

import os
from PIL import Image

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


class OpenVolumeMixer(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_ready(self):
        icon_path = os.path.join(self.plugin_base.PATH, "assets", "equalizer.png")
        self.set_media(media_path=icon_path)

    def on_key_down(self):
        # Reset position
        self.plugin_base.start_index = 0

        page_name = "VolumeMixer"
        if self.deck_controller.deck.dial_count() > 0:
            page_name = "VolumeMixerSDPlus"

        page_path = os.path.join(self.plugin_base.PATH, "pages", f"{page_name}.json")
        if not os.path.exists(page_path):
            log.error("Could not find volume mixer page. Consider reinstalling the plugin.")
            return
        page = gl.page_manager.get_page(path=page_path, deck_controller=self.deck_controller)
        if page is None:
            log.error("Could not create volume mixer page object. Consider reinstalling the plugin.")
            return

        self.plugin_base.original_page_path = self.deck_controller.active_page.json_path
        self.deck_controller.load_page(page)

    def get_config_rows(self) -> list:
        # Increments (%)
        self.increments_row = Adw.SpinRow.new_with_range(min=0, max=100, step=5)
        self.increments_row.set_title("Increments (%):")

        # Load default
        settings = self.get_settings() or {}
        self.increments_row.set_value(settings.get("increments", 10))
        self.plugin_base.volume_increment = self.increments_row.get_value() / 100

        # Connect signal
        self.increments_row.connect("changed", self.on_increments_change)

        # --- Label mode (plugin-wide) ---
        self.label_mode_row = Adw.ComboRow()
        self.label_mode_row.set_title(self.plugin_base.lm.get("settings.label_mode.title"))
        self.label_mode_row.set_subtitle(self.plugin_base.lm.get("settings.label_mode.subtitle"))

        # Values used for storage
        self._label_mode_values = ["auto", "app", "media", "app+media"]

        model = Gtk.StringList.new([
            self.plugin_base.lm.get("settings.label_mode.auto"),
            self.plugin_base.lm.get("settings.label_mode.app"),
            self.plugin_base.lm.get("settings.label_mode.media"),
            self.plugin_base.lm.get("settings.label_mode.app_media"),
        ])
        self.label_mode_row.set_model(model)

        # Load current plugin setting (global)
        try:
            ps = self.plugin_base.get_settings() or {}
            current = (ps.get("label_mode", "auto") or "auto").lower()
        except Exception:
            current = "auto"

        selected = 0
        if current in self._label_mode_values:
            selected = self._label_mode_values.index(current)
        self.label_mode_row.set_selected(selected)

        self.label_mode_row.connect("notify::selected", self.on_label_mode_changed)

        return [self.increments_row, self.label_mode_row]

    def on_increments_change(self, row):
        settings = self.get_settings() or {}
        settings["increments"] = row.get_value()
        self.plugin_base.volume_increment = row.get_value() / 100
        self.set_settings(settings)

    def on_label_mode_changed(self, row, _pspec=None):
        try:
            idx = row.get_selected()
        except Exception:
            idx = 0

        mode = "auto"
        try:
            if hasattr(self, "_label_mode_values") and 0 <= idx < len(self._label_mode_values):
                mode = self._label_mode_values[idx]
        except Exception:
            mode = "auto"

        # Store in plugin settings (global for all mixer keys)
        try:
            ps = self.plugin_base.get_settings() or {}
            ps["label_mode"] = mode
            self.plugin_base.set_settings(ps)
        except Exception as ex:
            log.error(f"Failed to store label_mode: {ex}")

        # Refresh all labels immediately
        try:
            self.plugin_base.refresh_volume_actions()
        except Exception:
            pass
