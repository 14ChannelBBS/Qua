function emojiParse(text) {
  return text.replace(/&#(\d+);/g, (_, dec) => {
    const char = String.fromCodePoint(dec);
    const parsed = twemoji.parse(char);
    return parsed === char ? char : parsed;
  });
}
