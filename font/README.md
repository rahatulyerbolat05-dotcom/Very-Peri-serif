# Сборка Very Peri Serif

Готовые шрифты лежат в `fonts/`, архив для скачивания в `dist/`. Здесь описано, как собрать их заново из исходников
(`data/` — контуры GLIF/SVG и параметры, `tools/` — скрипты, `font/` — OpenType, кернинг и тексты для пользователя).

## Подготовка

Нужны Git, Python 3.12 и make. Нужна полная история репозитория: проверки сравнивают результат с прежними версиями
через Git, поэтому ZIP исходников и `--depth 1` не подходят.

```sh
git clone https://github.com/rahatulyerbolat05-dotcom/Very-Peri-serif.git
cd Very-Peri-serif
python3.12 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Эталон Instrument Serif скачивается при первой сборке (`tools/fetch_reference.sh`) и закрепляется на коммите
`65c0ef2`: все измерения сняты с него. Урезанную веб-версию Instrument Serif использовать нельзя.

## Одна команда

```sh
make
```

| Шаг | Цель make | Скрипты | Результат |
|---|---|---|---|
| 1 | `regular` | `build_regular_release.py`, `make_test_copy.py` | `build/release/VeryPeriSerif-Regular.*`, `dist/test/VeryPeriSerifT<версия>-Regular.ttf` |
| 2 | `italic` | `italic_caps.py` → `italic_lower.py` → `italic_features.py` → `italic_kern.py` | `build/italic-lower/VeryPeriSerifItalicI<NNN>.ttf` |
| 3 | `family` | `build_family.py` | Regular и Italic одним семейством, `build/release/VeryPeriSerif-Italic.*` |
| 4 | `release` | `package_release.py` (`ttf2otf.py`) | `fonts/ttf`, `fonts/otf`, `fonts/webfonts`, `docs/qa/`, `dist/VeryPeriSerif-<версия>.zip` |

`make regular` собирает только Regular. `make clean` удаляет `build/`. `make quality` запускает FontBakery
(профиль universal, без сети) на `fonts/ttf`, для него нужен `requirements-quality.txt`.

Что проверяется при сборке:

- Regular: все функциональные тесты и сочетания HarfBuzz на конечном TTF (контекстные формы, ss01–ss09, aalt), все
  пары кернинга, контуры и таблицы против исходной стадии, OpenType Sanitizer (`docs/qa/validation.json`,
  `kerning-validation.json`, `release-validation.json`).
- Семейство: связь стилей, метрики, покрытие курсивом всех знаков Regular, набор без .notdef (`docs/qa/family-validation.json`).
- Публикация: OTF совпадает с TTF (расстояние Хаусдорфа контуров, те же таблицы и ширины), WOFF2 с TTF, лицензия и имена
  (`docs/qa/package-check.json`).

## Подбор полей курсива

Поля курсива записаны в `data/italic-spacing.json` и `data/italic-caps-spacing.json`, сборка их только применяет.
Чтобы подогнать их заново после изменения форм, цепочка такая (порядок важен, см. docstring `tools/italic_respace.py`):
`italic_respace.py --caps --reset`, `italic_caps.py`, `italic_respace.py --reset`, `italic_lower.py`, `italic_respace.py`,
`italic_lower.py`, `italic_respace.py --caps`, `italic_caps.py`, `italic_lower.py`, затем `make release`.

## Работа с исходниками

`data/alphabet.json` задаёт активные GLIF, `data/params.json` — параметры (единственный источник чисел).
Кернинг Regular: `tools/optical_kerning.py`, `font/kerning-overrides.json`. Контекстные классы проверяются
перед сборкой автоматически (`tools/check_context_classes.py`). `build-manifest.json` хранит выбранные источники и SHA256.

Если matplotlib не может писать в домашний каталог, задайте `XDG_CACHE_HOME` и `MPLCONFIGDIR`.

## Прежние сборки

`dist/VeryPeriSerifDraft/` — черновая сборка 1.010 для истории и сравнений (в редакторе **Very Peri Serif Draft**),
`docs/history.md` — журнал прежних выпусков.

## Лицензия

SIL Open Font License 1.1, текст и копирайты в `OFL.txt`; авторы в `AUTHORS.txt`, участие ИИ в `FONTLOG.txt` и
`font/ai-disclosure.json`. Разбор: `docs/legal-review.md`.
