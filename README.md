# Very Peri Serif

Кириллическое расширение Instrument Serif: русский и казахский, Regular.
Финальный **Very Peri Serif Regular**, версия1.000.

[Установка и возможности](font/README-regular.md) · [сборка из исходников](font/README.md).
[Состав и проверка финального релиза](docs/regular-release.md).

[Согласованы ширины, сужена д, усилена з](docs/width-review.md).
[Сравнение форм](docs/img/width_refinement.svg) · [сравнение в словах](docs/img/width_text_comparison.svg).
[Плавные стыки хвостиков: сравнение до/после](docs/img/tail_join_refinement.svg).
[Что исправлено и проверено](docs/tail-join-refinement.md).
[Хвостики и различие прописных У/Ү](docs/revision-1.009.md).
[Аудит 12 шрифтов и сравнение вариантов д](docs/de-reference-audit.md).

- [Устанавливаемый TTF](dist/VeryPeriSerif/VeryPeriSerif-Regular.ttf)
- [Архив TTF + WOFF2 + лицензия и примеры](dist/VeryPeriSerif-Regular.zip)
- [Лист набора готовым шрифтом](docs/img/regular_release_proof.svg)
- [Установка, функции OpenType и повторная сборка](font/README.md)

Работают кернинг, контекстные формы п/к/қ, родные латинские лигатуры,
альтернативная т (`ss08`) и прежние хвостики (`ss09`). Основные хвосты —
каплевидные. Кернинг и контекстные формы проверены в готовых TTF/WOFF2.

[Карта алфавита](docs/img/alphabet_status.svg) показывает происхождение
и состояние рисунков. [Правила проекта](CLAUDE.md),
[история решений](docs/alphabet-review.md),
[отчёт проверки готовой сборки](dist/VeryPeriSerif/quality-summary.json).

Лицензия SIL OFL1.1; авторы исходного Instrument Serif — Rodrigo Fuenzalida
и Jordan Egstad. Полный текст лицензии и авторство сохранены в архиве.

[РЕШЕНИЕ · 16.10.2026] В1.003 сужены развилки ү/ұ, уточнён вес З/з/ч,
добавлены обязательные текстовые знаки. [Оптическая проверка](docs/optical-review.md)
и [сравнение форм](docs/img/optical_changes.svg). В этой предыдущей сборке кернинг был сохранён из1.002.

[РЕШЕНИЕ · 16.10.2026] В1.004 выполнен полный попарный проход кернинга.
[Сравнение до/после](docs/img/kerning_comparison.svg),
[все пары и альтернативы в PDF](dist/VeryPeriSerifDraft/kerning-all-pairs.pdf),
[интерактивный лист — скачать и открыть](dist/VeryPeriSerifDraft/kerning-proof.html),
[метод и результаты проверки](docs/kerning-review.md).

[РЕШЕНИЕ · 16.10.2026] **1.005:** устранены верхние слипания засечек,
добавлены18 типографских символов. [Что исправлено](docs/regular-polish.md)
и [лист доводки](docs/img/regular_polish.svg).

[Исследование будущего Italic](docs/italic-analysis.md): русская письменная
основа, измеренные доноры, карта повторного использования и порядок работы.
[Сравнительный лист](docs/img/italic_research.svg).
