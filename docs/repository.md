# Где скачивать шрифт и где продолжать работу

**[Скачать актуальный Very Peri Serif — Regular + Italic](../dist/VeryPeriSerif-latest.zip).**
Текущая версия — **1.113**. В ZIP находятся оба начертания, TTF/OTF/WOFF2,
лицензия, авторы и образцы. Для компьютера установите два TTF из `fonts/ttf`.

## Одна рабочая ветка

`claude/upbeat-faraday-mzabid` — единственная рабочая ветка и ветка GitHub по умолчанию.
Открывая корень репозитория, вы попадаете в неё. Продолжать разработку следует здесь.

Постоянный адрес загрузки:
<https://github.com/rahatulyerbolat05-dotcom/Very-Peri-serif/raw/refs/heads/claude/upbeat-faraday-mzabid/dist/VeryPeriSerif-latest.zip>

`tools/package_release.py` обновляет `VeryPeriSerif-latest.zip` и `dist/latest.json`
после успешной проверки версионного пакета. `latest` — обновляемая ссылка-копия;
версионные архивы сохраняют прежние байты и контрольные суммы.

## История сохранена

При объединении 25.10.2026:

| Прежняя ветка | Что сохранено |
|---|---|
| `codex/premium-family` | Полностью совпадала с основной; вся работа уже в ней. |
| `claude/blissful-mayer-rp8s4x` | Старый срез Italic I026; все коммиты входят в основную историю. |
| `codex/cyrillic-studies` | Её отдельные 23 коммита исследований включены вторым родителем merge-коммита; исходный срез доступен по тегу `archive/cyrillic-studies-2026-10-25`. |

Последний merge сохраняет принятые текущие исходники и выпуск 1.113.
Старые альтернативные эскизы доступны в собственной исторической версии:
[архив исследований](https://github.com/rahatulyerbolat05-dotcom/Very-Peri-serif/tree/archive/cyrillic-studies-2026-10-25).

Для конкретной неизменной сборки используйте тег `v1.113` или
[версионный архив](../dist/VeryPeriSerif-1.113.zip).
Для скилла — тег `skill-ofl-cyrillic-v1.0.0` и
[его ZIP](../dist/skills/ofl-cyrillic-extension-1.0.0.zip).
Теги — сохранённые версии и исторические точки, рабочая ветка остаётся одна.
