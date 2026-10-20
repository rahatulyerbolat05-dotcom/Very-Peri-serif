# Very Peri Serif

> Кириллическое расширение [Instrument Serif](https://github.com/Instrument/instrument-serif): русский и казахский, начертания Regular и Italic.

![Very Peri Serif: Regular и Italic](docs/img/header.svg)

Very Peri Serif сохраняет латиницу Instrument Serif без изменений и добавляет кириллицу, которой в нём нет. Новые
буквы собраны из частей родных глифов Instrument Serif (стоек, засечек, чаш, капель и хвостов) по измеренным правилам,
чтобы у кириллицы были те же узкие пропорции, контраст и дисплейный характер, что у латиницы. Как и оригинал, шрифт
рассчитан на крупный кегль.

[English](README.md)

## Скачать

| | |
|---|---|
| [`dist/VeryPeriSerif-1.016.zip`](dist/VeryPeriSerif-1.016.zip) | всё перечисленное ниже вместе с лицензией, одним архивом |
| [`fonts/ttf`](fonts/ttf) | TrueType для программ на компьютере (Windows, macOS, Linux, Figma, Adobe, Office) |
| [`fonts/otf`](fonts/otf) | OpenType CFF, тот же рисунок кубическими кривыми (ставить TTF или OTF, не оба) |
| [`fonts/webfonts`](fonts/webfonts) | WOFF2 и [`very-peri-serif.css`](fonts/webfonts/very-peri-serif.css) для сайтов |
| [`docs/specimen`](docs/specimen) | образец шрифта в PDF |

Regular — выпуск 1.016. Italic 0.250 — тестовый: все буквы на месте, формы ещё уточняются.

## Языки

Латиница: 86 языков Instrument Serif. Кириллица: **русский** и **казахский**. Алфавиты болгарского, киргизского и
монгольского тоже покрыты (проверено по буквам); белорусского, украинского, сербского, татарского и узбекского пока нет.

## Функции OpenType

| Функция | Regular | Italic |
|---|---|---|
| `kern` | кернинг кириллицы, все кириллические и смешанные пары проверены в HarfBuzz | кернинг кириллицы, хвосты под строкой не сталкиваются |
| `calt` | у п, к, қ, н ножка меняется по следующей букве | — |
| `ss01` | а с е ё из родного набора ss01 для a c e ë | то же из родного набора курсива |
| `ss02`–`ss06` | — | д с выносом вверх, печатная т, печатная г, к и ж с выносом, э из родной c |
| `ss07` `ss08` `ss09` | печатная д, альтернативная т, прежние хвосты | — |
| `locl` | — | сербские и македонские формы б г д п т |
| `aalt` `ccmp` `liga` `dlig` `case` `ordn` `mark` `mkmk` | родные функции Instrument Serif | родные функции Instrument Serif |

## Сборка

```sh
python -m pip install -r requirements.txt
make
```

`make` собирает оба начертания из исходников (`data/`, `tools/`, `font/`) и публикует `fonts/`, отчёты проверки в
[`docs/qa`](docs/qa) и архив в `dist/`. Шаги и проверки: [font/README.md](font/README.md).

## Изменения

- 20.10.2026: один архив выпуска, OTF и веб-шрифты рядом с TTF; проверены лицензия и списки авторов.
- 19.10.2026: Regular 1.016, прямые края и выглаживание; Regular и Italic связаны в одно семейство.
- 17–19.10.2026: тестовые сборки курсива I001–I025.
- 17.10.2026: Regular 1.000, первый выпуск; 1.001–1.015 поля, кернинг, полировка контуров.

Каждое решение записано в [CLAUDE.md](CLAUDE.md); прежние заметки в [docs/history.md](docs/history.md).

## Благодарности

Instrument Serif нарисовал [Rodrigo Fuenzalida](https://rfuenzalida.com) под руководством
[Jordan Egstad](https://egstad.com), [JD Hooge](http://jdhooge.com/) и [Jack De Caluwé](https://jackdecaluwe.com/) для
[Instrument](https://instrument.com). Кириллическое расширение — [Yerbolat](https://github.com/rahatulyerbolat05-dotcom).
Строчная д в Regular — изменённый контур [Cormorant Garamond](https://github.com/CatharsisFonts/Cormorant)
(The Cormorant Project Authors). Very Peri Serif не создан и не одобрен компанией Instrument.

## Участие ИИ

Контуры, поля и кернинг кириллицы сделаны с помощью систем ИИ (Anthropic Claude, OpenAI Codex) под руководством автора:
он поставил задачу, выбирал и правил каждую форму, часть форм нарисовал сам. Латиница — Instrument Serif без изменений.
Подробно: [FONTLOG.txt](FONTLOG.txt), [font/ai-disclosure.json](font/ai-disclosure.json).

## Лицензия

Шрифт распространяется по лицензии SIL Open Font License, версия 1.1 ([OFL.txt](OFL.txt)). Лицензия и ответы на частые
вопросы: https://openfontlicense.org
