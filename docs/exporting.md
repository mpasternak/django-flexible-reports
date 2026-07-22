# Exporting

The renderer lives in `flexible_reports.adapters.django_tables2` and offers
four entry points. All of them take a report that has already been given a base
queryset, and a **parent context**:

```python
from django.template import Context

from flexible_reports.adapters.django_tables2 import (
    as_docx,
    as_html,
    as_tablib_databook,
    as_tablib_dataset,
)

report.set_base_queryset(Book.objects.select_related("author"))
report.set_context({"min_pages": 300})

parent_context = Context({"request": request})
```

!!! important

    `parent_context` must be a `django.template.Context` (or
    `RequestContext`), **not** a plain dict -- a dict raises
    `AttributeError: 'dict' object has no attribute 'render_context'`. It must
    contain `request`.

    Inside a template you never deal with this: `{% flexible report %}` passes
    the real template context for you.

## HTML

```python
html = as_html(report, parent_context)
```

Renders `Report.template` and returns safe HTML. This is exactly what
`{% flexible report %}` calls.

## Word (`.docx`)

```python
tmp = as_docx(report, parent_context)
```

Renders the report to HTML, strips it down to a whitelist of tags with
[bleach][bleach], then converts it with [pandoc][pandoc] (through
[pypandoc][pypandoc]).

Returns an **open** `NamedTemporaryFile` created with `delete=False` -- the
file survives garbage collection and it is your job to remove it:

```python
from django.http import FileResponse

tmp = as_docx(report, Context({"request": request}))
response = FileResponse(
    open(tmp.name, "rb"),
    as_attachment=True,
    filename="report.docx",
    content_type=(
        "application/vnd.openxmlformats-officedocument"
        ".wordprocessingml.document"
    ),
)
# ... and delete tmp.name once the response has been sent.
```

The tag whitelist defaults to tables, headings and basic inline formatting
(`table`, `tr`, `td`, `th`, `b`, `i`, `u`, `sup`, `sub`, `h1`--`h4`, `em`,
`strong`, `strike`, `font`) with `{"td": ["colspan"]}` for attributes; notably
`<a>` is dropped, which is what removes django-tables2's sorting links from the
headers. Override `allowed_tags` / `allowed_attributes` if you need more.

Requires the `pandoc` binary on the machine.

[bleach]: https://pypi.org/project/bleach/
[pandoc]: https://pandoc.org/
[pypandoc]: https://pypi.org/project/pypandoc/

## Spreadsheets (tablib)

### `as_tablib_databook` -- one sheet per element

```python
databook = as_tablib_databook(report, parent_context)
databook.export("xlsx")
```

Each report element becomes one [tablib][tablib] `Dataset` with proper headers,
added to the `Databook` under the element's title **truncated to 31
characters** (the Excel sheet-name limit).

### `as_tablib_dataset` -- everything in one sheet

```python
dataset = as_tablib_dataset(report, parent_context)
dataset.export("csv")
```

One flat `Dataset`. Element titles are added as tablib *separators*, and each
element contributes its **header row as an ordinary data row**, so the output
looks like:

```text
Nr,Title,Author,Country,Year,Price     <- header row of element 1
1,Going Postal484 pages,...
2,Small Gods400 pages,...
Nr,Title,Author,Country,Year,Price     <- header row of element 2
1,The Dispossessed341 pages,...
```

Use `as_tablib_databook` if you want one clean table per element.

!!! note

    Writing `xlsx` needs openpyxl, which tablib does not pull in by default
    and which this package does not depend on. Install `tablib[xlsx]` (or
    `openpyxl`) if you export to Excel. `csv`, `json`, `yaml` and
    `tsv` work out of the box.

[tablib]: https://tablib.readthedocs.io/

## Controlling what gets exported

Two per-column switches shape non-HTML output:

`exclude_from_export`
:   Leave this column out of exports entirely. Useful for purely decorative
    columns (row numbers, action links).

`strip_html_on_export` (on by default)
:   Run the rendered cell through `lxml.html`'s `text_content()`, so
    `<strong>Going Postal</strong><br><small>484 pages</small>` exports as
    `Going Postal484 pages`.

    Note that stripping concatenates the text nodes without inserting
    whitespace: if a cell template stacks values with `<br>` and you care
    about the exported text, put a separator (a space, a dash) into the
    template itself.
