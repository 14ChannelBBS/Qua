import glob
import importlib
from typing import List

from objects import QuaPlugin

from .logger import log


class PluginService:
    plugins: List[QuaPlugin] = []

    @classmethod
    def loadPlugins(cls):
        fileList = glob.glob("plugins/*.py")
        for file in fileList:
            module = importlib.import_module(
                file.replace(".py", "").replace("\\", ".").replace("/", ".")
            )

            if not getattr(module, "pluginInstance", None):
                log.warning(f'File "{file}" is not Qua plugin!')
                continue

            if not isinstance(module.pluginInstance, QuaPlugin):
                log.warning(f'File "{file}" is not Qua plugin!')
                continue

            plugin: QuaPlugin = module.pluginInstance
            cls.plugins.append(plugin)
            log.info(
                f"Qua Plugin {plugin.name} (ID: {plugin.id}, v{plugin.version}) was loaded!"
            )
