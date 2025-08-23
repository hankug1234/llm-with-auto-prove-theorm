def _get_result(script: str, pattern : str):
    from html import unescape
    import re
    if script is None:
        return None

    pat = re.compile(pattern, re.IGNORECASE)
    m = pat.search(script)
    if m:
        return m.group(1).strip()

    s2 = unescape(script)
    if s2 != script:
        m = pat.search(s2)
        if m:
            return m.group(1).strip()

    s3 = re.sub(r"\x1b\[[0-9;]*m", "", s2)
    if s3 != s2:
        m = pat.search(s3)
        if m:
            return m.group(1).strip()

    return None

if __name__ == "__main__":
    FAIL = r"<\s*FAIL\s*>([\s\S]*?)<\s*/\s*FAIL\s*>"
    text = "<FAIL> The open branches demonstrate a contradiction: they consistently assert both Human(V*) and ¬Human(V*) for various variables V*. This contradiction arises from the initial premises and the attempt to formalize the LLM's response. The premises do not allow for a consistent assignment of truth values to the variable 'you' as both Human and not Human. The original answer's formalization is therefore flawed and cannot be revised without introducing new, unsupported axioms. </FAIL>"
    print(_get_result(text,FAIL))