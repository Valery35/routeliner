# Публикация выпусков

Порядок объявления выпусков модуля Routeliner для QGIS. Файл заведён по
образцу doc/PUBLISH.md из PlanetX Lite, и сессии модуля читают этот же файл,
когда объявляют выпуск на площадках из списка ниже. Хабр и GIS-Lab не используются, решение автора от 28 октября 2026
года.

## Правила

- Выпуск объявляется на всех площадках списка, решение автора
  от 5 ноября 2026 года.
- Учётные записи создаёт и подтверждает автор. Доступ OAuth выдаётся
  только по отдельному согласию автора.
- Помощник публикует через Claude in Chrome в окне с группой вкладок
  Claude. Вход в другом окне Chrome помощнику не виден.
- Каждая публикация проверяется после отправки - запись открывается
  и сверяется. Ссылка на неё заносится в журнал ниже.
- Тексты на английском - для международных площадок, на русском -
  для Telegram, ВК и Facebook.
- Тексты объявлений пишутся по своду RULES.ru.md и RULES.en.md и
  проверяются measure.py в полосе letter до публикации.
- На каждую версию, загруженную в каталог модулей, на GitHub заводится
  релиз с тем же номером и архивом модуля (AGENTS.md, раздел «Выпуск»).

## Площадки

Список взят из PlanetX Lite, но площадки, которые подходят только для
PlanetX Lite и языка Rust, сюда не вошли. Тексты объявлений лежат рядом,
в doc/posts_<версия>.md.

| Площадка | Учётная запись | Как публиковать |
|---|---|---|
| GitHub, выпуск | Valery35 | Релиз по тегу без буквы v, архив модуля routeliner-<версия>.zip |
| Dropbox | - | routeliner.zip и routeliner_repo.zip в Dropbox\ИИ\Routeliner |
| Каталог QGIS | Valery35 | plugins.qgis.org/plugins/routeliner, архив без tests |
| Telegram, @qgis_isolines | автор | Бот PlanetX присылает черновик после релиза на GitHub, пост уходит после «Опубликовать» |
| ВК, vk.ru/qgismodules | автор | Пост или статья через Claude in Chrome |
| OSGeo Discourse, discourse.osgeo.org | автор, вход через GitHub | Раздел General (id 4) |
| LinkedIn | автор | Пост на английском с хештегами, без продвижения |
| Facebook | автор | Пост на русском на странице автора |
| X, @Valery35 | автор | До 280 знаков, ссылка считается за 23 |
| Mastodon, en.osm.town | Vaery35 | Пост на английском |
| Reddit r/gis, r/QGIS | автор | Только автор, сайт закрыт для браузеров помощника |
| Сайт informpp.ru | автор | Страница модуля [www.informpp.ru/главная-страница/qgis-routeliner](https://www.informpp.ru/главная-страница/qgis-routeliner), страница расширения [www.informpp.ru/главная-страница/routeliner-rustgis](https://www.informpp.ru/главная-страница/routeliner-rustgis) |

Особенности площадок:

- Каталог QGIS. Новая версия проходит автоматическую проверку и ручное
  одобрение модератора. Архив с папкой tests проверку безопасности
  не проходит.
- Telegram. Сообщение автору с кнопкой «Подготовить пост» отправляет
  .github/workflows/telegram-release.yml, как только на GitHub опубликован
  релиз, а без секретов хранилища этот шаг ничего не делает.
- OSGeo Discourse. В главный раздел QGIS темы не ставятся,
  его подразделы - языковые и региональные.

## Журнал публикаций

### Routeliner 0.3.1, 23 сентября 2026 года

- GitHub: https://github.com/Valery35/routeliner/releases/tag/0.3.1
- Каталог QGIS - версия загружена

### Routeliner 0.4.0 и 0.4.3, 24 сентября 2026 года

- GitHub: https://github.com/Valery35/routeliner/releases/tag/0.4.0
- GitHub: https://github.com/Valery35/routeliner/releases/tag/0.4.3
- Каталог QGIS - обе версии загружены
- На GitHub остался лишний тег v0.4.3, удалить его может автор

### Routeliner 0.5.0, 24-25 сентября 2026 года

- GitHub: https://github.com/Valery35/routeliner/releases/tag/0.5.0
- Каталог QGIS - версия загружена
- Dropbox - архивы обновлены

### Routeliner 0.5.1, 25 сентября 2026 года

- GitHub: https://github.com/Valery35/routeliner/releases/tag/0.5.1
- Каталог QGIS: https://plugins.qgis.org/plugins/routeliner/version/0.5.1/
- Dropbox - архивы обновлены
- Telegram - текст поста подготовлен 25 сентября 2026 года, публикует автор

### Routeliner 0.5.2, 25 октября 2026 года

- Каталог QGIS: https://plugins.qgis.org/plugins/routeliner/version/0.5.2/
- GitHub - релиза 0.5.2 нет, последним стоит 0.5.1
- Dropbox - архивы обновлены до 0.5.2 5 ноября 2026 года
- Тексты для всех площадок - doc/posts_0.5.2.md
