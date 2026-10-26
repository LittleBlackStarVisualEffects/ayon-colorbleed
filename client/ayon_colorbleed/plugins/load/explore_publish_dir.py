import os

from ayon_core.lib import is_running_from_build
from ayon_core.pipeline import load

from ayon_colorbleed import ColorbleedAddon


class ShowPublishInExplorer(load.LoaderPlugin):
    """Show publish in explorer"""

    product_types = {"*"}
    representations = {"*"}

    enabled = (
        not is_running_from_build() or
        os.getenv("AYON_USE_DEV") == "1"
    )

    label = "Show in explorer"
    order = 100
    icon = "external-link"
    color = "gray"

    def load(self, context, name, namespace, data):
        path = self.filepath_from_context(context)
        ColorbleedAddon.open_in_explorer(os.path.dirname(path))
