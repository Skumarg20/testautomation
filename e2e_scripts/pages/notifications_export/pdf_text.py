"""The text of each page of a PDF the app built (report PDFs, bill previews), without a PDF library.

Enough of the PDF format for the files MargBooks returns: numbered objects (also inside object streams),
Flate-compressed streams, the page tree, each page's fonts and their ToUnicode maps, and the text-showing
operators (Tj, TJ, ', "). A glyph with no Unicode mapping comes out as U+FFFD, which is how a font without
the script's glyphs (the "black dots" of MBC-13147) shows up here.
"""

import re
import zlib
from dataclasses import dataclass, field

UNMAPPED = "�"
WORD_GAP_THOUSANDTHS = -200
OBJECT_START = re.compile(rb"(\d+)\s+\d+\s+obj\b")
REFERENCE = re.compile(rb"(\d+)\s+\d+\s+R")
KIDS = re.compile(rb"/Kids\s*\[([^\]]*)\]")
CONTENTS = re.compile(rb"/Contents\s*(\[[^\]]*\]|\d+\s+\d+\s+R)")
FONT_DICT = re.compile(rb"/Font\s*(<<.*?>>|\d+\s+\d+\s+R)", re.S)
FONT_ENTRY = re.compile(rb"/([^\s/<>\[\]()]+)\s+(\d+)\s+\d+\s+R")
RESOURCES_REF = re.compile(rb"/Resources\s+(\d+)\s+\d+\s+R")
PARENT = re.compile(rb"/Parent\s+(\d+)\s+\d+\s+R")
TO_UNICODE = re.compile(rb"/ToUnicode\s+(\d+)\s+\d+\s+R")
DIRECT_LENGTH = re.compile(rb"/Length\s+(\d+)(?!\s+\d+\s+R)")
CODESPACE = re.compile(rb"begincodespacerange\s*<([0-9A-Fa-f]+)>")
BFCHAR = re.compile(rb"beginbfchar(.*?)endbfchar", re.S)
BFRANGE = re.compile(rb"beginbfrange(.*?)endbfrange", re.S)
HEX = re.compile(rb"<([0-9A-Fa-f\s]*)>")
RANGE_ENTRY = re.compile(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(<[0-9A-Fa-f]+>|\[[^\]]*\])")
CONTENT_TOKEN = re.compile(rb"\(|<<|>>|<[0-9A-Fa-f\s]*>|\[|\]|/[^\s/<>\[\]()%]*|[^\s/<>\[\]()%]+")
LITERAL_ESCAPES = {ord("n"): b"\n", ord("r"): b"\r", ord("t"): b"\t", ord("b"): b"\b", ord("f"): b"\f"}
LINE_BREAKS = {b"Tm", b"T*", b"ET", b"'", b'"'}
LINE_MOVES = {b"Td", b"TD"}


@dataclass
class _PdfObject:
    head: bytes
    stream: bytes = b""


@dataclass
class _Font:
    code_length: int = 1
    unicode: dict[int, str] = field(default_factory=dict)

    def decode(self, raw: bytes) -> str:
        if not self.unicode:
            return raw.decode("latin-1")
        codes = (
            int.from_bytes(raw[i : i + self.code_length], "big") for i in range(0, len(raw), self.code_length)
        )
        return "".join(self.unicode.get(code, UNMAPPED) for code in codes)


@dataclass(frozen=True)
class PdfPage:
    text: str

    def shows(self, expected: str) -> bool:
        """True if the page shows `expected`. White space is ignored on both sides: PDF writers place
        words, and often single glyphs, at their own positions instead of writing a space."""
        return _without_space(expected) in _without_space(self.text)

    def shows_every_character_of(self, word: str) -> bool:
        """Complex scripts (Devanagari) are drawn in visual glyph order, so the word is checked by its
        characters, each of which must have reached the PDF as itself."""
        return all(character in self.text for character in _without_space(word))


class PdfText:
    def __init__(self, pdf: bytes) -> None:
        self._objects = _read_objects(pdf)

    def pages(self) -> list[PdfPage]:
        """Each page's text, in page order, with runs of white space collapsed to one space."""
        return [PdfPage(" ".join(self._page_text(page).split())) for page in self._page_numbers()]

    def _page_numbers(self) -> list[int]:
        roots = [
            number
            for number, obj in self._objects.items()
            if re.search(rb"/Type\s*/Pages\b", obj.head) and not PARENT.search(obj.head)
        ]
        return [page for root in roots for page in self._leaves(root)]

    def _leaves(self, number: int) -> list[int]:
        kids = KIDS.search(self._head(number))
        if kids is None:
            return [number]
        return [leaf for ref in REFERENCE.findall(kids.group(1)) for leaf in self._leaves(int(ref))]

    def _page_text(self, page: int) -> str:
        contents = CONTENTS.search(self._head(page))
        refs = REFERENCE.findall(contents.group(1)) if contents else []
        content = b"\n".join(self._objects[int(ref)].stream for ref in refs if int(ref) in self._objects)
        return _show_text(content, self._fonts_of(page))

    def _fonts_of(self, page: int) -> dict[bytes, _Font]:
        for holder in self._resource_holders(page):
            font_dict = FONT_DICT.search(self._head(holder))
            if font_dict:
                return {name: self._font(int(ref)) for name, ref in FONT_ENTRY.findall(self._dict(font_dict))}
        return {}

    def _resource_holders(self, page: int) -> list[int]:
        """The page, its resources object, then its parents (resources are inherited)."""
        holders: list[int] = []
        current: int | None = page
        while current is not None and current in self._objects:
            holders.append(current)
            resources = RESOURCES_REF.search(self._head(current))
            if resources:
                holders.append(int(resources.group(1)))
            parent = PARENT.search(self._head(current))
            current = int(parent.group(1)) if parent else None
        return holders

    def _dict(self, match: re.Match[bytes]) -> bytes:
        value = match.group(1)
        reference = REFERENCE.fullmatch(value.strip())
        return self._head(int(reference.group(1))) if reference else value

    def _font(self, number: int) -> _Font:
        to_unicode = TO_UNICODE.search(self._head(number))
        if to_unicode is None or int(to_unicode.group(1)) not in self._objects:
            return _Font()
        return _parse_cmap(self._objects[int(to_unicode.group(1))].stream)

    def _head(self, number: int) -> bytes:
        obj = self._objects.get(number)
        return obj.head if obj else b""


def _without_space(text: str) -> str:
    return "".join(text.split())


def _read_objects(pdf: bytes) -> dict[int, _PdfObject]:
    objects: dict[int, _PdfObject] = {}
    position = 0
    while (start := OBJECT_START.search(pdf, position)) is not None:
        obj, position = _read_object(pdf, start.end())
        objects[int(start.group(1))] = obj
    for obj in list(objects.values()):
        if re.search(rb"/Type\s*/ObjStm\b", obj.head):
            objects.update(_unpack_object_stream(obj))
    return objects


def _read_object(pdf: bytes, start: int) -> tuple[_PdfObject, int]:
    end = pdf.find(b"endobj", start)
    stream_at = pdf.find(b"stream", start)
    if stream_at < 0 or (0 <= end < stream_at):
        return _PdfObject(pdf[start:end]), end + len(b"endobj")
    head = pdf[start:stream_at]
    body_start = stream_at + len(b"stream")
    body_start += 2 if pdf[body_start : body_start + 2] == b"\r\n" else 1
    length = DIRECT_LENGTH.search(head)
    body_end = body_start + int(length.group(1)) if length else pdf.find(b"endstream", body_start)
    end = pdf.find(b"endobj", body_end)
    return _PdfObject(head, _decoded(head, pdf[body_start:body_end])), end + len(b"endobj")


def _decoded(head: bytes, raw: bytes) -> bytes:
    if b"/FlateDecode" not in head:
        return raw
    inflater = zlib.decompressobj()
    try:
        return inflater.decompress(raw)
    except zlib.error:
        return b""


def _unpack_object_stream(stream_object: _PdfObject) -> dict[int, _PdfObject]:
    count = int(re.search(rb"/N\s+(\d+)", stream_object.head).group(1))  # type: ignore[union-attr]
    first = int(re.search(rb"/First\s+(\d+)", stream_object.head).group(1))  # type: ignore[union-attr]
    header = [int(value) for value in stream_object.stream[:first].split()[: count * 2]]
    numbers, offsets = header[0::2], [first + offset for offset in header[1::2]]
    ends = [*offsets[1:], len(stream_object.stream)]
    return {
        number: _PdfObject(stream_object.stream[start:end])
        for number, start, end in zip(numbers, offsets, ends, strict=True)
    }


def _parse_cmap(cmap: bytes) -> _Font:
    codespace = CODESPACE.search(cmap)
    font = _Font(code_length=len(codespace.group(1)) // 2 if codespace else 2)
    for block in BFCHAR.findall(cmap):
        hexes = HEX.findall(block)
        for source, target in zip(hexes[0::2], hexes[1::2], strict=False):
            font.unicode[int(source, 16)] = _utf16(target)
    for block in BFRANGE.findall(cmap):
        for low, high, target in RANGE_ENTRY.findall(block):
            _add_range(font, range(int(low, 16), int(high, 16) + 1), target)
    return font


def _add_range(font: _Font, codes: range, target: bytes) -> None:
    if target.startswith(b"["):
        for code, each in zip(codes, HEX.findall(target), strict=False):
            font.unicode[code] = _utf16(each)
        return
    first = int(target.strip(b"<>"), 16)
    for offset, code in enumerate(codes):
        font.unicode[code] = chr(first + offset) if first + offset < 0x110000 else UNMAPPED


def _utf16(hex_digits: bytes) -> str:
    digits = re.sub(rb"\s", b"", hex_digits)
    return bytes.fromhex(digits.decode("ascii")).decode("utf-16-be", errors="replace")


@dataclass(frozen=True)
class _Operator:
    name: bytes


@dataclass(frozen=True)
class _Name:
    value: bytes


def _show_text(content: bytes, fonts: dict[bytes, _Font]) -> str:
    font = _Font()
    operands: list[object] = []
    pieces: list[str] = []
    for token in _tokens(content):
        if not isinstance(token, _Operator):
            operands.append(token)
            continue
        if token.name == b"Tf" and len(operands) >= 2 and isinstance(operands[-2], _Name):
            font = fonts.get(operands[-2].value, _Font())
        elif token.name in (b"Tj", b"'", b'"') and operands and isinstance(operands[-1], bytes):
            pieces.append(font.decode(operands[-1]))
        elif token.name == b"TJ" and operands and isinstance(operands[-1], list):
            pieces.append(_shown_array(operands[-1], font))
        if _starts_a_line(token, operands):
            pieces.append(" ")
        operands = []
    return "".join(pieces)


def _starts_a_line(operator: _Operator, operands: list[object]) -> bool:
    """A line break, or a move with a vertical part (a move along the line places the next glyph)."""
    if operator.name in LINE_MOVES:
        return bool(operands) and operands[-1] != 0.0
    return operator.name in LINE_BREAKS


def _shown_array(items: list[object], font: _Font) -> str:
    text = []
    for item in items:
        if isinstance(item, bytes):
            text.append(font.decode(item))
        elif isinstance(item, float) and item < WORD_GAP_THOUSANDTHS:
            text.append(" ")
    return "".join(text)


def _tokens(content: bytes) -> list[object]:
    """Operands (bytes for strings, float, _Name, list for arrays) and _Operator, in content order."""
    tokens: list[object] = []
    stack: list[list[object]] = [tokens]
    position = 0
    while (match := CONTENT_TOKEN.search(content, position)) is not None:
        word = match.group(0)
        position = match.end()
        if word == b"(":
            value, position = _literal(content, position)
            stack[-1].append(value)
        elif word == b"[":
            stack.append([])
        elif word == b"]" and len(stack) > 1:
            closed = stack.pop()
            stack[-1].append(closed)
        elif word.startswith(b"<") and not word.startswith(b"<<"):
            digits = re.sub(rb"\s", b"", word[1:-1])
            stack[-1].append(bytes.fromhex((digits + b"0" * (len(digits) % 2)).decode("ascii")))
        elif word.startswith(b"/"):
            stack[-1].append(_Name(word[1:]))
        elif word == b"ID":
            position = content.find(b"EI", position) + len(b"EI")
        else:
            stack[-1].append(_number_or_operator(word))
    return tokens


def _number_or_operator(word: bytes) -> object:
    try:
        return float(word)
    except ValueError:
        return _Operator(word)


def _literal(content: bytes, position: int) -> tuple[bytes, int]:
    """A (string) with nested parentheses and escapes; `position` is just after the opening one."""
    value = bytearray()
    depth = 1
    while position < len(content):
        char = content[position]
        position += 1
        if char == ord("\\"):
            escaped, position = _escape(content, position)
            value += escaped
            continue
        depth += {ord("("): 1, ord(")"): -1}.get(char, 0)
        if depth == 0:
            break
        value.append(char)
    return bytes(value), position


def _escape(content: bytes, position: int) -> tuple[bytes, int]:
    char = content[position]
    octal = re.match(rb"[0-7]{1,3}", content[position : position + 3])
    if octal:
        return bytes([int(octal.group(0), 8) & 0xFF]), position + len(octal.group(0))
    if char in (ord("\r"), ord("\n")):
        return b"", position + (2 if content[position : position + 2] == b"\r\n" else 1)
    return LITERAL_ESCAPES.get(char, bytes([char])), position + 1
