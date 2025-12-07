from objects import (
    QuaPlugin,
    RenderingResponseEvent,
    ResponsePostEvent,
    ThreadPostEvent,
)


class TemplatePlugin(QuaPlugin):
    def __init__(self):
        super().__init__()

        self.id = "template"
        self.name = "テンプレートプラグイン"
        self.description = "Quaのプラグインテンプレート。"
        self.projectUrl = "https://github.com/14ChannelBBS/Qua"
        self.version = "1.0.0"

    async def onThreadPost(self, event: ThreadPostEvent):
        # event.title = "スレタイ書き換え"
        # スレッドデータ直書き換えとか実装したほうが良いんかね...?
        ...

    async def onResponsePost(self, event: ResponsePostEvent):
        # event.name = "名前書き換え"
        # スレッドデータ直書き換えとか実装したほうが良いんかね...?
        ...

    def onRenderingResponse(self, event: RenderingResponseEvent):
        # event.response.name = "表示される名前を書き換え(スレッドデータは書き換えない)"
        ...


pluginInstance = TemplatePlugin()
