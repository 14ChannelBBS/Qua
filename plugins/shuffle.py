import random
import re
from typing import List, Tuple

from objects import (
    Device,
    QuaPlugin,
    RenderingResponseEvent,
    ResponsePostEvent,
    ThreadPostEvent,
)


class ShufflePlugin(QuaPlugin):
    def __init__(self):
        super().__init__()

        self.id = "shuffle"
        self.name = "シャッフルプラグイン"
        self.description = (
            "文字列をシャッフルするシャッフルタグを追加するプラグインです。"
        )
        self.projectUrl = "https://github.com/14ChannelBBS/Qua"
        self.version = "1.0.0"

        self.compiled = re.compile(r"&lt;shuffle&gt;(.*)&lt;/shuffle&gt;")

    def shuffle(self, text: str) -> Tuple[str, List[str]]:
        shuffledTexts = re.findall(self.compiled, text)

        for i, t in enumerate(shuffledTexts.copy()):
            text = text.replace(
                f"&lt;shuffle&gt;{t}&lt;/shuffle&gt;", f"<shuffle={i}>", 1
            )
            shuffledTexts[i] = "".join(random.sample(t, len(t)))

        return text, shuffledTexts

    async def onThreadPost(self, event: ThreadPostEvent):
        event.content, shuffledTexts = self.shuffle(event.content)
        event.attributes["shuffleTexts"] = shuffledTexts

    async def onResponsePost(self, event: ResponsePostEvent):
        event.content, shuffledTexts = self.shuffle(event.content)
        event.attributes["shuffleTexts"] = shuffledTexts

    def onRenderingResponse(self, event: RenderingResponseEvent):
        for i, t in enumerate(event.response.attributes.get("shuffleTexts", [])):
            if event.device == Device.OfficialClient:
                info = f"""
                    <br>
                    <small>
                        <span style="color: red;">
                            シャッフル 原文→
                        </span>
                        <span style="background-color: #00000022; color: red; @media (prefers-color-scheme: dark) {{background-color: #00000088;}}" onClick="this.innerText='「{t}」'">
                            クリックして表示
                        </span>
                    </small>
                """.replace("    ", "").replace("\n", "")
            else:
                info = f" <br> シャッフル 原文→「{t}」"

            event.response.content = event.response.content.replace(
                f"<shuffle={i}>", t + info
            )


pluginInstance = ShufflePlugin()
