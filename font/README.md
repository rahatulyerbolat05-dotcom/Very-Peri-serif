# Very Peri Serif Draft — рабочая черновая сборка

Regular, версия1.012. Основная д — реальный контур Cormorant, на основе варианта03, с дополнительно суженной чашей; печатная д доступна через ss07. Русская У с диагональной нижней ветвью, Ү с прямой стойкой. Согласованы ширины широких составных букв; усилены чаши з. Капли из авторского SVG и плавные стыки сохранены. Семейство: **Very Peri Serif Draft**.
Это отдельное имя, поэтому оно не заменяет установленный Instrument Serif.

## Установка

Откройте `VeryPeriSerifDraft-Regular.ttf` и нажмите «Установить».
После установки перезапустите редактор, если он не обновил список шрифтов.
В комплекте также есть WOFF2 для сайта и `proof.svg` с примерами набора.
TTF — устанавливаемый шрифт, WOFF2 — веб-формат.

## Что работает

- Все66 русских и18 казахских букв, родная латиница Instrument Serif,
  цифры, знаки и комбинируемые акценты исходного шрифта; добавлены ₸, ₽, ₴, №, ʼ, неразрывный дефис, тонкий и узкий
  неразрывный пробелы, пунктирный круг с привязкой акцентов.
- В1.005 добавлены типографские штрихи ′ ″, † ‡, ≈, символ замены �,
  дополнительные пробелы/дефисы и латинские Ə/ə.
  Доводка и точный состав: `docs/regular-polish.md`.
- `kern` — попарно уточнённые интервалы кириллицы, казахских букв,
  их альтернатив и смешанных сочетаний; родной кернинг латиницы сохранён.
- `calt` — включён по умолчанию: п получает хвост перед нижней левой
  засечкой; к и қ получают короткую форму перед верхней левой головкой.
- `liga` — родные fi/fl/ffi/ffl; `dlig` — сохранённые необязательные
  латинские лигатуры исходного шрифта.
- `ss01` — родной стилистический набор синхронизирован с а/с/е/ё.
- `ss08` — альтернативная т Claude.
- `ss09` — прежние хвостики ц/щ/қ/ң и заглавных вместо основных капель.
  Работает также вместе с контекстной формой қ.
- `ss07` — печатная строчная д из1.006; округлая д с нижним крючком основная.
- `aalt` — сохранены родные варианты; запасные формы қ и печатная д доступны среди
  альтернатив символа в редакторах, которые поддерживают эту функцию.
- Акценты привязаны к кириллице; у і точка автоматически убирается
  перед верхним знаком. Верхний акцент над Ё/Й учитывает их диакритику.

Пара лл остаётся двумя буквами с кернингом: её отдельная лигатура была
отклонена пользователем и в эту сборку не включена.

Для сайта:

```css
@font-face {
  font-family: "Very Peri Serif Draft";
  src: url("VeryPeriSerifDraft-Regular.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
}
.text { font-family: "Very Peri Serif Draft", serif; }
.old-tails { font-feature-settings: "ss09" 1; }
.printed-de { font-feature-settings: "ss07" 1; }
.alternate-te { font-feature-settings: "ss08" 1; }
```

В редакторах оставьте включёнными кернинг, стандартные лигатуры и
контекстные альтернативы. Для прежних хвостов выберите Stylistic Set09;
для т Claude — Set08, для печатной д — Set07. Названия пунктов зависят от редактора.

## Проверки и ограничения черновика

HarfBuzz проверяет реальные подстановки и позиции, а не только наличие
названий функций. Результаты — `validation.json`; дополнительная проверка
OpenType Sanitizer и сравнение FontBakery с оригиналом — `quality-summary.json`.
Hyperglot проверен с настройками base/primary и подтвердил русский и казахский.
Полный отчёт не заявляет поддержку всех вспомогательных знаков этих языков.

В1.012 проверены102480 пар по реальным краям глифов и143136
кириллических/смешанных сочетаний через HarfBuzz, плюс110889 родных пар.
Проверены все16 комбинаций ss01/ss07/ss08/ss09 и два режима aalt. Учитываются все84×84 пары букв, подстановки,
латиница, цифры и знаки. Сохранены характерные контакты засечек оригинала.
Метод и границы проверки — `docs/kerning-review.md`. Некоторые формы
букв пока не утверждены: используется первый показанный в текущей карте
вариант, а точные пути записаны в `build-manifest.json`.

Сборка Regular без отдельного курсива и новых хинтов для кириллицы.
Часть расширенной кириллицы ещё не добавлена. В базовом тесте русского/казахского нет подстановки системного
шрифта для букв; отсутствующие дополнительные символы редактор может
показать резервным шрифтом.

Метрики строк hhea/typo990/−310 сохранены. Windows clipping ascent расширен
до1250 для верхних акцентов над предсоставленными буквами; это запас
обрезки, а не перенос контуров. Исходные GLIF не изменяются при сборке.
В compiled-копиях нормализуется направление обхода и удаляются вырожденные
сегменты, возникающие при округлении в TrueType.

## Повторная сборка из репозитория

Нужны Git и Python3.12. Все текущие GLIF, параметры, лицензии и скрипты
сохранены в репозитории. Для сборки также нужен исходный Instrument Serif
строго на коммите65c0ef225f386a3c7e87570a4aa9cc0262c2fd81.

Подготовка с нуля (macOS/Linux):

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
используйте его; новый worktree не нужен. Клонируйте с историей:
проверки сравнивают результат с предыдущими версиями через Git.
Архива исходников ZIP или `--depth 1` для полного набора проверок недостаточно.

Сборка1.012 проверена в отдельной чистой копии с новым окружением
Python3.12 на Linux: все команды ниже прошли, TTF совпал с опубликованным
побайтно.

Сборка и проверка из корня репозитория, с активированным окружением:

```sh
python -I tools/refine_widths.py
python -I tools/build_draft_font.py
python -I tools/check_draft_font.py
python -I tools/kerning_proof.py
python -I tools/width_proof.py --text
python -I tools/audit_widths.py
python -I tools/package_draft_font.py
```

TTF и WOFF2 появятся в `dist/VeryPeriSerifDraft/`, готовый архив —
`dist/VeryPeriSerifDraft-Regular.zip`. Первая сборка скачивает только
зависимости и эталон; текущие рисунки букв не требуют повторной отрисовки.

Если matplotlib не может писать в домашний каталог, задайте
`XDG_CACHE_HOME=/workspace/.cache` и `MPLCONFIGDIR=/workspace/.cache/matplotlib`.
Попарная настройка: `tools/optical_kerning.py`; сводка —
`kerning-review.json`, проверка — `kerning-validation.json`.
`kerning-all-pairs.pdf` содержит126 страниц; `kerning-proof.html` —
интерактивное сравнение1.011/1.012 со встроенными шрифтами, без сети.
`--keep-kerning` оставлен для намеренного сохранения текущих пар;
обычная повторная сборка запускается без этого флага.
Оптическая проверка контуров: `docs/optical-review.md`.
Конкретные черновые пары: `font/kerning-overrides.json`.
Сгенерированные правила: `font/draft-features.fea`.
`build-manifest.json` содержит выбранные GLIF, SHA256, число пар и поправки
защиты от столкновений. Подстановки собираются из актуальных контекстных
классов репозитория, а родные GSUB/GPOS сохраняются.

Дополнительное сравнение с эталоном:

```sh
python -m pip install -r font/requirements-quality.txt
fontbakery check-googlefonts --skip-network --no-progress --json build/draft-font/fontbakery-native.json reference/instrument-serif/fonts/ttf/InstrumentSerif-Regular.ttf
fontbakery check-googlefonts --skip-network --no-progress --json build/draft-font/fontbakery-draft.json dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf
hyperglot dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf --output build/draft-font/hyperglot.yaml
python -I tools/package_draft_font.py
```

## Лицензия

SIL Open Font License1.1, полный текст в `OFL.txt`.
Оригинал: Copyright2022 The Instrument Serif Project Authors,
Rodrigo Fuenzalida и Jordan Egstad (`AUTHORS.txt`).
Кириллическое расширение и изменения — участники проекта Very Peri Serif,2026.
Это черновая производная версия; родная латиница и её лицензия сохранены.

[РЕШЕНИЕ · 17.10.2026] Глиф д — изменённый Cormorant Garamond Regular ss10, Copyright2015 the Cormorant Project Authors. Лицензия SIL OFL1.1: Cormorant-OFL.txt; подробности Cormorant-NOTICE.txt.
