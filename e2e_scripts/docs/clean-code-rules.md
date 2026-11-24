# Clean Code rules for this project

Source: R. C. Martin, *Clean Code* (chapters 1-13 and the ch. 17 smell catalogue), restated in our own words and adapted to Python/pytest/Playwright. IDs (C1, G5, N1, T4...) are the book's. `[tool]` marks rules a linter enforces; the rest are review rules. Java-only items are marked N/A.

## Ch. 1 Attitude
- Boy Scout rule: leave each file you touch cleaner than you found it.
- Bad code compounds. Never rush with "we'll clean it later".

## Ch. 2 Names
- Reveal intent: a name should answer why it exists, what it does and how it is used. Rename when you find a better name.
- No disinformation: don't use a name that implies something false (a `list` suffix on a non-list; look-alike names).
- Make meaningful distinctions: no number series (`a1, a2`), no noise words (`data`, `info`, `the`).
- Pronounceable and searchable names; avoid single letters and bare numbers outside tiny scopes.
- No encodings: no type or scope prefixes, no Hungarian notation. [tool: pep8-naming]
- No mental mapping: readers shouldn't have to translate a name into another one.
- Classes are nouns; avoid `Manager`, `Processor`, `Data`, `Info`. Methods are verbs; accessors and predicates are named for their value.
- Don't be cute: no jokes or slang in names. Say what you mean.
- One word per concept (`get` or `fetch`, not both); don't pun (one word, one meaning).
- Use solution-domain names (pattern and CS terms) for technical things, problem-domain names (GST, ITC, GSTR, ledger) for business things.
- Add meaningful context (`invoice_state`, not `state`), but no gratuitous prefixes such as a project acronym on every name.
- N1 descriptive names; N2 names at the right abstraction level; N3 standard nomenclature; N4 unambiguous names; N5 name length grows with scope; N6 avoid encodings; N7 a name must describe side effects.

## Ch. 3 Functions
- Small, then smaller: hardly ever 20 lines; blocks in `if`/`while` are one line (a call); keep indentation to one or two levels.
- Do one thing (G30). If you can extract another function with a meaningful name, it does more than one thing.
- One level of abstraction per function; read top-down like a story (the stepdown rule, G34).
- `if`/`elif` chains on type belong behind polymorphism or a lookup (G23); hide them once, deep in the lower layer.
- Descriptive names; a long descriptive name beats a short cryptic one or a comment. Be consistent in phrasing within a module.
- Arguments: zero is ideal, one or two normal, three avoid, more than three needs a very special reason (F1). [tool: ruff max-args=3]
  - Common one-argument forms: ask a question about it, transform it, or fire an event. Don't mix them.
  - No flag arguments (F3, G15): split into two functions.
  - Two or three related arguments usually mean a missing object; wrap them in a small class or dataclass.
  - Name functions and arguments as verb/noun pairs that read well (`write_field(name)`, `assert_expected_equals_actual(expected, actual)`).
- No hidden side effects: a function that says `check_password` must not also start a session.
- No output arguments (F2): change the object you are called on instead.
- Command-query separation: a function either does something or answers something, not both.
- Prefer exceptions to returned error codes; extract the `try` body into its own function; error handling is "one thing" (functions that handle errors do nothing else).
- Don't repeat yourself (G5): duplication is the root of much evil; remove it.
- Structured, single-exit style matters little in small functions; early `return` is fine when it keeps functions tiny.
- Write the long version first, then refine with tests green. Nobody writes it clean the first time.

## Ch. 4 Comments
- A comment is a failure to express yourself in code; try to avoid it. Prefer a better name or an extracted function.
- Good: legal headers, informative notes (e.g. what a regex matches), explanation of intent, clarification of an unchangeable external value, warning of consequences, amplification of something easy to dismiss, TODO notes (with the scenario id; review them often), docstrings for public APIs.
- Bad: mumbling, redundant comments (C3), misleading comments, mandated boilerplate, journal/change-log comments (C1), noise, scary noise, position markers and banners, closing-brace comments, attributions and bylines, HTML in comments, nonlocal information, too much information, an unobvious connection, function-header comments on tiny functions.
- C1 inappropriate information (history belongs in git); C2 obsolete comment: fix or delete; C4 write comments well or not at all; C5 delete commented-out code. [tool: ruff ERA]

## Ch. 5 Formatting
- Code formatting is communication. One automatic formatter decides; no style debates. [tool: ruff format]
- Newspaper metaphor: file name and top tell the story; high-level at top, detail below; callers above callees.
- Vertical openness: blank line between concepts; keep related lines dense and close (vertical distance, G10): declare variables near first use.
- Dependent and similar functions stay close together.
- Horizontal: lines up to about 110 characters. [tool: ruff E501]
- Files typically around 200 lines; rarely over 500. Split big files.
- Team rules beat personal taste; follow them everywhere.

## Ch. 6 Objects and data structures
- Hide implementation: expose behaviour, not fields and getters.
- Objects hide data and expose behaviour; data structures expose data and have little behaviour. Pick one per class; avoid hybrids.
- Procedural code makes new functions easy; OO code makes new types easy. Choose by what changes.
- Law of Demeter: talk to your friends, not strangers. No train wrecks like `a.get_b().get_c().do()` (G36). Tell the object to do the job instead.
- Data transfer objects (plain dataclasses/pydantic models) are fine for moving data.

## Ch. 7 Error handling
- Use exceptions rather than return codes.
- Write the `try/except` first in tests that force failure; then make the code pass.
- Give exceptions context: the operation that failed and why (include the URL, role, journey id).
- Define exception classes by how callers handle them; wrap third-party exceptions behind one of your own.
- Special-case objects can remove the need for a special case in the caller.
- Don't return `None` for "nothing" when a list or special case works; don't pass `None` as an argument unless the API requires it.
- Never swallow an exception (`except: pass`). [tool: ruff bugbear]

## Ch. 8 Boundaries (third-party code)
- Wrap third-party APIs (Playwright, httpx) behind our own small interfaces (page objects, `ApiClient`) so a library change touches one place.
- Learning tests: write small tests that pin down how an external API behaves; they tell you when an upgrade breaks us.
- Code against the interface you wish you had, then adapt.

## Ch. 9 Unit tests
- TDD laws: write a failing test before production code; write only enough test to fail; write only enough code to pass.
- Keep tests clean; dirty tests are worse than none. Readability is the top quality of a test.
- Build-Operate-Check, or given-when-then. A small test-specific language (our page objects and fixtures) makes tests read well.
- One concept per test; minimise asserts per test.
- F.I.R.S.T.: Fast, Independent, Repeatable, Self-validating, Timely.
- Our adaptation: E2E tests run against the seeded QA tenant. "Repeatable" means the same result on any worker, any order, any time.

## Ch. 10 Classes
- Order inside a class: constants, then variables, then public, then private helpers (called after the caller).
- Classes should be small, measured in responsibilities, not lines. A class name that needs "And" or "Manager" is too big.
- Single Responsibility Principle: one reason to change.
- Cohesion: methods use most of the instance variables. Losing cohesion is a signal to split.
- Organise for change: open for extension, closed for modification (OCP); depend on abstractions, not concretions (DIP).

## Ch. 11 Systems
- Separate construction from use: build objects at the start (`conftest.py`, fixtures); the rest of the code just uses them.
- Use dependency injection (fixtures) instead of hard-wired lookups or globals.
- Keep configuration at high levels (G35): `config/settings.py` only.

## Ch. 12 Emergence (Kent Beck's four rules, in order)
1. Runs all the tests.
2. No duplication.
3. Expresses the intent of the programmer.
4. Minimises the number of classes and methods.

## Ch. 13 Concurrency (applies to our parallel runs)
- Keep concurrency code separate and small; limit shared data; make data copies instead of sharing.
- Our rule: no shared mutable state between tests or workers. One account and one dataset per worker.
- Keep threads (workers) as independent as possible.

## Ch. 14-16 Refactoring in practice
- Work in tiny steps with the tests green at every step; don't leave a half-done refactor.

## Ch. 17 Smells and heuristics (full catalogue)
Comments: C1 inappropriate information; C2 obsolete comment; C3 redundant comment; C4 poorly written comment; C5 commented-out code.
Environment: E1 build takes more than one step; E2 tests take more than one step (`make test` must be enough).
Functions: F1 too many arguments; F2 output arguments; F3 flag arguments; F4 dead function.
General:
- G1 multiple languages in one file (keep HTML/JS/SQL strings out of Python modules; load from files).
- G2 obvious behaviour unimplemented (least surprise).
- G3 incorrect behaviour at boundaries: write a test for every boundary, don't trust intuition.
- G4 overridden safeties: never turn off lint, type checks, or tests to get green.
- G5 duplication (DRY).
- G6 code at the wrong level of abstraction (high-level concepts mixed with low-level detail).
- G7 base classes depending on their derivatives.
- G8 too much information: keep interfaces small and hide data.
- G9 dead code: delete it.
- G10 vertical separation: define things near use.
- G11 inconsistency: do similar things the same way.
- G12 clutter: unused variables, functions, empty constructors, noise comments.
- G13 artificial coupling between unrelated things.
- G14 feature envy: a method that uses another object's data more than its own belongs on that object.
- G15 selector arguments.
- G16 obscured intent: run-on expressions, magic numbers.
- G17 misplaced responsibility: put code where a reader would look for it.
- G18 inappropriate static: prefer instance behaviour when it could vary; `@staticmethod` only when truly independent.
- G19 use explanatory variables for intermediate results.
- G20 function names should say what they do.
- G21 understand the algorithm before coding; don't poke until tests pass.
- G22 make logical dependencies physical (ask for what you need instead of assuming it).
- G23 prefer polymorphism to if/else or switch.
- G24 follow standard conventions (PEP 8, our formatter).
- G25 replace magic numbers with named constants.
- G26 be precise: no floats for money (use `Decimal`), don't assume the first match is the only match, don't skip transactions or locks because a clash seems unlikely. For GST maths this is critical.
- G27 structure over convention: enforce design with the code structure (types, base classes), not with naming conventions.
- G28 encapsulate conditionals (`if is_inter_state(invoice)`).
- G29 avoid negative conditionals.
- G30 functions should do one thing.
- G31 hide no temporal coupling: make required call order explicit.
- G32 don't be arbitrary: have a reason for each structure choice.
- G33 encapsulate boundary conditions (no scattered +1/-1).
- G34 functions descend only one level of abstraction.
- G35 keep configurable data at high levels.
- G36 avoid transitive navigation (Law of Demeter).
Java (mostly N/A to Python): J1 avoid long import lists via wildcards (in Python do the opposite: no `import *`, [tool: ruff F403]); J2 don't inherit constants; J3 use enums rather than integer constants (use `Enum` for roles, statuses, GST slabs).
Names: N1-N7 as listed in Ch. 2.
Tests:
- T1 insufficient tests: test everything that could break.
- T2 use a coverage tool (pytest-cov) to find gaps.
- T3 don't skip trivial tests.
- T4 an ignored test is a question about an ambiguity: every `skip` carries the scenario id and the question.
- T5 test boundary conditions.
- T6 exhaustively test near bugs; bugs cluster. Add a regression test for every defect.
- T7 patterns of failure are revealing: order test cases so patterns show.
- T8 coverage patterns are revealing.
- T9 tests should be fast.

## How this maps onto our code
| Book idea | Where it shows up here |
|---|---|
| Wrap boundaries (ch. 8) | `pages/` wrap Playwright; `fixtures/api_client.py` wraps httpx |
| Separate construction from use (ch. 11) | `conftest.py` builds sessions, data and API client; tests only consume |
| Config at high level (G35) | `config/settings.py` is the only reader of the environment |
| Enums over int constants (J3) | `Role` and journey statuses are `Literal`/`Enum` types |
| Precision (G26) | money and tax values use `Decimal`, never `float` |
| Tests are first-class (ch. 9) | same lint and type checks apply to `tests/` |
| One step to test (E2) | `make test` / `make smoke` |

## Tool enforcement
`ruff` rules: E, F, I, B, UP, PT, N (naming), C90 (complexity max 8), PLR0913 (args max 3), SIM, ERA (commented-out code). `mypy --strict`. Run `make lint typecheck` before every commit. Rules marked "review" are checked in code review and by the test-healer/generator agents.
