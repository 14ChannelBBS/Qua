from typing import Union

import emoji

with open("emoji-variation-sequences.txt", "r") as f:
    variationSequences = f.read()


def checkEmoji(char: str) -> Union[bool, str]:
    isEmoji = emoji.is_emoji(char)
    isTextEmoji = (
        emoji.is_emoji(char[0])
        and f"{hex(ord(char[0]))[2:].upper()} FE0E" in variationSequences
    )

    if isTextEmoji:
        return char[0] + chr(int("FE0F", 16))
    elif isEmoji:
        return True
    else:
        return False
