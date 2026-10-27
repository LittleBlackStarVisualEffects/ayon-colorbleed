import os
import platform
import subprocess

import ayon_api
from ayon_core.pipeline import Anatomy, get_representation_path
from ayon_core.addon import (
    AYONAddon,
    IPluginPaths,
    click_wrap,
    ensure_addons_are_process_ready,
)
from ayon_core.lib.transcoding import (
    VIDEO_EXTENSIONS, IMAGE_EXTENSIONS
)

from .version import __version__

VIDEO_EXTENSIONS_TUPLE = tuple(VIDEO_EXTENSIONS)
IMAGE_EXTENSIONS_TUPLE = tuple(IMAGE_EXTENSIONS)


class ColorbleedAddon(AYONAddon, IPluginPaths):
    name = "colorbleed"
    title = "Colorbleed"
    version = __version__

    def get_plugin_paths(self):
        """Implementation of IPluginPaths to get plugin paths."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        plugins_dir = os.path.join(current_dir, "plugins")

        return {
            "actions": [os.path.join(plugins_dir, "launcher_actions")],
            "load": [os.path.join(plugins_dir, "load")],
            "publish": [os.path.join(plugins_dir, "publish")]
        }

    # region CLI
    def cli(self, addon_click_group):
        main_group = click_wrap.group(
            self._cli_main, name=self.name, help="Colorbleed addon"
        )
        (
            main_group.command(
                self._cli_run,
                name="run",
                help="Run filepaths"
            )
            .option("--project", required=True, help="Project name")
            .option("--entity_type", required=True, help="Entity type")
            .argument("entity_ids", nargs=-1, required=True)
        )
        (
            main_group.command(
                self._cli_show_in_explorer,
                name="show-in-explorer",
                help="Show given paths or entity URIs in explorer."
            )
            .option("--project", required=True, help="Project name")
            .option("--entity_type", required=True, help="Entity type")
            .argument("entity_ids", nargs=-1, required=True)
        )
        # Convert main command to click object and add it to parent group
        addon_click_group.add_command(
            main_group.to_click_obj()
        )

    def _cli_main(self):
        ensure_addons_are_process_ready(
            addon_name=self.name,
            addon_version=self.version
        )

    def _get_entity_paths(self, project_name, entity_type, entity_ids):
        paths: "list[str]" = []
        if entity_type != "version":
            return paths
        anatomy = Anatomy(project_name)
        representations = ayon_api.get_representations(
            project_name=project_name,
            version_ids=entity_ids,
        )
        for representation in representations:
            try:
                path = get_representation_path(
                    project_name, representation, anatomy=anatomy
                )
            except Exception as exc:
                print(
                    f"Skipping representation '{representation['name']}':"
                    f" {exc}"
                )
                continue
            paths.append(str(path))
        return paths

    def _cli_run(
        self, project, entity_type, entity_ids
    ):
        """Run paths using OS default application"""

        paths = self._get_entity_paths(project, entity_type, entity_ids)
        if not paths:
            return

        # Unfortunately the user is unable to pick a specific representation
        # from the web frontend. So we will prioritize certain files over
        # others - hoping we're running a file that makes sense to run.
        def prioritize(path: str) -> int:
            # Lower number is prioritized
            order = 0

            # Prefer certain image/video extensions first
            if path.endswith(".exr"):
                order -= 1000
            elif path.endswith("_h264.mp4"):
                order -= 30
            elif path.endswith(".mp4"):
                order -= 20

            # Videos first, then images
            if path.endswith(VIDEO_EXTENSIONS_TUPLE):
                order -= 1000
            elif path.endswith(IMAGE_EXTENSIONS_TUPLE):
                order -= 500

            # Avoid paths that do not exist
            if not os.path.exists(path):
                order += 9999

            return order

        paths.sort(key=prioritize)
        self.run_file(paths[0])

    def _cli_show_in_explorer(
        self, project, entity_type, entity_ids
    ):
        """Open the folders of the given entities in the OS file browser"""
        paths = self._get_entity_paths(project, entity_type, entity_ids)
        folders = set()
        for path in paths:
            if not os.path.isdir(path):
                path = os.path.dirname(path)
            folders.add(os.path.normpath(path))

        if not folders:
            raise RuntimeError("No published files found for this version.")

        existing = sorted(f for f in folders if os.path.isdir(f))
        if not existing:
            raise RuntimeError(
                "Folder not found on this machine (is the drive mounted?):\n"
                + "\n".join(sorted(folders))
            )
        for folder in existing:
            self.open_in_explorer(folder)
    # endregion

    @staticmethod
    def run_file(path):
        platform_name = platform.system().lower()
        if platform_name == 'windows':  # Windows
            os.startfile(path)
        elif platform_name == 'darwin':  # macOS
            subprocess.Popen(('open', path))
        elif platform_name == "linux":  # linux variants
            subprocess.Popen(('xdg-open', path))
        else:
            raise RuntimeError(f"Unknown platform {platform.system()}")

    @staticmethod
    def open_in_explorer(path: str):
        platform_name = platform.system().lower()
        if platform_name == "windows":
            os.startfile(path)
        elif platform_name == "darwin":
            subprocess.run(["open", path], check=True)
        elif platform_name == "linux":
            subprocess.Popen(["xdg-open", path])
        else:
            raise RuntimeError(f"Unknown platform {platform.system()}")
