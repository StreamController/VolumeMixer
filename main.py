from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

import sys
import os
import webbrowser
from loguru import logger as log
from PIL import Image, ImageEnhance
import math
import re
import threading
import subprocess
import time
from evdev import ecodes as e
from evdev import UInput

from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page

import pulsectl
from plugins.com_core447_VolumeMixer.actions.OpenVolumeMixer import OpenVolumeMixer
from plugins.com_core447_VolumeMixer.actions.ExitVolumeMixer import ExitVolumeMixer
from plugins.com_core447_VolumeMixer.actions.MuteKey import MuteKey
from plugins.com_core447_VolumeMixer.actions.VolumeUpKey import UpKey
from plugins.com_core447_VolumeMixer.actions.VolumeDownKey import DownKey
from plugins.com_core447_VolumeMixer.actions.MoveRight import MoveRight
from plugins.com_core447_VolumeMixer.actions.MoveLeft import MoveLeft
from .actions.Dial import Dial

# Add plugin to sys.paths
sys.path.append(os.path.dirname(__file__))


class VolumeMixer(PluginBase):
    def __init__(self):
        super().__init__()
        self.init_vars()

        self.open_volume_mixer_holder = ActionHolder(
            plugin_base=self,
            action_base=OpenVolumeMixer,
            action_id_suffix="Open",
            action_name=self.lm.get("actions.open-volume-mixer.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED
            }
        )
        self.add_action_holder(self.open_volume_mixer_holder)

        self.exit_volume_mixer_holder = ActionHolder(
            plugin_base=self,
            action_base=ExitVolumeMixer,
            action_id_suffix="Exit",
            action_name=self.lm.get("actions.exit-volume-mixer.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED
            }
        )
        self.add_action_holder(self.exit_volume_mixer_holder)

        self.mute_key_holder = ActionHolder(
            plugin_base=self,
            action_base=MuteKey,
            action_id_suffix="VolumeMute",
            action_name=self.lm.get("actions.mute-key.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED
            }
        )
        self.add_action_holder(self.mute_key_holder)

        self.up_key_holder = ActionHolder(
            plugin_base=self,
            action_base=UpKey,
            action_id_suffix="VolumeUp",
            action_name=self.lm.get("actions.up-key.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED
            }
        )
        self.add_action_holder(self.up_key_holder)

        self.down_key_holder = ActionHolder(
            plugin_base=self,
            action_base=DownKey,
            action_id_suffix="VolumeDown",
            action_name=self.lm.get("actions.down-key.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED
            }
        )
        self.add_action_holder(self.down_key_holder)

        self.move_right_holder = ActionHolder(
            plugin_base=self,
            action_base=MoveRight,
            action_id_suffix="MoveRight",
            action_name=self.lm.get("actions.move-right.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNTESTED
            }
        )
        self.add_action_holder(self.move_right_holder)

        self.move_left_holder = ActionHolder(
            plugin_base=self,
            action_base=MoveLeft,
            action_id_suffix="MoveLeft",
            action_name=self.lm.get("actions.move-left.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNTESTED
            }
        )
        self.add_action_holder(self.move_left_holder)

        self.dial_holder = ActionHolder(
            plugin_base=self,
            action_base=Dial,
            action_id_suffix="Dial",
            action_name=self.lm.get("actions.dial.name"),
            action_support={
                Input.Key: ActionInputSupport.UNSUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED
            }
        )
        self.add_action_holder(self.dial_holder)

        # Register plugin
        self.register(
            plugin_name=self.lm.get("plugin.name"),
            github_repo="https://github.com/StreamController/VolumeMixer",
            plugin_version="1.0.0",
            app_version="1.0.0-alpha"
        )

        self.register_page(os.path.join(self.PATH, "pages", "VolumeMixer.json"))
        self.register_page(os.path.join(self.PATH, "pages", "VolumeMixerSDPlus.json"))

    def init_vars(self):
        self.lm = self.locale_manager
        self.lm.set_to_os_default()

        #TODO: Add multi deck support
        self.original_page_path = None
        self.start_index = 0
        self.pulse = pulsectl.Pulse("stream-controller", threading_lock=True)
        self.volume_increment = 0.05
        self.volume_actions: list[ActionBase] = []

        # Label mode for stream names shown on the deck
        # Values: auto | app | media | app+media
        self._generic_media_regex = re.compile(
            r"^(audio\s*stream\s*#?\d+|audiostream\s*#?\d+|playback\s*stream\s*#?\d+)$",
            re.IGNORECASE
        )
        try:
            ps = self.get_settings() or {}
            if "label_mode" not in ps:
                ps["label_mode"] = "auto"
                self.set_settings(ps)
        except Exception as ex:
            log.debug(f"Could not init plugin settings: {ex}")

    def refresh_volume_actions(self) -> None:
        """Refresh labels/icons on all mixer actions."""
        for a in list(self.volume_actions):
            try:
                a.on_tick()
            except Exception:
                pass

    def get_label_mode(self) -> str:
        try:
            return (self.get_settings() or {}).get("label_mode", "auto")
        except Exception:
            return "auto"

    def _get_sink_input_proplist(self, sink_input) -> dict:
        proplist = getattr(sink_input, "proplist", None)
        if isinstance(proplist, dict):
            return proplist
        proplist = getattr(sink_input, "properties", None)
        if isinstance(proplist, dict):
            return proplist
        return {}

    def get_display_name(self, sink_input) -> str:
        """Return the text shown on the deck for a given sink_input."""
        proplist = self._get_sink_input_proplist(sink_input)

        fallback = getattr(sink_input, "name", "") or ""
        app = (
            proplist.get("application.name")
            or proplist.get("application.process.binary")
            or proplist.get("application.process.user")
            or ""
        )
        media = (
            proplist.get("media.name")
            or proplist.get("node.description")
            or proplist.get("application.icon_name")
            or ""
        )

        mode = (self.get_label_mode() or "auto").strip().lower()

        def is_generic_media(s: str) -> bool:
            s2 = (s or "").strip()
            if not s2:
                return True
            return bool(self._generic_media_regex.match(s2))

        if mode == "app":
            return app or fallback
        if mode == "media":
            return media or fallback
        if mode in ("app+media", "app_media", "app-media"):
            if app and media and app.strip().lower() != media.strip().lower():
                return f"{app}: {media}"
            return app or media or fallback

        # auto (default)
        if media and not is_generic_media(media):
            return media
        if app:
            return app
        if media:
            return media
        return fallback
