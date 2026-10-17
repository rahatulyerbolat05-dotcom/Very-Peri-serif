# Very Peri Serif — Regular 1.008

Устанавливаемое начертание Regular: русский, казахский и латиница.
В меню редактора шрифт называется **Very Peri Serif**, начертание **Regular**.

## Установка

Откройте `VeryPeriSerif-Regular.ttf` и нажмите «Установить».
При необходимости перезапустите редактор. Шрифт имеет собственное имя;
ранее установленная версия Very Peri Serif Draft остаётся отдельным семейством.

`VeryPeriSerif-Regular.woff2` — версия для сайта.
`specimen.pdf` и `proof.svg` показывают набор готовым шрифтом.

## Возможности

- Все66 русских и18 казахских букв, латиница исходного Instrument Serif,
  цифры и текстовые знаки; в том числе ₸, ₽, ₴, №, кавычки и тире.
- `kern`, `liga`, `calt`: кернинг, стандартные латинские лигатуры
  fi/fl/ffi/ffl и контекстные формы п/к/қ, выходная ножка к и К. Включены по умолчанию.
- `ss01`: родной стилистический набор, согласованный с а/с/е/ё.
- `ss07`: печатная д вместо основной округлой д с нижним хвостом.
- `ss08`: альтернативная т с горизонтальной верхней частью.
- `ss09`: прежние окончания ц/щ/қ/ң и прописных вместо основных капель.
- `aalt`: доступные альтернативы; `dlig`: родные необязательные
  латинские лигатуры. Поддерживаются верхние акценты и их привязка.

В редакторе оставьте включёнными кернинг, стандартные лигатуры и
контекстные альтернативы. Пара лл остаётся двумя буквами с кернингом.

## Для сайта

```css
@font-face {
  font-family: "Very Peri Serif";
  src: url("VeryPeriSerif-Regular.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
body { font-family: "Very Peri Serif", serif; }
.printed-de { font-feature-settings: "ss07" 1; }
.old-tails { font-feature-settings: "ss09" 1; }
```

## Состав релиза

Regular 1.008 фиксирует последние формы: компактные составные буквы,
суженную чашу д, усиленные стенки з, авторские капли с плавными стыками
и различимые У/Ү. Это одно прямое начертание веса400; курсив развивается отдельно.

Контуры, ширины, кернинг и функции OpenType соответствуют проверенной
геометрии1.012. Для финального релиза оформлены имя, версия и метаданные.
Проверки относятся к конечным TTF/WOFF2: результаты — `validation.json`,
`kerning-validation.json`, `release-validation.json`, `quality-summary.json`.
`SHA256SUMS.txt` позволяет проверить файлы архива.

## Повторная сборка

Нужны Git, Python3.12 и полная история этого репозитория. Подготовка
окружения и точный коммит Instrument Serif — в `font/README.md` репозитория.
После установки `font/requirements.txt` из корня репозитория:

```sh
python -I tools/build_regular_release.py
```

Команда заново строит шрифт по текущим исходникам, проверяет финальные
файлы и формирует `dist/VeryPeriSerif-Regular.zip`. Для дополнительной
проверки FontBakery и Hyperglot:

```sh
python -m pip install -r font/requirements-quality.txt
python -I tools/build_regular_release.py --quality
```

## Лицензия и авторство

SIL Open Font License1.1. Разрешены личное и коммерческое использование,
встраивание и модификация на условиях OFL. Полный текст — `OFL.txt`.

Instrument Serif: Copyright2022 The Instrument Serif Project Authors;
Rodrigo Fuenzalida и Jordan Egstad, см. `AUTHORS.txt`.
Кириллическое расширение и изменения: участники Very Peri Serif,2026.
Строчная д — изменённый Cormorant Garamond Regular ss10:
Copyright2015 the Cormorant Project Authors. Её лицензия и атрибуция —
`Cormorant-OFL.txt`, `Cormorant-NOTICE.txt`.
