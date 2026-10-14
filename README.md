# Very Peri Serif

Рабочее кириллическое расширение **Instrument Serif Regular**.
Здесь сохранены исходники, SVG-презентации, пробные TTF/WOFF2 и проверки
совместной разработки. Полный алфавит и окончательный кернинг ещё не готовы.
Курсив пока отложен.

Порядок работы: [CLAUDE.md](CLAUDE.md), актуальные
[решения пользователя](docs/decisions.md), [инструкция](docs/instruction.md).
Сверка полезных правил и расхождений: [instruction-review.md](docs/instruction-review.md).
Статусы букв: [progress.json](data/progress.json), паспорта: [letters.json](data/letters.json).

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
| [новое исследование д](studies/regular/de-cyrillic/) | Две печатные конструкции с площадкой и короткими ножками; выбор открыт |

Сборки содержат **абвгдежзийкорсухё**, включая унаследованные а/е/о/р/с/у/х.
Некоторые формы и промежуточные метрики в ранних папках относятся к той
стадии разработки; последующие выбранные контуры находятся в поздних сборках.
История и резервные версии сохранены в [studies/archive](studies/archive/).

![Два рисунка к и исходные латинские соседи](studies/regular/ka/comparison.svg)

![Две кириллические д и исходные латинские соседи](studies/regular/de-cyrillic/comparison.svg)

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
