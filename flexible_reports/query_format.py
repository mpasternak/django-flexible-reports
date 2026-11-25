"""Re-indent a datasource query without changing what it means.

Backs the *Format* button of the datasource query editor. It works for both
query languages and for queries carrying Django template tags, because it never
parses the query -- it only moves the whitespace *between* tokens:

* string literals and template tags (``{{ value }}``, ``{% if x %}``, a whole
  ``{% comment %}...{% endcomment %}`` block) are copied verbatim,
* everything else is cut only at whitespace, parentheses and commas, so an
  operator such as ``>=`` or a dotted name such as ``author.name`` can never be
  split or have a space pushed into it.

One assumption is made about template tags: a ``{{ variable }}`` outside a
string literal renders to a whole value. Where the query itself contradicts
that -- the variable is joined to other text, as in ``{{ q }}A(B){{ q }}`` --
formatting is refused, because the tokens of the query as written would no
longer be the tokens of the query as rendered.

Whitespace between tokens is insignificant in django-dsl and in DjangoQL alike,
so the result compiles to the same filter. :func:`format_query` re-checks that
invariant on every call (:func:`significant_tokens` must be identical before and
after) and, for a DjangoQL query that parses, also that the AST is unchanged.

Layout: every ``and`` / ``or`` operand goes on its own line, the operator leads
the line, and a parenthesised group is broken out and indented once it grows
beyond :data:`INLINE_GROUP_WIDTH` characters::

    rok = 2020
    AND NOT (
        charakter IN ["KS", "KSP", "KSZ"]
        AND (typ_kbn = "000" OR typ_kbn="PNP")
    )
"""

from .query_backends import DJANGOQL, DSL

__all__ = ["QueryFormatError", "format_query", "significant_tokens"]

INDENT = "    "

#: Parentheses nested deeper than this are refused. No hand-written query comes
#: near it, and the layout code recurses once per level.
MAX_DEPTH = 100

#: A parenthesised group up to this many characters stays on one line.
INLINE_GROUP_WIDTH = 60

#: Logical operators are case-sensitive in both languages: DjangoQL reads
#: ``AND`` as a field name, django-dsl reads ``and`` as one.
LOGICAL = {
    DSL: frozenset(["AND", "OR"]),
    DJANGOQL: frozenset(["and", "or"]),
}

#: Quote characters that open a string literal. django-dsl knows only double
#: quotes and no escape sequences; DjangoQL has both quotes and backslashes.
QUOTES = {DSL: '"', DJANGOQL: "\"'"}
ESCAPES = {DSL: False, DJANGOQL: True}

_TEMPLATE_PAIRS = (("{{", "}}"), ("{%", "%}"), ("{#", "#}"))

ATOM = "atom"
OPEN = "("
CLOSE = ")"
COMMA = ","


class QueryFormatError(ValueError):
    """The query cannot be laid out safely (it is returned to no one)."""


def _template_end(query, pos):
    """Index just past the template tag starting at ``pos``, or ``None``."""
    for opening, closing in _TEMPLATE_PAIRS:
        if not query.startswith(opening, pos):
            continue
        end = query.find(closing, pos + 2)
        if end == -1:
            raise QueryFormatError("Unterminated template tag %r" % opening)
        end += 2
        # ``{% comment %}`` may carry a note: ``{% comment "why" %}``.
        if opening == "{%" and query[pos + 2 : end - 2].split()[:1] == ["comment"]:
            # The body of a comment block is not query text at all.
            stop = query.find("endcomment", end)
            stop = query.find("%}", stop) if stop != -1 else -1
            if stop == -1:
                raise QueryFormatError("Unterminated {% comment %} block")
            end = stop + 2
        return end
    return None


def _string_end(query, pos, escapes):
    quote = query[pos]
    i = pos + 1
    while i < len(query):
        template_end = _template_end(query, i)
        if template_end is not None:
            # ``"{{ name|default:"x" }}"``: quotes inside a tag do not close
            # the literal around it.
            i = template_end
            continue
        char = query[i]
        if escapes and char == "\\":
            i += 2
            continue
        if char == quote:
            return i + 1
        i += 1
    raise QueryFormatError("Unterminated string literal")


#: What may touch a ``{{ variable }}`` that sits outside a string literal,
#: besides whitespace: an opening bracket, a comma or an operator in front of
#: it (``rok>={{ rok }}``, ``[{{ a }},{{ b }}]``), their closing counterparts
#: behind it.
_BEFORE_VARIABLE = frozenset("(,=<>~![")
_AFTER_VARIABLE = frozenset("),=<>~!]")


def _check_variable_stands_alone(query, start, end):
    """Refuse a ``{{ variable }}`` glued to other text outside a literal.

    The formatter may only move whitespace that lies *between* tokens, and it
    finds tokens in the unrendered query. That holds as long as a variable
    renders to a whole value. Glued to text -- ``{{ q }}A(B){{ q }}`` with ``q``
    rendering to a quote -- it may be building a string literal out of pieces,
    and then the space this module would put before ``(B)`` lands *inside* the
    value. Nothing here can tell which it is, so such a query is not formatted.
    (Inside a quoted literal a variable is safe: the quotes are in the query.)
    """
    before = query[start - 1] if start > 0 else " "
    after = query[end] if end < len(query) else " "
    if (before.isspace() or before in _BEFORE_VARIABLE) and (
        after.isspace() or after in _AFTER_VARIABLE
    ):
        return
    raise QueryFormatError(
        "A template variable is joined to other text (%s); such a query "
        "cannot be formatted safely" % query[start:end]
    )


def _tokenize(query, language):
    """``[(kind, text)]`` with whitespace dropped.

    An atom is a maximal run of adjacent non-whitespace pieces, so
    ``impact_factor>=0`` and ``"{{ a }}"`` each stay one atom.
    """
    quotes = QUOTES[language]
    escapes = ESCAPES[language]
    tokens = []
    atom = []
    pos = 0

    def flush():
        if atom:
            tokens.append((ATOM, "".join(atom)))
            atom.clear()

    while pos < len(query):
        char = query[pos]
        if char.isspace():
            flush()
            pos += 1
            continue
        if char in "(),":
            flush()
            tokens.append((char, char))
            pos += 1
            continue
        end = _template_end(query, pos)
        if end is not None and char + query[pos + 1] == "{{":
            _check_variable_stands_alone(query, pos, end)
        if end is None and char in quotes:
            end = _string_end(query, pos, escapes)
        if end is None:
            end = pos + 1
        atom.append(query[pos:end])
        pos = end
    flush()
    return tokens


def significant_tokens(query, language=DSL):
    """The query as a list of token texts, whitespace between them removed.

    Two queries with equal lists differ only in layout.
    """
    return [text for kind, text in _tokenize(query, language)]


def _is_block_tag(text):
    return text.startswith("{%") and text.endswith("%}")


def _nest(tokens):
    """Fold the flat token list into nested lists, one per pair of parens."""
    root = []
    stack = [root]
    for kind, text in tokens:
        if kind == OPEN:
            if len(stack) > MAX_DEPTH:
                raise QueryFormatError(
                    "Parentheses are nested too deeply (more than %d levels)"
                    % MAX_DEPTH
                )
            group = []
            stack[-1].append(group)
            stack.append(group)
        elif kind == CLOSE:
            if len(stack) == 1:
                raise QueryFormatError("Unbalanced parentheses")
            stack.pop()
        else:
            stack[-1].append((kind, text))
    if len(stack) != 1:
        raise QueryFormatError("Unbalanced parentheses")
    return root


def _has_block_tag(items):
    for item in items:
        if isinstance(item, list):
            if _has_block_tag(item):
                return True
        elif item[0] == ATOM and _is_block_tag(item[1]):
            return True
    return False


def _join(parts):
    out = ""
    for part in parts:
        if not out or part == COMMA:
            out += part
        else:
            out += " " + part
    return out


def _inline(items):
    parts = []
    for item in items:
        if isinstance(item, list):
            parts.append("(" + _inline(item) + ")")
        else:
            parts.append(item[1])
    return _join(parts)


def _fits_inline(group):
    return not _has_block_tag(group) and len(_inline(group)) + 2 <= INLINE_GROUP_WIDTH


def _block(items, logical, depth):
    """Render ``items`` one operand per line, at indentation ``depth``."""
    pad = INDENT * depth
    lines = []
    current = []

    def flush():
        if current:
            lines.append(pad + _join(current))
            current.clear()

    for item in items:
        if isinstance(item, list):
            if _fits_inline(item):
                current.append("(" + _inline(item) + ")")
            else:
                inner = _block(item, logical, depth + 1)
                current.append("(\n" + inner + "\n" + pad + ")")
            continue
        kind, text = item
        if kind == ATOM and _is_block_tag(text):
            # ``{% if %}`` / ``{% endif %}`` / a comment block: a line of its own.
            flush()
            lines.append(pad + text)
        elif kind == ATOM and text in logical:
            flush()
            current.append(text)
        else:
            current.append(text)
    flush()
    return "\n".join(lines)


def _check_djangoql_ast(before, after):
    from djangoql.exceptions import DjangoQLError
    from djangoql.parser import DjangoQLParser

    try:
        ast_before = DjangoQLParser().parse(before)
    except DjangoQLError:
        # Not parseable as it stands (template tags, or simply invalid): the
        # token comparison is the only guarantee available.
        return
    try:
        ast_after = DjangoQLParser().parse(after)
    except DjangoQLError as e:
        raise QueryFormatError("Formatting would break the query (%s)" % e) from e
    try:
        changed = ast_before != ast_after
    except RecursionError as e:
        # A chain of a thousand conditions parses into a tree too deep to
        # compare. Unverified is not good enough here: refuse.
        raise QueryFormatError("The query is too long to format safely") from e
    if changed:
        raise QueryFormatError("Formatting would change the meaning of the query")


def format_query(query, language=DSL):
    """Return ``query`` re-indented; its meaning is guaranteed unchanged.

    Raises :class:`QueryFormatError` when the query cannot be laid out safely
    (an unterminated string or template tag, unbalanced parentheses). An empty
    query formats to an empty string.
    """
    if language not in LOGICAL:
        raise QueryFormatError("Unknown query language %r" % (language,))
    query = query or ""
    tokens = _tokenize(query, language)
    formatted = _block(_nest(tokens), LOGICAL[language], 0)

    if significant_tokens(formatted, language) != [text for kind, text in tokens]:
        # Cannot happen by construction; if it ever does, refuse rather than
        # hand back a query that means something else.
        raise QueryFormatError("Formatting would change the tokens of the query")
    if language == DJANGOQL:
        _check_djangoql_ast(query, formatted)
    return formatted
