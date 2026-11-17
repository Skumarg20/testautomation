"""
Test ke liye chhote auzaar.

Yahan ek hi cheez hai: code me se COMMENT aur DOCSTRING hataana.

Zaroorat kyun padi -- teen baar aisa ho chuka hai ki test ne comment me
likha ek shabd dekh kar fail kar diya, jabki asli code bilkul theek tha:

    # temperature 0 -- 0.1/0.2 NAHI          <- comment
    "temperature": 0,                        <- asli code

Test ne "0.1" dekh kar keh diya ki temperature galat hai. Isliye jab bhi
test source code padhe, use pehle yahan se guzarna chahiye.
"""
from __future__ import annotations

import io
import tokenize


def code_only(src: str) -> str:
    """Comment aur docstring hata kar sirf asli code."""
    out: list[str] = []
    try:
        prev_type = None
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                continue
            # docstring = wo string jo apni line par akeli khadi ho
            if tok.type == tokenize.STRING and prev_type in (
                    None, tokenize.INDENT, tokenize.NEWLINE, tokenize.NL):
                prev_type = tok.type
                continue
            out.append(tok.string)
            if tok.type not in (tokenize.NL, tokenize.NEWLINE):
                prev_type = tok.type
    except (tokenize.TokenError, IndentationError):
        return src
    return " ".join(out)
