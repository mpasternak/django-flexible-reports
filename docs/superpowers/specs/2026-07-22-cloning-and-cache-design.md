# Klonowanie tabel i raportów + usunięcie cache'u tabel

Data: 2026-07-22
Status: zaakceptowana

## Cel

Trzy niezależne zmiany w `django-flexible-reports`:

1. Możliwość sklonowania `Table` (wraz z kolumnami i kolejnością sortowania).
2. Możliwość sklonowania `Report` (wraz z jego elementami).
3. Naprawa błędu: zmiana `label` w bazie nie jest widoczna bez restartu procesu
   Django.

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
(sqlite in-memory, Python 3.13, django-tables2 z `.venv`):

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
- `TemplateColumn.render()` (`columns/templatecolumn.py`) wykonuje
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

## Zakres zmian

### A. `Table.clone()`

Nowy moduł `flexible_reports/models/cloning.py` z helperami nazewniczymi;
metoda `clone()` na modelu. Logika mieszka w modelu, admin ją tylko wywołuje —
dzięki temu klonowanie działa też ze skryptu i z shella oraz testuje się bez
warstwy HTTP.

Algorytm (cały w `transaction.atomic`):

1. Wczytaj do pamięci `column_set` i `columnorder_set` **przed** zmianą PK.
2. Skopiuj `Table` (`pk = None`, `_state.adding = True`), ustaw nową etykietę.
3. Skopiuj kolumny, budując mapę `stare_pk -> nowy obiekt Column`.
4. Skopiuj `ColumnOrder`, przepinając pole `column` przez tę mapę.
5. Zwróć nowy obiekt.

Krok 4 jest krytyczny: `ColumnOrder` ma FK zarówno do `Table`, jak i do
`Column`. Bez przepięcia klon sortowałby się po kolumnach oryginału, co jest
cichym błędem — tabela renderuje się poprawnie, tylko w złej kolejności, i
psuje się dopiero przy edycji kolumn oryginału.

Nazwa klonu: `label` -> `"X (kopia)"`, przy kolejnych klonach `"X (kopia 2)"`,
`"X (kopia 3)"`. `Table.label` nie ma ograniczenia unikalności, więc numerowanie
jest wyłącznie kosmetyczne — ale bez niego lista wyboru tabeli w
`ReportElement` wypełnia się nierozróżnialnymi pozycjami.

### B. `Report.clone()`

Klonowanie **płytkie**: nowy `Report` i nowe `ReportElement`-y wskazujące na
**te same** obiekty `Table` i `Datasource`. Głębokie klonowanie odrzucono —
mnożyłoby w adminie w większości identyczne tabele. Kto chce niezależnej
tabeli, klonuje ją osobno (punkt A) i przepina element.

- `title` -> `"X (kopia)"`, analogicznie do `Table.label`.
- `template` kopiowany dosłownie.
- `slug` -> unikalny w obrębie `Report` (`x-kopia`, `x-kopia-2`), z pilnowaniem
  `max_length` pola `SlugField`.
- Slugi `ReportElement` pozostają **bez zmian**.

Uzasadnienie unikalności sluga raportu: `Report.slug` nie ma `unique=True` i nie
jest używany w URL-ach tego pakietu (`urls.py` jest pusty), ale projekty
konsumujące niemal na pewno robią `Report.objects.get(slug=...)`. Klon z
identycznym slugiem wywołałby u nich `MultipleObjectsReturned`.

Uzasadnienie niezmienności slugów elementów: `unique_together` to
`('parent', 'slug')`, więc pod nowym rodzicem nie kolidują, a szablon raportu
adresuje elementy przez `{{ elements.jakis_slug }}`. Zmiana slugów rozspójniłaby
skopiowany szablon z elementami.

### C. Admin — przycisk w formularzu edycji

Wspólny `CloneAdminMixin` w `flexible_reports/admin/cloning.py`, podpięty pod
`TableAdmin` i `ReportAdmin`.

- `get_urls()` dokłada trasę `<path:object_id>/clone/` o nazwie
  `flexible_reports_<model>_clone`.
- Widok przyjmuje **wyłącznie POST** (`require_POST`). Klonowanie zmienia stan
  bazy, więc zwykły link `<a href>` pozwoliłby stworzyć obiekt przez
  `<img src="...">` osadzony w obcej stronie. Formularz daje CSRF za darmo.
- Uprawnienia: wymagane `has_add_permission` (tworzymy obiekt) **oraz**
  `has_view_permission` na obiekcie źródłowym. Brak któregokolwiek -> 403.
- Nieistniejące `object_id` -> 404.
- Po sklonowaniu: `log_addition()` (wpis w historii admina),
  `message_user(..., messages.SUCCESS)` i przekierowanie na formularz edycji
  **klonu**, nie oryginału.

Szablon `flexible_reports/templates/admin/flexible_reports/change_form_with_clone.html`
rozszerza `admin/change_form.html` i nadpisuje `{% block object-tools-items %}`,
dokładając `{{ block.super }}` oraz `<li>` z małym formularzem POST.

Weryfikacja: w `admin/change_form.html` (Django z `.venv`) blok
`object-tools-items` jest w linii 31, a główny `<form>` otwiera się dopiero w
linii 36 — nasz formularz nie zagnieżdża się więc w cudzym, co byłoby
niepoprawnym HTML-em.

Admin ustawia `change_form_template` na powyższy szablon. `TableAdmin` i
`ReportAdmin` nie definiują dziś własnego `change_form_template`, więc nic nie
nadpisujemy.

### D. Usunięcie cache'u i przyspieszenie szablonów

W `flexible_reports/adapters/django_tables2.py`:

1. Usuń `_table_cache` oraz `global _table_cache`; `_table()` buduje klasę przy
   każdym wywołaniu.
2. Dodaj kompilację szablonu kolumny cache'owaną **treścią szablonu**:

```python
@lru_cache(maxsize=512)
def _compiled_template(template_code):
    return Template(template_code)
```

3. `DjangoTables2TemplateColumn` nadpisuje `render()`, używając
   `_compiled_template(self.template_code)` zamiast `Template(self.template_code)`.
   Gdy kolumna nie ma `template_code` (tylko `template_name`), deleguje do
   `super().render(...)`.

**Skompilowanego `Template` nie wolno przypinać do obiektu kolumny.** Kolumny
żyją w `Table.base_columns` i są deepcopy'owane przy każdej instancjacji tabeli;
`Template` trzyma referencję do `engine`, więc deepcopy sklonowałby cały graf
silnika szablonów wraz z loaderami i bibliotekami tagów. Zamiast przyspieszenia
dałoby to regres. Cache modułowy kluczowany treścią omija ten problem w całości.

Cache kluczowany treścią nie wymaga inwalidacji z definicji: zmiana szablonu w
bazie daje inny string, więc inny klucz. `maxsize=512` ogranicza wzrost przy
wielokrotnej edycji szablonów. Współdzielenie skompilowanych `Template` między
wątkami jest bezpieczne — dokładnie tak działa `cached.Loader` w Django.

## Testy

Podejście TDD: każdy test pisany przed implementacją i uruchamiany, żeby
zobaczyć, że zawodzi z właściwego powodu.

Konwencja repo: `pytest`, `pytest-django`, `model_bakery`, fixture `admin_client`,
testy w `test_app/tests/test_models/` i `test_app/tests/test_admin/`.

| Test | Plik | Co pilnuje |
|---|---|---|
| `test_clone_table_copies_columns` | `test_models/test_cloning.py` | liczba i wartości pól kolumn |
| `test_clone_table_remaps_column_order` | `test_models/test_cloning.py` | `ColumnOrder` klonu wskazuje na kolumny klonu, nie oryginału |
| `test_clone_table_is_independent` | `test_models/test_cloning.py` | edycja kolumny klonu nie zmienia oryginału |
| `test_clone_table_label_is_numbered` | `test_models/test_cloning.py` | drugi klon dostaje `(kopia 2)` |
| `test_clone_report_shares_tables` | `test_models/test_cloning.py` | element klonu ma to samo `table_id` i `datasource_id` |
| `test_clone_report_copies_elements` | `test_models/test_cloning.py` | liczba elementów, zachowane slugi elementów |
| `test_clone_report_unique_slug` | `test_models/test_cloning.py` | slug klonu różny od oryginału i nieprzekraczający `max_length` |
| `test_clone_button_visible` | `test_admin/test_cloning.py` | przycisk obecny na formularzu edycji |
| `test_clone_requires_post` | `test_admin/test_cloning.py` | GET -> 405, obiekt nie powstaje |
| `test_clone_requires_add_permission` | `test_admin/test_cloning.py` | user bez `add` -> 403 |
| `test_clone_missing_object_404` | `test_admin/test_cloning.py` | nieistniejące `object_id` -> 404 |
| `test_clone_redirects_to_clone` | `test_admin/test_cloning.py` | przekierowanie na edycję klonu, nie oryginału |
| `test_label_change_visible_without_restart` | `test_app/tests/test_adapters.py` | **regresja na cache**: zmiana `Column.label` widoczna w kolejnym renderze w tym samym procesie |
| `test_removed_column_disappears` | `test_app/tests/test_adapters.py` | **regresja na cache**: usunięta kolumna znika z renderu |

Dwa ostatnie testy nie przechodzą na obecnym kodzie — pisane jako pierwsze.

## Poza zakresem

- Głębokie klonowanie raportu (wraz z tabelami).
- Klonowanie `Datasource`.
- Akcja masowego klonowania na changeliście.
- Pole `Table.modified` i migracja — patrz "Odrzucone alternatywy".

## Dokumentacja

Wpis w `HISTORY.rst` w sekcji dla kolejnego wydania: dwie nowe funkcje
(klonowanie tabeli i raportu) oraz poprawka błędu z cache'em, z wyraźnym
zaznaczeniem, że zmiany etykiet nie wymagają już restartu.
