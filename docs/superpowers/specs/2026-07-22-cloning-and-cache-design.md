# Klonowanie tabel i raportów + usunięcie cache'u tabel

Data: 2026-07-22
Status: zaakceptowana, po review

## Cel

Trzy niezależne zmiany w `django-flexible-reports`:

1. Możliwość sklonowania `Table` (wraz z kolumnami i kolejnością sortowania).
2. Możliwość sklonowania `Report` (wraz z jego elementami).
3. Naprawa błędu: zmiana `label` w bazie nie jest widoczna bez restartu procesu
   Django.

Wersje zweryfikowane w `.venv`: Django 6.0.7, django-tables2 3.0.0.

## Kontekst — diagnoza błędu z punktu 3

`flexible_reports/adapters/django_tables2.py` trzyma moduł-globalny słownik:

```python
_table_cache = {}

def _table(table):
    global _table_cache
    if table.pk not in _table_cache:
        ...
        _table_cache[table.pk] = AdHocTable
    return _table_cache[table.pk]
```

Cache jest kluczowany wyłącznie po `table.pk` i **nie ma żadnej inwalidacji**.
Raz zbudowana klasa `AdHocTable` — zawierająca `verbose_name` kolumn, `attrs`,
`empty_text`, `order_by` i `prefix` — żyje do końca procesu. Wprowadził to
commit `40d9da4 "Speedups"`.

Konsekwencje:

- Zmiana `Column.label` lub `Table.label` wymaga restartu procesu.
- Usunięcie kolumny również nie działa — `base_columns` zapamiętanej klasy nadal
  ją zawiera.
- Przy wielu workerach zachowanie jest niedeterministyczne: edycja w adminie
  trafia do jednego procesu, pozostałe serwują stare nagłówki. Użytkownik widzi
  raz stare, raz nowe dane, zależnie od tego, który worker obsłuży żądanie.
  Z tego powodu inwalidacja sygnałem `post_save` w pamięci procesu **nie
  wystarcza** — naprawiłaby tylko jeden worker.

### Pomiar: ile ten cache jest wart

Benchmark na tabeli 8 kolumn typu `TemplateColumn` z szablonem `{{ value }}`
(sqlite in-memory, Python 3.13, django-tables2 3.0.0):

| | 20 wierszy | 100 | 500 | 1000 |
|---|---|---|---|---|
| Budowa klasy `AdHocTable` (to, co cache oszczędza) | 0,48 ms | 0,46 ms | 0,46 ms | 0,45 ms |
| Instancjacja (`deepcopy base_columns`, zawsze) | 0,22 ms | 0,20 ms | 0,18 ms | 0,17 ms |
| Pełny render tabeli do HTML | 6,4 ms | 30,5 ms | 172,7 ms | 312,6 ms |
| **Udział cache'u w renderze** | 7,4% | 1,5% | 0,27% | 0,14% |

Oszczędność jest stała (~0,46 ms + 2 zapytania SQL), a koszt renderu rośnie
liniowo z liczbą wierszy. Im większy raport, tym cache mniej znaczy.

Powód jest strukturalny, potwierdzony w źródłach `django_tables2`:

- `Table.__init__` (`tables.py:318`) wykonuje `copy.deepcopy(type(self).base_columns)`
  przy **każdej** instancjacji. Zapamiętanie klasy nie omija tego deepcopy.
- `TemplateColumn.render()` (`columns/templatecolumn.py:116`) wykonuje
  `Template(self.template_code)` przy **każdej komórce**. Dla tabeli 500×8 to
  4000 kompilacji szablonu na jeden render; cache klasy nie eliminuje z tego nic.

### Prawdziwy hot-spot

Prototyp kompilujący szablon raz zamiast per komórka, ta sama tabela 500×8:

```
Render obecny (kompilacja per komórka):     151,4 ms
Render z szablonem kompilowanym raz:        113,3 ms
  -> 1,34x szybciej (oszczędność 38,1 ms)

Dla porównania _table_cache oszczędza:         0,46 ms
```

Zysk jest ~83x większy niż z cache'u, który psuje nagłówki — i to przy
najprostszym możliwym szablonie. Przy bogatszych szablonach różnica rośnie,
bo kompilacja jest droższa.

### Decyzja

Usuwamy `_table_cache` całkowicie i w zamian cache'ujemy kompilację szablonu
kolumny. Netto render będzie **szybszy niż obecnie**, mimo usunięcia cache'u,
a nagłówki będą zawsze świeże we wszystkich procesach.

Odrzucone alternatywy:

- **Inwalidacja sygnałem `post_save`** — nie działa przy wielu workerach.
- **Klucz wersjonowany `(pk, Table.modified)`** — poprawne między procesami, ale
  wymaga nowego pola, migracji i sygnałów z `Column`/`ColumnOrder`, żeby
  uratować 0,46 ms. Nadinżynieria wobec zmierzonych liczb.

Usunięcie cache'u jest bezpieczne: jedynym konsumentem jest
`templatetags/flexible_reports_tags.py:12` -> `as_html` -> `table()`
(`adapters/django_tables2.py:148-149`), który natychmiast instancjuje klasę i
nigdzie jej nie przechowuje. Nic nie zależy od tożsamości (identity) zwracanej
klasy. Prefiks sortowania pochodzi ze stanu w bazie
(`SortIndividually.get_prefix` -> `table.pk`), więc przebudowana klasa zachowuje
się identycznie przy sortowaniu i paginacji z querystringa.

## Nazewnictwo klonów (wspólne dla A i B)

Sufiks musi być **tłumaczalny**. Cały pakiet używa angielskich `msgid` pod
`gettext_lazy` i ma polskie tłumaczenie w
`flexible_reports/locale/pl/LC_MESSAGES/django.po` (71 msgidów). Pakiet jest
publikowany na PyPI z angielskimi klasyfikatorami i README, więc zaszycie
polskiego „kopia" w danych byłoby błędem dla każdego nieanglojęzycznego
wdrożenia.

- msgid: `"copy"`, tłumaczenie pl: `"kopia"`.
- Etykieta: `"X (copy)"`, kolejne `"X (copy 2)"`, `"X (copy 3)"`.
- **Klon klonu**: z etykiety źródłowej najpierw **zdejmujemy** istniejący sufiks
  (regex zbudowany z aktualnego tłumaczenia), więc klon `"X (copy)"` daje
  `"X (copy 2)"`, a nie `"X (copy) (copy)"`. Gdy etykieta powstała przy innym
  aktywnym języku, regex nie dopasuje się i dostaniemy zagnieżdżony sufiks —
  degradacja jest kosmetyczna i akceptowana.
- Numer wybieramy jako pierwszy wolny, sprawdzając istniejące wartości w bazie.
  Skan jest **wyścigowy**: dwa równoczesne klonowania mogą wyliczyć tę samą
  nazwę. Żadne pole nie ma `unique=True`, więc nie ma wyjątku — powstaną dwie
  identyczne etykiety. Akceptujemy to świadomie; klonowanie to operacja
  administracyjna wykonywana ręcznie.

Slug (`Report.slug`, `SlugField()` czyli `max_length=50`, `models/report.py:105`):

- sufiks `-copy`, `-copy-2`, ... (slugifikowany, żeby zniósł tłumaczenia z
  diakrytykami);
- **skracamy rdzeń**, nie całość: rdzeń jest przycinany tak, by
  `len(rdzeń + sufiks) <= max_length`. Dzięki temu sufiks nigdy nie zostaje
  obcięty, a slug pozostaje rozróżnialny.

## Zakres zmian

### A. `Table.clone()`

Nowy moduł `flexible_reports/models/cloning.py` z helperami nazewniczymi;
metoda `clone()` na modelu. Logika mieszka w modelu, admin ją tylko wywołuje —
dzięki temu klonowanie działa też ze skryptu i z shella oraz testuje się bez
warstwy HTTP.

**Zasada nadrzędna: `clone()` nie modyfikuje `self` ani żadnego obiektu
osiągalnego z `self`.** Wywołanie `table.clone()` musi zostawić `table` i jego
kolumny nietknięte — po powrocie `table.pk` jest niezmieniony i dalsze
`table.save()` zapisuje oryginał. Ma to znaczenie praktyczne: gdy obiekt przyszedł
z `prefetch_related("column_set")`, menedżer relacji zwraca **zacache'owane**
instancje, więc wyzerowanie im PK zepsułoby obiekty trzymane przez wywołującego
(`TableAdmin.columns`, `admin/table.py:94-95`, iteruje właśnie `obj.column_set.all()`).

Algorytm (cały w `transaction.atomic`):

1. Pobierz dzieci **świeżym querysetem** (`Column.objects.filter(parent=self)`,
   `ColumnOrder.objects.filter(table=self)`), nie przez menedżer relacji na
   `self` — omija to cache prefetch.
2. Skopiuj `Table`: świeży obiekt (refetch albo `copy.copy`), `pk = None`,
   ustaw nową etykietę, `save()`. Nigdy nie zerować `self.pk`.
3. Dla każdej kolumny: zapamiętaj `old_pk` **przed** wyzerowaniem, ustaw
   `pk = None`, **`parent = klon`**, `save()`; zbuduj mapę
   `old_pk -> nowy obiekt Column`.
4. Dla każdego `ColumnOrder`: `pk = None`, **`table = klon`** oraz
   **`column = mapa[old.column_id]`**, `save()`.
5. Zwróć nowy obiekt.

Oba przepięcia w kroku 4 są krytyczne i muszą być wykonane jawnie. `ColumnOrder`
ma FK do `Table` **i** do `Column` (`models/table.py:74-81`):

- bez przepięcia `column` klon sortowałby się po kolumnach oryginału;
- bez przepięcia `table` wpisy zostałyby przy oryginale, a `columnorder_set`
  klonu byłby pusty i klon po cichu straciłby sortowanie.

Oba to ciche błędy — tabela renderuje się poprawnie, tylko w złej kolejności.

`clone()` na niezapisanej instancji (`pk is None`) nie jest wspierane; dostęp do
menedżera relacji podniesie `ValueError`. Nie dodajemy własnej walidacji.

Relacje wskazujące na `Table`, świadomie **nieklonowane**: `ReportElement.table`
(`models/report.py:51`) — klonowanie tabeli nie rusza raportów, które jej
używają. Poza `Column.parent` i `ColumnOrder.table` nic innego w pakiecie ani w
`test_app` nie wskazuje na `Table`. Nie ma żadnych M2M.

`Column.Meta.unique_together = ("parent", "id", "position")` (`column.py:114`)
zawiera PK, więc więz jest w praktyce pusty — klon nie może go naruszyć nawet
przy powtórzonych `position`.

### B. `Report.clone()`

Klonowanie **płytkie**: nowy `Report` i nowe `ReportElement`-y wskazujące na
**te same** obiekty `Table` i `Datasource`. Głębokie klonowanie odrzucono —
mnożyłoby w adminie w większości identyczne tabele. Kto chce niezależnej
tabeli, klonuje ją osobno (punkt A) i przepina element.

Ta sama zasada nienaruszalności źródła co w A.

- `title` -> `"X (copy)"`, wg reguł z sekcji „Nazewnictwo klonów".
- `template` kopiowany dosłownie.
- `slug` -> unikalny, wg reguł skracania z sekcji „Nazewnictwo klonów".
- Elementy: `pk = None`, **`parent = klon`**, slug **bez zmian**.

Uzasadnienie unikalności sluga raportu: `Report.slug` nie ma `unique=True` i nie
jest używany w URL-ach tego pakietu (`urls.py` jest pusty), ale projekty
konsumujące niemal na pewno robią `Report.objects.get(slug=...)`. Klon z
identycznym slugiem wywołałby u nich `MultipleObjectsReturned`.

Uzasadnienie niezmienności slugów elementów: `unique_together` to
`('parent', 'slug')`, więc pod nowym rodzicem nie kolidują, a szablon raportu
adresuje elementy przez `{{ elements.jakis_slug }}`. Zmiana slugów rozspójniłaby
skopiowany szablon z elementami.

Elementy typu except-catchall (`datasource=None`, ustawione `base_model`)
kopiują się bez zmian — to zwykłe nullowalne FK.

Jedyną relacją wskazującą na `Report` jest `ReportElement.parent`
(`models/report.py:19`).

### C. Admin — przycisk w formularzu edycji

Wspólny `CloneAdminMixin` w `flexible_reports/admin/cloning.py`, podpięty pod
`TableAdmin` i `ReportAdmin`.

**Rejestracja trasy — kolejność jest krytyczna:**

```python
def get_urls(self):
    return my_urls + super().get_urls()   # NIE odwrotnie
```

`ModelAdmin.get_urls()` kończy się wstecznie kompatybilnym catch-allem
`path("<path:object_id>/", RedirectView...)` (`django/contrib/admin/options.py:735`).
Konwerter `path:` łapie ukośniki, więc URL `5/clone/` dopasowałby się do niego
jako `object_id="5/clone"` i przekierował na `.../5/clone/change/` -> 404.
Doklejenie własnych tras **za** `super()` daje martwą trasę.

**Metoda HTTP i opakowanie widoku:**

```python
path(
    "<path:object_id>/clone/",
    self.admin_site.admin_view(require_POST(self.clone_view)),
    name="%s_%s_clone" % info,
)
```

Kolejność opakowań jest istotna:

- `require_POST` **nie może** być dekoratorem w ciele klasy. Jego wrapper ma
  sygnaturę `inner(request, *args, **kwargs)`
  (`django/views/decorators/http.py:36`), więc przy dekoracji niezwiązanej
  metody `request` zbindowałby się do `self` i dostalibyśmy
  `AttributeError: 'TableAdmin' object has no attribute 'method'` — czyli 500
  zamiast obiecanego 405. Dekorujemy **związaną** metodę wewnątrz `get_urls()`
  (równoważnie: `@method_decorator(require_POST)` na metodzie).
- `admin_view` musi być **na zewnątrz**, żeby anonimowy GET dostał
  przekierowanie na login, a nie 405 (drobny wyciek informacji o istnieniu URL-a).
  `admin_view` dokłada też sprawdzenie `is_staff`, `never_cache` i obsługę
  sesji — bez niego widok byłby chroniony wyłącznie przypadkiem, przez
  `has_add_permission`.

**Uprawnienia:** wymagane `has_add_permission(request)` (tworzymy obiekt) oraz
`has_view_permission(request, obj)` na obiekcie źródłowym. Brak któregokolwiek
-> `PermissionDenied` (403). Nie wymagamy uprawnienia `change` na źródle — to
odpowiada filozofii wbudowanego „save as new" w Django.

**Nieistniejące `object_id`** -> 404 (`self.get_object()` zwraca `None`).

**Po sklonowaniu:**

- `self.log_addition(request, new_obj, [{"added": {}}])` — argument `message` jest
  **wymagany** (`options.py:936`), a ta struktura sprawia, że strona historii
  renderuje poprawne „Added." zamiast surowego stringa.
- `message_user(..., messages.SUCCESS)`.
- Przekierowanie na formularz edycji **klonu**. Jeśli użytkownik nie ma
  uprawnienia `change` do modelu, przekierowujemy na changelistę — inaczej po
  udanej akcji zobaczyłby 403. To odwzorowanie zachowania
  `ModelAdmin._response_post_save`.

Przekierowanie budujemy przez `reverse()` z PK nowego obiektu — brak komponentu
sterowanego przez użytkownika, więc nie ma ryzyka open redirect.

**Szablon** `flexible_reports/templates/admin/flexible_reports/change_form_with_clone.html`
rozszerza `admin/change_form.html` i nadpisuje `{% block object-tools-items %}`,
dokładając `{{ block.super }}` oraz `<li>` z małym formularzem POST z
`{% csrf_token %}`.

Weryfikacja w Django 6.0.7: blok `object-tools-items` jest w linii 31, a główny
`<form>` otwiera się w linii **37** — nasz formularz nie zagnieżdża się więc w
cudzym, co byłoby niepoprawnym HTML-em. Blok renderuje się tylko pod
`{% if change and not is_popup %}` (linia 29), co samo z siebie trzyma przycisk
z dala od formularza dodawania.

Widok przyjmuje wyłącznie POST, bo klonowanie zmienia stan bazy: zwykły link
`<a href>` pozwoliłby stworzyć obiekt przez `<img src="...">` osadzony w obcej
stronie. Formularz daje CSRF za darmo.

Admin ustawia `change_form_template` na powyższy szablon. `TableAdmin` i
`ReportAdmin` nie definiują dziś własnego `change_form_template`
(`admin/table.py:88-114`, `admin/report.py:53-65`), więc nic nie nadpisujemy.
Nowy szablon łapie się w `package-data` (`templates/**/*` w `pyproject.toml`).

**Znane ograniczenie — grappelli.** Pakiet opcjonalnie wspiera grappelli
(`admin/helpers.py:8-14`). Z zainstalowanym grappelli
`{% extends "admin/change_form.html" %}` rozwiąże się do szablonu *grappelli*,
którego struktura bloków jest inna. Nie dało się tego zweryfikować (grappelli nie
ma w `.venv`). Ryzyko: przycisk może się nie pokazać. Do sprawdzenia ręcznie
przed wydaniem; odnotowane w `HISTORY.rst`.

### D. Usunięcie cache'u i przyspieszenie szablonów

W `flexible_reports/adapters/django_tables2.py`:

1. Usuń `_table_cache` oraz `global _table_cache`; `_table()` buduje klasę przy
   każdym wywołaniu.
2. Dodaj kompilację szablonu cache'owaną **treścią szablonu**:

```python
@lru_cache(maxsize=512)
def _compiled_template(template_code):
    return Template(template_code)
```

3. `DjangoTables2TemplateColumn` nadpisuje `render()`.

**Override musi odtworzyć ciało metody rodzica dosłownie, zmieniając wyłącznie
`Template(self.template_code)` na `_compiled_template(self.template_code)`.**
Rodzic (`django_tables2/columns/templatecolumn.py:104-120`) robi cztery rzeczy,
z których żadnej nie wolno pominąć:

1. `parent_context = getattr(table, "context", Context())` — dziedziczy kontekst
   strony podpięty przez `{% render_table %}`;
2. `self.get_context_data(...)` — dostarcza `default`, `column`, `record` (pod
   `context_object_name`), `value`, `row_counter` oraz scalony `extra_context`
   (również gdy jest callable);
3. `with parent_context.update(context):` — to **context manager**, więc zmienne
   komórki są *zdejmowane* po jej wyrenderowaniu; pominięcie tego przecieka
   zmienne z jednej komórki do następnej;
4. `parent_context["request"] = request` wewnątrz tego bloku, z
   `getattr(table, "request", None)`.

Gdy kolumna nie ma `template_code` (tylko `template_name`), delegujemy do
`super().render(...)`. Analogicznie delegujemy, gdy `self` nie ma
`get_context_data` — `pyproject.toml` deklaruje `django-tables2>=1.16.0`, a ta
metoda jest nowsza; fallback do `super().render()` zachowuje poprawność na
starych wersjach kosztem optymalizacji, bez podnoszenia dolnego progu zależności.

4. `FooterMixin._render_footer` (`adapters/django_tables2.py:60`) też przechodzi
   na `_compiled_template`. Kompiluje raz na render, nie raz na komórkę, więc
   zysk jest mały — ale zostawienie tam gołego `Template()` byłoby niespójne.

**Skompilowanego `Template` nie wolno przypinać do obiektu kolumny.** Kolumny
żyją w `Table.base_columns` i są deepcopy'owane przy każdej instancjacji tabeli
(`tables.py:318`; komentarz `CounterMixin`, `adapters/django_tables2.py:30-35`,
już dokumentuje ten deepcopy). `Template` trzyma referencję do `engine`, więc
deepcopy sklonowałby cały graf silnika szablonów wraz z loaderami i bibliotekami
tagów. Zamiast przyspieszenia dałoby to regres. Cache modułowy kluczowany treścią
omija ten problem w całości.

Cache kluczowany treścią nie wymaga inwalidacji z definicji: zmiana szablonu w
bazie daje inny string, więc inny klucz. `maxsize=512` ogranicza wzrost przy
wielokrotnej edycji szablonów. `Template(code)` rozwiązuje `Engine.get_default()`
w momencie **wywołania**, nie importu, więc nie wprowadzamy zależności od
kolejności importów. `lru_cache` w CPythonie jest bezpieczny wątkowo (najgorszy
przypadek to podwójna kompilacja — nieszkodliwa), a współdzielenie skompilowanych
`Template` między wątkami jest dokładnie tym, co robi `cached.Loader` w Django.

**Zastrzeżenie:** zacache'owane `Template` zapamiętują silnik aktywny w chwili
kompilacji. Pod `override_settings(TEMPLATES=...)` cache serwowałby szablony
związane ze starym silnikiem, a stan przeciekałby między testami. Udostępniamy
`_compiled_template.cache_clear()` i wołamy je w autouse-fixture w testach, żeby
nie gonić fantomowych flaków.

## Testy

Podejście TDD: każdy test pisany przed implementacją i uruchamiany, żeby
zobaczyć, że zawodzi z właściwego powodu.

Konwencja repo: `pytest`, `pytest-django`, `model_bakery`, fixture `admin_client`,
testy w `test_app/tests/test_models/` i `test_app/tests/test_admin/`.
Baza: Postgres (patrz `tests/settings.py`).

### Klonowanie — modele (`test_models/test_cloning.py`)

| Test | Co pilnuje |
|---|---|
| `test_clone_table_copies_columns` | liczba i wartości pól kolumn |
| `test_clone_table_remaps_column_order` | `ColumnOrder` klonu wskazuje na kolumny klonu **oraz** na tabelę-klon (`columnorder.table == clone`) |
| `test_clone_table_does_not_touch_source` | `original.pk` i PK oryginalnych kolumn niezmienione po `clone()`; działa też na instancji z `prefetch_related("column_set")` |
| `test_clone_table_is_independent` | edycja kolumny klonu nie zmienia oryginału |
| `test_clone_table_label_is_numbered` | drugi klon dostaje `(copy 2)`, nie `(copy) (copy)` |
| `test_clone_report_shares_tables` | element klonu ma to samo `table_id` i `datasource_id` |
| `test_clone_report_copies_elements` | liczba elementów, zachowane slugi elementów |
| `test_clone_report_handles_except_catchall` | element z `datasource=None` i ustawionym `base_model` klonuje się poprawnie |
| `test_clone_report_unique_slug` | slug klonu różny od oryginału; **przypadek brzegowy: slug źródłowy dokładnie 50 znaków**, żeby realnie wymusić skracanie rdzenia |

### Klonowanie — admin (`test_admin/test_cloning.py`)

| Test | Co pilnuje |
|---|---|
| `test_clone_button_visible` | przycisk obecny na formularzu edycji |
| `test_clone_url_not_swallowed_by_catchall` | POST na `<pk>/clone/` trafia w nasz widok, a nie w RedirectView (regresja na kolejność `get_urls`) |
| `test_clone_requires_post` | GET jako zalogowany admin -> 405, obiekt nie powstaje |
| `test_clone_requires_add_permission` | user bez `add` -> 403 |
| `test_clone_requires_view_permission` | user bez `view` na źródle -> 403 |
| `test_clone_missing_object_404` | nieistniejące `object_id` -> 404 |
| `test_clone_redirects_to_clone` | przekierowanie na edycję klonu, nie oryginału |
| `test_clone_logs_addition` | powstaje `LogEntry` typu ADDITION dla klonu |

### Cache i render (`test_app/tests/test_adapters.py`)

| Test | Co pilnuje |
|---|---|
| `test_label_change_visible_without_restart` | **regresja**: zmiana `Column.label` widoczna w kolejnym renderze w tym samym procesie |
| `test_removed_column_disappears` | **regresja**: usunięta kolumna znika z renderu |
| `test_template_column_context_is_complete` | **najważniejszy dla override'u `render()`**: kolumna z szablonem używającym `{{ row_counter }}`, `{{ record }}` i zmiennej z kontekstu strony; asercje na **wielu wierszach**, żeby wymusić poprawne `row_counter` i zdejmowanie zmiennych przez context manager |
| `test_no_template_pinned_to_column` | **regresja na deepcopy**: po renderze żadna kolumna w `base_columns` nie ma w `vars()` instancji `django.template.base.Template` |
| `test_compiled_template_cache_is_used` | `_compiled_template.cache_info().hits` rośnie między dwoma renderami — dowód, że cache jest realnie na ścieżce gorącej |
| `test_concurrent_render` | dwa wątki renderujące tę samą tabelę dają identyczny HTML bez wyjątków (ścieżka współdzielonego `Template`/`lru_cache`) |

Testy `test_label_change_visible_without_restart` i `test_removed_column_disappears`
nie przechodzą na obecnym kodzie — pisane jako pierwsze.

## Poza zakresem

- Głębokie klonowanie raportu (wraz z tabelami).
- Klonowanie `Datasource`.
- Akcja masowego klonowania na changeliście.
- Pole `Table.modified` i migracja — patrz „Odrzucone alternatywy".
- Naprawa `docker-compose.yml` (brak `POSTGRES_HOST_AUTH_METHOD: trust`, przez co
  kontener nie startuje z nowoczesnym obrazem postgresa) — realny błąd, ale
  niezwiązany z tą zmianą.

## Dokumentacja

Wpis w `HISTORY.rst` w sekcji dla kolejnego wydania: dwie nowe funkcje
(klonowanie tabeli i raportu) oraz poprawka błędu z cache'em, z wyraźnym
zaznaczeniem, że zmiany etykiet nie wymagają już restartu. Odnotować też
niezweryfikowaną kompatybilność przycisku z grappelli.

Nowy msgid `"copy"` z tłumaczeniem `"kopia"` w
`flexible_reports/locale/pl/LC_MESSAGES/django.po`.
