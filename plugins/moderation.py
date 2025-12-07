import re

from objects import (
    QuaPlugin,
    ResponsePostEvent,
)


class ModerationPlugin(QuaPlugin):
    def __init__(self):
        super().__init__()

        self.id = "moderation"
        self.name = "モデレーション"
        self.description = "★持ちがスレッド消せるようにしておきます。。。管理者ページができるまでの暫定実装。"
        self.projectUrl = "https://github.com/14ChannelBBS/Qua"
        self.version = "1.0.0"

    async def onResponsePost(self, event: ResponsePostEvent):
        pass


pluginInstance = ModerationPlugin()
