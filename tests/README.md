# Your tests / Ваши тесты

Create your own JSON Lines inputs here, together with expected and actual outputs and an explanation of each test. Run a file from the repository root:

```sh
python tools/run.py --input tests/my_cases.jsonl
```

Create `my_cases.jsonl` before running this example command. The launcher prints actual results; compare them with independently justified expected answers. Your files are not discovered automatically. Call your route helper directly in your test code. See the root README for all requirements.

Создайте здесь свои входы JSON Lines, ожидаемые и фактические результаты и объяснения тестов. Команда выше запускает созданный вами файл, но не сравнивает ответы автоматически. Функцию восстановления пути вызывайте непосредственно из своего тестового кода. Полные требования приведены в README в корне репозитория.

## My tests (Python)

```sh
python tests/run_tests.py                          # parts A-D, log in tests/test_output.txt
python tools/run.py --input tests/my_cases.jsonl   # actual results in tests/my_cases_actual.jsonl
python tests/benchmark.py                          # Kruskal vs Prim, output in tests/benchmark_output.txt
```

`cases.json` holds every input with a written justification and an expected answer; `validator.py` checks answers semantically. Details are in `ANALYSIS.md`.
