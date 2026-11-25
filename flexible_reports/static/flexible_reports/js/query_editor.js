/*
 * Query editor for the datasource admin form.
 *
 * Upgrades every <textarea class="flexible-reports-query"> in place. The
 * textarea stays the real form field -- with JavaScript off, or if anything
 * here fails, the form works exactly as before.
 *
 *   - Syntax colouring for both query languages (django-dsl and DjangoQL) and
 *     for the Django template tags a query may carry. It is the usual
 *     transparent-textarea trick: a coloured copy of the text sits right
 *     behind the field. No editor library is involved.
 *   - A "Format" button. The layout is computed on the server
 *     (flexible_reports.query_format), which guarantees the query keeps its
 *     meaning.
 *   - For DjangoQL: field and value completion by the widget that ships with
 *     djangoql (window.DjangoQL), fed with the schema of the model chosen in
 *     "Base model". Changing the model reloads the schema.
 *   - For django-dsl: a list of the model's fields and shortcuts under the
 *     field; clicking a name inserts it.
 *
 * FlexibleReportsQueryEditor.tokenize(text, language) is exported so the
 * tokenizer can be tested without a DOM.
 */
(function (root, factory) {
  "use strict";
  var api = factory(root);
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.FlexibleReportsQueryEditor = api;
  }
})(typeof window !== "undefined" ? window : this, function (window) {
  "use strict";

  var TEMPLATE = /^(\{\{[\s\S]*?\}\}|\{%[\s\S]*?%\}|\{#[\s\S]*?#\})/;
  var WS = /^\s+/;

  // Order matters: keywords before names, two-character operators before
  // one-character ones, dates and floats before integers.
  var PATTERNS = {
    djangoql: [
      ["string", /^"(\\.|[^"\\\n])*"/],
      ["string", /^'(\\.|[^'\\\n])*'/],
      ["number", /^-?\d+(\.\d+)?([eE][+-]?\d+)?/],
      ["operator", /^(!=|>=|<=|!~)/],
      ["logical", /^(and|or|not)(?![_0-9A-Za-z])/],
      ["operator", /^(in|startswith|endswith)(?![_0-9A-Za-z])/],
      ["constant", /^(True|False|None)(?![_0-9A-Za-z])/],
      ["operator", /^(=|>|<|~)/],
      ["paren", /^[()]/],
      ["comma", /^,/],
      // The optional trailing dot is the moment between typing "author."
      // and picking a field: not worth an error squiggle.
      ["name", /^[_A-Za-z][_0-9A-Za-z]*(\.[_A-Za-z][_0-9A-Za-z]*)*\.?/],
    ],
    dsl: [
      ["string", /^"[^"]*"/],
      ["number", /^\d{4}-\d{1,2}-\d{1,2}/],
      ["number", /^\d+/],
      ["logical", /^(AND|OR|NOT)(?![_0-9A-Za-z])/],
      ["operator", /^IN(?![_0-9A-Za-z])/],
      ["constant", /^NULL(?![_0-9A-Za-z])/],
      ["operator", /^(>=|<=|~~|=|>|<|~)/],
      ["paren", /^[()[\]]/],
      ["comma", /^,/],
      ["name", /^[_A-Za-z][_0-9A-Za-z]*/],
    ],
  };

  function tokenize(text, language) {
    var patterns = PATTERNS[language] || PATTERNS.dsl;
    var all = [["ws", WS], ["template", TEMPLATE]].concat(patterns);
    var tokens = [];
    var pos = 0;
    text = String(text == null ? "" : text);
    while (pos < text.length) {
      var rest = text.slice(pos);
      var matched = false;
      for (var i = 0; i < all.length; i++) {
        var m = all[i][1].exec(rest);
        if (m && m[0].length) {
          tokens.push({ type: all[i][0], value: m[0] });
          pos += m[0].length;
          matched = true;
          break;
        }
      }
      if (!matched) {
        // A character neither language knows. One token per character, so
        // the loop always advances.
        tokens.push({ type: "error", value: text.charAt(pos) });
        pos += 1;
      }
    }
    return tokens;
  }

  var ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;" };

  function escapeHtml(s) {
    return s.replace(/[&<>]/g, function (c) {
      return ESCAPES[c];
    });
  }

  function renderHtml(text, language) {
    // Token types come from the fixed tables above and every value is
    // escaped, so nothing typed into the field can end up as markup.
    var tokens = tokenize(text, language);
    var html = "";
    for (var i = 0; i < tokens.length; i++) {
      html +=
        '<span class="fr-tok-' +
        tokens[i].type +
        '">' +
        escapeHtml(tokens[i].value) +
        "</span>";
    }
    // A trailing newline has no height of its own; without this the copy
    // would end one line short of the textarea.
    if (text.charAt(text.length - 1) === "\n") {
      html += " ";
    }
    return html;
  }

  var api = { tokenize: tokenize, renderHtml: renderHtml };
  if (!window || !window.document) {
    return api;
  }
  var document = window.document;

  // Font and box metrics the coloured copy has to share with the textarea
  // for the two texts to sit exactly on top of each other.
  var SYNCED = [
    "fontFamily", "fontSize", "fontWeight", "fontStyle", "lineHeight",
    "letterSpacing", "wordSpacing", "textIndent", "tabSize",
    "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
    "borderTopWidth", "borderRightWidth", "borderBottomWidth",
    "borderLeftWidth",
  ];

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text) {
      node.textContent = text;
    }
    return node;
  }

  function insertAtCaret(textarea, text) {
    textarea.focus();
    // execCommand keeps the browser's undo history intact, which assigning
    // to .value does not; it is deprecated but still the only way to do so.
    var done = false;
    try {
      done = document.execCommand("insertText", false, text);
    } catch (e) {
      done = false;
    }
    if (!done) {
      textarea.setRangeText(
        text, textarea.selectionStart, textarea.selectionEnd, "end"
      );
      textarea.dispatchEvent(new window.Event("input", { bubbles: true }));
    }
  }

  function attach(textarea) {
    if (!textarea || textarea.dataset.frQueryEditor === "on") {
      return null;
    }
    textarea.dataset.frQueryEditor = "on";

    var form = textarea.form;
    var languageField = form && form.elements.query_language;
    var modelField = form && form.elements.base_model;

    function language() {
      return languageField && languageField.value === "djangoql"
        ? "djangoql"
        : "dsl";
    }

    // ---- colouring ------------------------------------------------------

    var textColor = window.getComputedStyle(textarea).color;
    var wrapper = el("div", "fr-query-editor");
    var backdrop = el("div", "fr-query-backdrop");
    var code = el("div", "fr-query-code");
    backdrop.appendChild(code);
    textarea.parentNode.insertBefore(wrapper, textarea);
    wrapper.appendChild(backdrop);
    wrapper.appendChild(textarea);
    textarea.classList.add("fr-query-input");
    // The field's own text is transparent: keep the caret visible and give
    // uncoloured characters the colour the field had.
    textarea.style.caretColor = textColor;
    backdrop.style.color = textColor;

    function syncMetrics() {
      var cs = window.getComputedStyle(textarea);
      for (var i = 0; i < SYNCED.length; i++) {
        backdrop.style[SYNCED[i]] = cs[SYNCED[i]];
      }
      // clientWidth leaves out the vertical scrollbar, so the copy wraps at
      // the same column as the textarea whether or not one is showing.
      var borders =
        parseFloat(cs.borderLeftWidth) + parseFloat(cs.borderRightWidth);
      backdrop.style.width = textarea.clientWidth + borders + "px";
      backdrop.style.height = textarea.offsetHeight + "px";
    }

    function syncScroll() {
      code.style.transform =
        "translate(" + -textarea.scrollLeft + "px, " + -textarea.scrollTop + "px)";
    }

    function paint() {
      code.innerHTML = renderHtml(textarea.value, language());
      syncMetrics();
      syncScroll();
    }

    textarea.addEventListener("input", paint);
    // The completion widget replaces the value on Enter/Tab without firing
    // "input"; repaint on keyup so accepted text is never left uncoloured.
    textarea.addEventListener("keyup", paint);
    textarea.addEventListener("scroll", syncScroll);
    window.addEventListener("resize", paint);
    if (window.ResizeObserver) {
      // The user dragging the textarea's resize handle.
      new window.ResizeObserver(syncMetrics).observe(textarea);
    }

    // Where the caret is on screen, read off the coloured copy (a textarea
    // cannot be asked). Null when it cannot be worked out.
    function caretRect() {
      var offset = textarea.selectionStart;
      var walker = document.createTreeWalker(code, window.NodeFilter.SHOW_TEXT);
      var node = walker.nextNode();
      while (node && offset > node.length) {
        offset -= node.length;
        node = walker.nextNode();
      }
      if (!node) {
        return null;
      }
      var range = document.createRange();
      range.setStart(node, offset);
      range.setEnd(node, offset);
      var rects = range.getClientRects();
      return rects.length ? rects[rects.length - 1] : null;
    }

    // ---- toolbar: Format --------------------------------------------------

    var toolbar = el("div", "fr-query-toolbar");
    var formatButton = el(
      "button",
      // "button" is the Django admin's button class, "grp-button" grappelli's.
      "button grp-button fr-query-format",
      textarea.dataset.labelFormat || "Format"
    );
    formatButton.type = "button";
    var status = el("span", "fr-query-status");
    status.setAttribute("role", "status");
    toolbar.appendChild(formatButton);
    toolbar.appendChild(status);
    wrapper.parentNode.insertBefore(toolbar, wrapper.nextSibling);

    function csrfToken() {
      var input = form && form.elements.csrfmiddlewaretoken;
      return input ? input.value : "";
    }

    function formatFailed(detail) {
      var label =
        textarea.dataset.labelFormatFailed || "The query could not be formatted";
      status.textContent = detail ? label + ": " + detail : label;
      status.classList.add("fr-query-status-error");
    }

    formatButton.addEventListener("click", function () {
      var body = new window.URLSearchParams();
      body.append("q", textarea.value);
      body.append("language", language());
      status.textContent = "";
      status.classList.remove("fr-query-status-error");
      formatButton.disabled = true;
      window
        .fetch(textarea.dataset.formatUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-CSRFToken": csrfToken() },
          body: body,
        })
        .then(function (response) {
          return response.json().then(function (data) {
            return { ok: response.ok, data: data };
          });
        })
        .then(function (result) {
          if (result.ok && typeof result.data.formatted === "string") {
            textarea.value = result.data.formatted;
            paint();
          } else {
            formatFailed(result.data && result.data.error);
          }
        })
        .catch(function () {
          formatFailed("");
        })
        .then(function () {
          formatButton.disabled = false;
        });
    });

    // ---- django-dsl: list of fields and shortcuts -------------------------

    var hints = el("details", "fr-query-hints");
    var hintsSummary = el("summary");
    var hintsBody = el("div", "fr-query-hints-body");
    hints.appendChild(hintsSummary);
    hints.appendChild(hintsBody);
    hints.hidden = true;
    toolbar.parentNode.insertBefore(hints, toolbar.nextSibling);

    function hintButton(name, title) {
      var button = el("button", "fr-query-hint", name);
      button.type = "button";
      if (title) {
        button.title = title;
      }
      button.addEventListener("click", function () {
        insertAtCaret(textarea, name);
      });
      return button;
    }

    var dslSchema = null;

    function renderHints() {
      hintsBody.textContent = "";
      var show =
        language() === "dsl" && dslSchema && dslSchema.fields.length > 0;
      hints.hidden = !show;
      if (!show) {
        return;
      }
      hintsSummary.textContent =
        (textarea.dataset.labelFields || "Available fields") +
        " (" + dslSchema.fields.length + ")";
      var i;
      for (i = 0; i < dslSchema.fields.length; i++) {
        hintsBody.appendChild(hintButton(dslSchema.fields[i]));
      }
      var shortcuts = Object.keys(dslSchema.shortcuts || {}).sort();
      if (shortcuts.length) {
        hintsBody.appendChild(
          el(
            "div", "fr-query-hints-title",
            textarea.dataset.labelShortcuts || "Shortcuts"
          )
        );
        for (i = 0; i < shortcuts.length; i++) {
          hintsBody.appendChild(
            hintButton(shortcuts[i], String(dslSchema.shortcuts[shortcuts[i]]))
          );
        }
      }
    }

    // ---- DjangoQL: completion ---------------------------------------------

    var completion = null;
    var EMPTY_SCHEMA = { current_model: "", models: {} };

    function setCompletionSchema(introspections) {
      if (!window.DjangoQL) {
        return; // djangoql is not an installed app: no widget to drive
      }
      if (completion) {
        completion.loadIntrospections(introspections);
        return;
      }
      completion = new window.DjangoQL({
        introspections: introspections,
        selector: textarea,
        autoResize: false,
        completionEnabled: language() === "djangoql",
        // The widget was written for a one-line search box and submits the
        // form on Enter. In a multi-line editor Enter is a line break.
        onSubmit: function () {
          insertAtCaret(textarea, "\n");
        },
      });
      followCaret(completion.completion);
      // Picking a suggestion with the mouse changes the value with no event
      // the colouring could listen to.
      var select = completion.selectCompletion;
      completion.selectCompletion = function () {
        var result = select.apply(this, arguments);
        paint();
        return result;
      };
    }

    // The widget hangs its popup under the bottom edge of the textarea --
    // right for a one-line search box, a long way from the text in an editor
    // this tall. Whenever it (re)positions the popup, move it to the caret.
    function followCaret(popup) {
      if (!popup || !window.MutationObserver) {
        return;
      }
      new window.MutationObserver(function () {
        if (popup.style.display === "none") {
          return;
        }
        var rect = caretRect();
        var box = textarea.getBoundingClientRect();
        if (!rect || rect.bottom < box.top || rect.bottom > box.bottom) {
          return; // caret scrolled out of view: leave the popup where it is
        }
        var top = Math.round(rect.bottom + window.pageYOffset + 2) + "px";
        // Writing the same value again would not fire the observer, but an
        // unconditional write would: only touch the style when it differs.
        if (popup.style.top !== top) {
          popup.style.top = top;
        }
      }).observe(popup, { attributes: true, attributeFilter: ["style"] });
    }

    function applyLanguage() {
      if (completion) {
        if (language() === "djangoql") {
          completion.enableCompletion();
        } else {
          completion.disableCompletion();
        }
      }
      renderHints();
      paint();
    }

    var schemaRequest = 0;

    function loadSchema() {
      var model = modelField && modelField.value;
      var request = ++schemaRequest;
      dslSchema = null;
      if (!model || !textarea.dataset.schemaUrl) {
        setCompletionSchema(EMPTY_SCHEMA);
        renderHints();
        return;
      }
      var url =
        textarea.dataset.schemaUrl + "?base_model=" + encodeURIComponent(model);
      window
        .fetch(url, { credentials: "same-origin" })
        .then(function (response) {
          if (!response.ok) {
            throw new Error("HTTP " + response.status);
          }
          return response.json();
        })
        .then(function (data) {
          if (request !== schemaRequest) {
            return; // the model was changed again in the meantime
          }
          dslSchema = data.dsl || null;
          setCompletionSchema(data.djangoql || EMPTY_SCHEMA);
          applyLanguage();
        })
        .catch(function (error) {
          if (request !== schemaRequest) {
            return;
          }
          // Without a schema the field is still a working, coloured
          // textarea; say why the suggestions are missing and carry on.
          window.console.error("flexible_reports query editor:", error);
          setCompletionSchema(EMPTY_SCHEMA);
          renderHints();
        });
    }

    if (languageField) {
      languageField.addEventListener("change", applyLanguage);
    }
    if (modelField) {
      modelField.addEventListener("change", loadSchema);
    }

    paint();
    loadSchema();

    return { repaint: paint, reloadSchema: loadSchema };
  }

  function init() {
    var nodes = document.querySelectorAll("textarea.flexible-reports-query");
    for (var i = 0; i < nodes.length; i++) {
      attach(nodes[i]);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  api.attach = attach;
  return api;
});
