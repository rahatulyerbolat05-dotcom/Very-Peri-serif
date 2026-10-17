# Сборка Very Peri Serif

Финальный **Very Peri Serif Regular 1.002**: установка и функции —
[README-regular.md](README-regular.md). Готовый архив:
`dist/VeryPeriSerif-Regular.zip`. Все рисунки букв, параметры, лицензии
и скрипты хранятся в репозитории.

## Подготовка с нуля

Нужны Git и Python3.12. Команды для macOS/Linux:

```sh
git clone --branch claude/upbeat-faraday-mzabid https://github.com/rahatulyerbolat05-dotcom/Very-Peri-serif.git
cd Very-Peri-serif
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r font/requirements.txt
git clone https://github.com/Instrument/instrument-serif reference/instrument-serif
git -C reference/instrument-serif checkout --detach 65c0ef225f386a3c7e87570a4aa9cc0262c2fd81
```

На Windows создайте окружение командой `py -3.12 -m venv .venv`,
а в PowerShell активируйте его через `.venv\Scripts\Activate.ps1`.
Остальные команды Git/Python одинаковы. Если репозиторий уже есть,
используйте его; новый worktree не нужен. Нужна полная история:
проверки сравнивают результат с предыдущими версиями через Git.
Архива исходников ZIP или `--depth 1` для полного набора проверок недостаточно.

Эталон Instrument Serif закреплён на коммите65c0ef2: его нельзя
заменять текущим HEAD или урезанной веб-версией. Глиф д и необходимые
лицензии Cormorant уже сохранены; заново скачивать или рисовать его не нужно.

## Финальный Regular

Из корня репозитория, с активированным окружением:

```sh
python -I tools/build_regular_release.py
```

Команда заново строит шрифт из выбранных GLIF, пересчитывает кернинг,
оформляет финальное имя/версию, проверяет конечные TTF и WOFF2 и
собирает архив. Результаты:

- `dist/VeryPeriSerif/VeryPeriSerif-Regular.ttf` — установка;
- `dist/VeryPeriSerif/VeryPeriSerif-Regular.woff2` — сайт;
- `dist/VeryPeriSerif/specimen.pdf`, `proof.svg` — набор и альтернативы;
- `dist/VeryPeriSerif-Regular.zip` — комплект с лицензиями и отчётами.

Дополнительные проверки FontBakery и языкового покрытия Hyperglot:

```sh
python -m pip install -r font/requirements-quality.txt
python -I tools/build_regular_release.py --quality
```

Режим без `--quality` выполняет функциональные, векторные, метрические
проверки, проверку WOFF2 и OpenType Sanitizer. FontBakery/Hyperglot в его
отчёте обозначаются как не запущенные; их результаты не заимствуются
из другой сборки. Сетевые проверки FontBakery отключены.

Все868 функциональных тестов и254025 сочетаний HarfBuzz выполняются
на финальном TTF, включая все16 сочетаний ss01/ss07/ss08/ss09 и два
режима aalt. Для кернинга проверяются102480 геометрических пар.
Отдельно сравниваются все509 контуров/метрик и таблицы OpenType с
исходной стадией; изменение имён не должно менять рисунки или набор.
Контрольные суммы конечных файлов включены в `SHA256SUMS.txt`.

## Работа с исходниками

`data/alphabet.json` задаёт активные GLIF, `data/params.json` — параметры.
Чтобы пересоздать текущие правки ширин/веса после изменения их параметров:

```sh
python -I tools/refine_widths.py
python -I tools/build_regular_release.py
```

Кернинг: `tools/optical_kerning.py`, `font/kerning-overrides.json`.
Контекстные классы автоматически проверяются перед сборкой.
`build-manifest.json` сохраняет выбранные источники и SHA256.

Окружение Linux/Python3.12 проверено в отдельной чистой копии:
установлены зависимости, собраны TTF/WOFF2, выполнены проверки и упаковка.
Финальные TTF и WOFF2 из чистого окружения совпали с релизом побайтно.
Фиксированные метки времени используются и при упаковке релиза.

Если matplotlib не может писать в домашний каталог, задайте доступные
каталоги `XDG_CACHE_HOME` и `MPLCONFIGDIR`; в облачной среде проверены
`/workspace/.cache` и `/workspace/.cache/matplotlib`.

## Предыдущие рабочие сборки

`dist/VeryPeriSerifDraft/` сохранён для истории и сравнений.
`tools/build_draft_font.py`, `check_draft_font.py`, `kerning_proof.py`
остаются доступны для промежуточной работы. В редакторе финальная
версия называется **Very Peri Serif**, прежняя — **Very Peri Serif Draft**.

## Лицензия

SIL Open Font License1.1; атрибуция Instrument Serif и Cormorant включена
в каждый архив. Подробности — [README-regular.md](README-regular.md).
