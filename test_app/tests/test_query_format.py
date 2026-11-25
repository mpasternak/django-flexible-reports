import pytest

from flexible_reports.query_format import (
    QueryFormatError,
    format_query,
    significant_tokens,
)

# Shaped like the queries real reports carry: lists in brackets, template
# block tags, a parameter, operators glued to their operands.
DSL_QUERY = """typ IN ["aut.", "Aut. koresp."] AND charakter IN ["KSZ", "KS"]
AND NOT (charakter IN ["KS", "KSP", "KSZ"] AND (typ_kbn = "000" OR typ_kbn="PNP"))
{% if punktuj %} AND punkty>0 {% endif %} AND autor = {{ obiekt.pk }}"""

DSL_FORMATTED = """typ IN ["aut.", "Aut. koresp."]
AND charakter IN ["KSZ", "KS"]
AND NOT (
    charakter IN ["KS", "KSP", "KSZ"]
    AND (typ_kbn = "000" OR typ_kbn="PNP")
)
{% if punktuj %}
AND punkty>0
{% endif %}
AND autor = {{ obiekt.pk }}"""

DJANGOQL_QUERY = (
    'year >= 2020 and (kind.short = "art" or kind.short = "mon" '
    'or title ~ "a long enough title to push this group over the limit") '
    "and status in (1,2 , 3)"
)

DJANGOQL_FORMATTED = """year >= 2020
and (
    kind.short = "art"
    or kind.short = "mon"
    or title ~ "a long enough title to push this group over the limit"
)
and status in (1, 2, 3)"""


def test_format_dsl_query():
    assert format_query(DSL_QUERY, "dsl") == DSL_FORMATTED


def test_format_djangoql_query():
    assert format_query(DJANGOQL_QUERY, "djangoql") == DJANGOQL_FORMATTED


@pytest.mark.parametrize(
    "query,language",
    [(DSL_QUERY, "dsl"), (DJANGOQL_QUERY, "djangoql")],
)
def test_format_changes_layout_only(query, language):
    formatted = format_query(query, language)
    assert significant_tokens(formatted, language) == significant_tokens(
        query, language
    )


@pytest.mark.parametrize(
    "query,language",
    [(DSL_QUERY, "dsl"), (DJANGOQL_QUERY, "djangoql")],
)
def test_format_is_idempotent(query, language):
    formatted = format_query(query, language)
    assert format_query(formatted, language) == formatted


def test_format_keeps_djangoql_ast():
    from djangoql.parser import DjangoQLParser

    parse = DjangoQLParser().parse
    assert parse(format_query(DJANGOQL_QUERY, "djangoql")) == parse(DJANGOQL_QUERY)


def test_format_leaves_string_contents_alone():
    # Whitespace, parentheses, commas and keywords inside a literal are data.
    query = 'title ~ "a  (b , c)  and  d" and x = 1'
    assert format_query(query, "djangoql") == (
        'title ~ "a  (b , c)  and  d"\nand x = 1'
    )


def test_format_djangoql_escaped_quote_does_not_end_the_string():
    query = r'title = "say \"and\" twice" and x = 1'
    assert format_query(query, "djangoql") == (
        r'title = "say \"and\" twice"' + "\nand x = 1"
    )


def test_format_keeps_template_tags_verbatim():
    query = 'a = {{  obj.pk  }} AND b = "{{ name|default:"x y" }}"'
    assert format_query(query, "dsl") == (
        'a = {{  obj.pk  }}\nAND b = "{{ name|default:"x y" }}"'
    )


def test_format_keeps_comment_block_verbatim():
    comment = "{% comment %}\n  not (a query) AND at all\n{% endcomment %}"
    query = "a = 1 AND " + comment + " b = 2"
    assert format_query(query, "dsl") == "a = 1\nAND\n" + comment + "\nb = 2"


def test_format_keeps_comment_block_with_a_note_verbatim():
    # ``{% comment "note" %}`` is the same block tag; an apostrophe or an
    # unbalanced parenthesis in its body must not be read as query text.
    comment = '{% comment "why" %}\n  don\'t (touch\n{% endcomment %}'
    query = "a = 1 AND " + comment + " b = 2"
    assert format_query(query, "djangoql") == "a = 1 AND\n" + comment + "\nb = 2"


def test_logical_keywords_are_case_sensitive_per_language():
    # ``and`` is a plain field name to django-dsl, ``AND`` one to DjangoQL --
    # neither may be treated as an operator and moved to a new line.
    assert format_query("and = 1 AND or = 2", "dsl") == "and = 1\nAND or = 2"
    assert format_query("AND = 1 and OR = 2", "djangoql") == "AND = 1\nand OR = 2"


def test_format_does_not_split_glued_operators():
    assert format_query("a>=1 AND b<=2", "dsl") == "a>=1\nAND b<=2"
    assert format_query("a.b!=1 and c!~2", "djangoql") == "a.b!=1\nand c!~2"


def test_format_empty_query():
    assert format_query("", "dsl") == ""
    assert format_query("  \n ", "djangoql") == ""
    assert format_query(None, "dsl") == ""


@pytest.mark.parametrize(
    "query",
    [
        'a = "unterminated',
        "a = 1 AND (b = 2",
        "a = 1) AND b = 2",
        "a = {{ unterminated",
        "{% comment %} never closed",
    ],
)
def test_format_refuses_what_it_cannot_lay_out(query):
    with pytest.raises(QueryFormatError):
        format_query(query, "dsl")


def test_format_unknown_language():
    with pytest.raises(QueryFormatError):
        format_query("a = 1", "sql")


def test_format_refuses_absurdly_deep_nesting():
    # Deep enough to exhaust the interpreter's recursion limit if it were laid
    # out; it must be refused with a message, not crash the view.
    query = "(" * 3000 + "a = 1" + ")" * 3000
    with pytest.raises(QueryFormatError, match="nested too deeply"):
        format_query(query, "dsl")


def test_format_still_handles_reasonable_nesting():
    query = "(" * 50 + "a = 1 and b = 2" + ")" * 50
    formatted = format_query(query, "djangoql")
    assert significant_tokens(formatted, "djangoql") == significant_tokens(
        query, "djangoql"
    )
    assert format_query(formatted, "djangoql") == formatted


def test_format_very_long_djangoql_chain_does_not_crash():
    # Thousands of conditions parse into a tree too deep to compare; the
    # outcome may be a refusal, never an unhandled RecursionError.
    query = " and ".join("a = %d" % i for i in range(3000))
    try:
        formatted = format_query(query, "djangoql")
    except QueryFormatError:
        return
    assert significant_tokens(formatted, "djangoql") == significant_tokens(
        query, "djangoql"
    )


@pytest.mark.parametrize(
    "query",
    [
        # ``q`` may render to a quote: the parentheses would then be part of a
        # string value, and spacing them out would change that value.
        "title = {{ q }}A(B){{ q }}",
        "title = {{ q }}A (B)",
        "title = A(B){{ q }}",
        "title = x{{ a }}",
        "title = {{ a }}{{ b }}",
    ],
)
@pytest.mark.parametrize("language", ["dsl", "djangoql"])
def test_format_refuses_a_variable_joined_to_text(query, language):
    with pytest.raises(QueryFormatError, match="joined to other text"):
        format_query(query, language)


@pytest.mark.parametrize(
    "query,expected",
    [
        ("a = {{ obj.pk }} AND b = 1", "a = {{ obj.pk }}\nAND b = 1"),
        ("a>={{ year }} AND b = 1", "a>={{ year }}\nAND b = 1"),
        ("a IN [{{ x }},{{ y }}] AND b = 1", "a IN [{{ x }}, {{ y }}]\nAND b = 1"),
        ("(a = {{ x }}) AND b = 1", "(a = {{ x }})\nAND b = 1"),
        ('a = "{{ q }}A(B){{ q }}" AND b = 1', 'a = "{{ q }}A(B){{ q }}"\nAND b = 1'),
    ],
)
def test_format_accepts_variables_that_stand_alone(query, expected):
    assert format_query(query, "dsl") == expected


def test_rendered_query_is_unchanged_by_formatting():
    # The property the refusal above protects: rendering the formatted query
    # yields the same tokens as rendering the original one.
    from django.template import Context, Template

    query = 'a = {{ x }} AND (b = "{{ y }} (z)" OR c IN [{{ x }},{{ x }}])'
    context = Context({"x": 5, "y": "p  q"}, autoescape=False)
    before = Template(query).render(context)
    after = Template(format_query(query, "dsl")).render(context)
    assert significant_tokens(after, "dsl") == significant_tokens(before, "dsl")
