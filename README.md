# Very Peri Serif

Рабочее кириллическое расширение **Instrument Serif Regular**.
Здесь сохранены исходники, SVG-презентации, пробные TTF/WOFF2 и проверки
совместной разработки. Полный алфавит и окончательный кернинг ещё не готовы.
Отдельный Italic пока отложен; строчные Regular используют письменные скелеты.

Порядок работы: [CLAUDE.md](CLAUDE.md), актуальные
[решения пользователя](docs/decisions.md), [инструкция](docs/instruction.md).
Сверка полезных правил и расхождений: [instruction-review.md](docs/instruction-review.md).
Статусы букв: [progress.json](data/progress.json), паспорта: [letters.json](data/letters.json).
Актуальная сверка двух веток: [shared-alphabet-inventory.json](data/shared-alphabet-inventory.json).
Прежний [cross-branch-inventory.json](data/cross-branch-inventory.json) сохранён
как исторический снимок; он не включает последние добавления обеих веток.
Текущие добавления и выборы отражены в progress.json.
Есть материалы для **28 строчных**: 19 в наших пробных шрифтах и ещё
л/м/н/п/ш/ъ/ы/ь/ю отдельными GLIF/SVG в актуальной ветке Клода.
Из них 20 букв имеют отдельные исследования или явно выбранное соответствие
донору, 8 используют исходные латинские омоглифы из нашего реестра.
Это наличие рисунков и кандидатов, а не число окончательно принятых глифов.

[Общая карта алфавита](https://github.com/rahatulyerbolat05-dotcom/Very-Peri-serif/blob/claude/upbeat-faraday-mzabid/docs/img/alphabet_status.png)
объединяет **46 из 66 русских букв** (18 прописных, 28 строчных) и
**8 из 18 дополнительных казахских**. Наши контуры выделены синим,
контуры ветки Клода — зелёным. Карта учитывает исходники и открытые варианты;
она не означает сборку общего производственного шрифта.
Два расхождения показаны для дальнейшего выбора: **т** — наша выбранная
m-образная02 против Т-образной t1 Клода; **к** — наши две головки против
его головки от ı и короткой контекстной формы.
Общие и и й01 совпадают с родными u и ŭ; компактная й02 остаётся кандидатом.

## Текущие пробы

| Материалы | Состояние |
|---|---|
| [б](studies/regular/be/), [г](studies/regular/ghe/) | Основные «Капля», другие рисунки сохранены |
| [в](studies/regular/ve/) | Два варианта, выбор основного открыт |
| [ж](studies/regular/zhe-selected/) | Точный выбранный глиф из наработок пользователя с Клодом |
| [з](studies/regular/ze/) | Основная 01; вторая удалена по просьбе пользователя |
| [и](studies/regular/i-selected/) | Основная чашеобразная; диагональная — ss07 |
| [й](studies/regular/shorti/), [к](studies/regular/ka/) | Два рисунка каждой буквы, выбор основного открыт |
| [прежние д](studies/regular/de-loop/) | Сохранены; пользователь запросил переработку |
| [g-подобные д](studies/regular/de-native/) | Отклонены пользователем: читаются как g; сохранены для истории |
| [печатные д](studies/regular/de-cyrillic/) | Оба рисунка отклонены: не соответствуют письменному принципу строчных |
| [письменные д](studies/regular/de-cursive/) | Обе реализации отклонены: кривые и окончания не попали в стиль |
| [д](studies/regular/de-reimagined/) | Основная01 «Острый свод»;02 «Перьевой поворот» сохранён отдельно альтернативой |
| [т](studies/regular/te/) | Основная02 «Письменный выход»;01 «Родные арки» — альтернативный стиль |
| [э](studies/regular/ereversed-refined/) | Основная02 «Капля a — ниже»;01 «Капля a — выше» сохранена отдельной альтернативой |
| [ш, ь, ы, ъ в ветке Клода](https://github.com/rahatulyerbolat05-dotcom/Very-Peri-serif/tree/f8e2fb3cac2d33146871f2095aac52a343a5f2ef/docs/glyphs) | Выбраны R1 / S3 / Y1 / K2; пока отдельные эскизы, в наши шрифты не включены |
| [л, м, н, п, ю в актуальной ветке Клода](https://github.com/rahatulyerbolat05-dotcom/Very-Peri-serif/tree/d2cd2ee856a85d99aa4880b8f44b126ee49a1eca/docs/glyphs) | Основы л1 / m1 / n4 / native n / yu1; л и м ещё ждут подтверждения, в наши шрифты не включены |

Сборки содержат **абвгдежзийкорстухэё**, включая унаследованные а/е/о/р/с/у/х.
Некоторые формы и промежуточные метрики в ранних папках относятся к той
стадии разработки; последующие выбранные контуры находятся в поздних сборках.
История и резервные версии сохранены в [studies/archive](studies/archive/).

После объединения исходников не интегрированы строчные **ф, ц, ч, щ, я**
и прописные **Б, Д, З, И, Й, У, Ф, Ц, Ч, Щ, Ъ, Ы, Ь, Э, Я**.
Для ф уже сохранён авторский SVG в ветке Клода; прежний контур удалён по
просьбе пользователя, поэтому на карте она пока не считается интегрированной.
Казахские без готовых основ: **Ә, Қ, Ң, Ұ, Һ / ә, ғ, қ, ң, ұ** — 10 букв.
Последнее обновление ветки Клода добавило **Ғ, Ө, ө** (Gh2 / O1 / o1).
Прописная Ж Клода и наша строчная ж — разные регистры. Его основная м
V-образная; латинская m там лишь альтернатива и не заменяет нашу т.

![Два варианта э рядом с исходными буквами](studies/regular/ereversed-refined/comparison.svg)

Актуальное направление строчных: письменные/курсивные скелеты с вертикальной
осью, контрастом и деталями Instrument Serif Regular. Отдельное начертание
Italic остаётся отложенным. Прежние запреты арок из исторической инструкции
исправлены; уже выбранные глифы сохраняются.

Текущая работа — [строчная э](studies/regular/ereversed-refined/): выраженная
капля из родной a и заново выстроенный свод. У01 вход выше, у02 ниже.
Пользователь выбрал02 основной;01 сохранена отдельно альтернативой.
Точные контуры и метрики закреплены в [selected-ereversed.json](data/selected-ereversed.json).
[Сравнение с прежними](studies/regular/ereversed-refined/evolution.svg)
и [размерные пробы э](studies/regular/ereversed-refined/sizes.svg).

У [строчной т](studies/regular/te/): две верхние арки
на основе native m;01 сохраняет исходные окончания,02 использует правый
выход a/d. Пользователь выбрал02 основной,01 альтернативным стилем.
Д01 «Острый свод» выбрана пользователем;
её контур и метрики сохранены точно в обеих пробах т.

[Презентация т](studies/regular/te/comparison.svg) и [размерные пробы](studies/regular/te/sizes.svg).
[Г в актуальном контексте](studies/regular/ghe/context-with-te/) показывает
выбранную «Каплю» и сохранённый «Клюв» рядом с т02 и д01.

Предшествующий [разбор кривых и окончаний](studies/reference-analysis/de-curves-deep/)
сохраняет измерения родных деталей и сравнение 40 внешних семейств.

[Исследование реальных кириллических конструкций д](studies/reference-analysis/cursive-de/)
сравнивает восемь форм/настроек из шести шрифтов с настоящими U+0434,
локализациями и ss10. Источники закреплены по коммиту и SHA-256.

Пробные шрифты можно скачать непосредственно из папок исследований.
Для к есть четыре сочетания двух головок и двух краток й. Новое исследование д
сохраняет эти сочетания; ни первая к, ни первая кратка й не назначены основной
по умолчанию. Переключатели ss02–ss07 и ограничения описаны в паспортах букв.

## Воспроизведение

Проверено на Python 3.12 с зависимостями из requirements-fonts.txt.
Установка для своей машины:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-fonts.txt
.venv/bin/python tools/prepare_reference.py
.venv/bin/python tools/build_shorti.py
.venv/bin/python tools/build_ka.py --base-dir build/regular/shorti
.venv/bin/python tools/build_de_native.py --base-dir build/regular/ka
.venv/bin/python tools/build_de_cyrillic.py --base-dir build/regular/ka
.venv/bin/python tools/build_de_cursive.py --base-dir build/regular/ka
.venv/bin/python tools/build_de_reimagined.py --base-dir build/regular/ka
.venv/bin/python tools/build_te.py --base-dir build/regular/de-reimagined
.venv/bin/python tools/build_ereversed.py --base-dir build/regular/te
.venv/bin/python tools/build_ereversed.py --revision refined --base-dir build/regular/te
.venv/bin/python tools/audit_de_reimagined.py
.venv/bin/python tools/research_cursive_de.py
.venv/bin/python tools/verify_studies.py
.venv/bin/python tools/verify_studies.py --rebuilt-dir build/regular
```

Выходы создаются в игнорируемой папке build/regular; сохранённые studies
и журнал выбора не перезаписываются. Для одиночной сборки к или д можно
использовать сохранённые studies как входные данные: это значения по умолчанию.

prepare_reference.py загружает только необходимые Regular-файлы на точном
коммите **65c0ef225f386a3c7e87570a4aa9cc0262c2fd81**, проверяет SHA-256
и отказывается заменять отличающийся исходник. Старый fetch_reference.sh
сохранён для прежних исследований; он следит за веткой upstream и поэтому
не используется как гарантия закреплённого источника новых сборок.

Проверки импорта, шрифтов и воспроизведения записываются в
[data/repository-verification.json](data/repository-verification.json).
FontBakery, Hyperglot и приёмка полного набора не заявлены как пройденные.

## Лицензия и атрибуция

Производные пробные шрифты распространяются под [SIL OFL 1.1](OFL.txt).
Исходные авторы: [AUTHORS.txt](AUTHORS.txt), участники: [CONTRIBUTORS.txt](CONTRIBUTORS.txt).
Сохранён Copyright 2022 The Instrument Serif Project Authors.
Наши материалы являются рабочим расширением и не выдаются за официальный
кириллический релиз Instrument. Эталонные бинарники, сгенерированные PNG,
пользовательские архивы и библиотеки Python в Git не добавляются.
