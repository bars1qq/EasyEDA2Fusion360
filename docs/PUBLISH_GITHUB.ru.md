# Как выложить проект на GitHub

Инструкция для тех, кто раньше не публиковал проекты на GitHub. Ниже — три способа:
через GitHub Desktop (самый простой), через сайт GitHub и через командную строку.
Выберите один — результат одинаковый.

---

## Что попадёт в репозиторий

В репозиторий кладём **исходники и документацию**, а готовый `.exe` — в раздел
**Releases** (иначе репозиторий распухнет и GitHub начнёт ругаться).

```
easyeda2kicad-gui/
├── README.md                  ← главная страница проекта
├── LICENSE                    ← AGPL-3.0
├── THIRD_PARTY_NOTICES.md     ← лицензии сторонних компонентов
├── .gitignore                 ← что не коммитить
├── requirements.txt           ← зависимости Python
├── requirements-dev.txt       ← PyInstaller для сборки
├── build.ps1                  ← сборка .exe и ZIP
├── app.py                     ← интерфейс
├── core.py                    ← конвертация
├── icon.ico
├── icon.png
└── docs/
    ├── USAGE.md               ← инструкция пользователя
    ├── BUILD.md               ← сборка из исходников
    ├── PUBLISH_GITHUB.md      ← этот файл
    └── screenshots/
        ├── main.png
        └── empty.png
```

Папку `EasyEDA2KiCad-repo` из этого проекта можно брать как есть — она уже
собрана по этой структуре.

---

## Вариант 1. GitHub Desktop (рекомендую)

Подходит, если не хочется запоминать команды.

1. Установите **GitHub Desktop**: https://desktop.github.com/
2. Войдите в свой аккаунт GitHub (Create account, если его нет).
3. Меню **File → New repository…**
   - **Name:** `easyeda2kicad-gui`
   - **Local path:** выберите папку, где будет лежать проект.
   - **Initialize this repository with a README:** снимите галочку — README у нас уже есть.
   - Нажмите **Create repository**.
4. Откройте созданную папку в проводнике и скопируйте туда **всё содержимое**
   папки `EasyEDA2KiCad-repo` (файлы и папку `docs`).
5. Вернитесь в GitHub Desktop — справа появится список изменений.
6. Внизу слева в поле **Summary** напишите `Initial commit` и нажмите
   **Commit to main**.
7. Нажмите **Publish repository** (сверху).
   - Снимите галочку **Keep this code private**, если хотите, чтобы проект был
     доступен всем.
   - Нажмите **Publish repository**.
8. Готово: репозиторий появился на GitHub, ссылку можно отправлять людям.

---

## Вариант 2. Через сайт GitHub (без установки программ)

1. Зарегистрируйтесь на https://github.com/ (если ещё нет аккаунта).
2. Нажмите **+** в правом верхнем углу → **New repository**.
3. Заполните:
   - **Repository name:** `easyeda2kicad-gui`
   - **Description:** `GUI: EasyEDA component link → KiCad symbol, footprint and STEP`
   - **Public**
   - **Initialize this repository with a README** — не включайте.
4. Нажмите **Create repository**.
5. На странице пустого репозитория нажмите **uploading an existing file**
   (или **Add file → Upload files**).
6. Перетащите в окно **содержимое** папки `EasyEDA2KiCad-repo`:
   `README.md`, `LICENSE`, `app.py`, `core.py`, `icon.ico`, `icon.png`,
   `requirements.txt`, `requirements-dev.txt`, `build.ps1`,
   `THIRD_PARTY_NOTICES.md` и папку `docs`.
7. Внизу нажмите **Commit changes**.

Файл `.gitignore` на сайте иногда не виден в проводнике. Если его не удалось
перетащить, создайте вручную: **Add file → Create new file**, имя `.gitignore`,
вставьте содержимое из файла `.gitignore` этого проекта.

---

## Вариант 3. Командная строка (Git)

1. Установите **Git for Windows**: https://git-scm.com/download/win
2. Откройте папку проекта в проводнике, правой кнопкой → **Open Git Bash here**
   (или запустите Git Bash и перейдите в папку через `cd`).
3. Выполните:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
```

4. Создайте пустой репозиторий на GitHub (как в варианте 2, без README)
   и скопируйте его адрес вида `https://github.com/ВАШ_ЛОГИН/easyeda2kicad-gui.git`.
5. Выполните:

```bash
git remote add origin https://github.com/ВАШ_ЛОГИН/easyeda2kicad-gui.git
git push -u origin main
```

При первом пуше Git попросит войти в GitHub — проще всего через
**Git Credential Manager**, который устанавливается вместе с Git for Windows.

---

## Релиз с готовым ZIP

Пользователям не нужен Python — им нужен готовый архив. Он кладётся в **Releases**.

1. Соберите архив: `.\build.ps1` (см. [BUILD.md](BUILD.md)) — получится
   `EasyEDA2KiCad-portable.zip`.
2. На странице репозитория откройте **Releases** → **Create a new release**
   (или **Draft a new release**).
3. **Choose a tag** → напишите `v1.0.0` → **Create new tag**.
4. **Release title:** `v1.0.0 — первый релиз`.
5. В описании напишите, что нового, и укажите требования (Windows 10/11).
6. В блоке **Attach binaries** прикрепите `EasyEDA2KiCad-portable.zip`.
7. Нажмите **Publish release**.

Ссылка `../../releases/latest` в README автоматически ведёт на последний релиз.

> Ограничение GitHub: файл в релизе — до 2 ГБ. Наш архив ~11 МБ, всё в порядке.

---

## Оформление репозитория

После публикации зайдите в **Settings** репозитория (шестерёнка):

- **Description:** `GUI: EasyEDA component link → KiCad symbol, footprint and STEP`
- **Topics:** `kicad`, `easyeda`, `fusion360`, `pcb`, `eda`, `lcsc`, `jlcpcb`
- **Social preview:** загрузите `docs/screenshots/main.png` — так ссылка на проект
  будет выглядеть аккуратно в соцсетях и мессенджерах.

README уже содержит скриншот и быстрый старт, отдельно ничего добавлять не нужно.

---

## Лицензия и правовые моменты

- Проект распространяется по **AGPL-3.0** (файл `LICENSE`). Это требование
  движка easyeda2kicad, который используется внутри.
- AGPL означает: если вы публикуете **сборку** или **изменённую версию**,
  исходный код должен быть доступен. Для личного использования ничего делать не нужно.
- Не удаляйте `LICENSE` и `THIRD_PARTY_NOTICES.md` из репозитория и из архива.
- В README написано, что проект **не аффилирован** с EasyEDA, JLCPCB и LCSC —
  это важно, чтобы не было претензий.
- Данные компонентов принадлежат их авторам. Приложение только конвертирует то,
  что пользователь открыл публично.

---

## Как выпускать обновления

1. Внесите изменения в `app.py` / `core.py`.
2. Закоммитьте их (GitHub Desktop: Summary → Commit → Push).
3. Поднимите версию в описании релиза (`v1.0.1`) и соберите новый ZIP.
4. Опубликуйте новый Release и прикрепите архив.

Старые релизы остаются доступными — пользователи могут скачать любую версию.

---

## Чек-лист перед публикацией

- [ ] В репозитории нет папок `dist/`, `build/`, `vendor/`, `.venv/`, `__pycache__/`.
- [ ] `README.md` открывается и картинка по ссылке `docs/screenshots/main.png` видна.
- [ ] `LICENSE` и `THIRD_PARTY_NOTICES.md` на месте.
- [ ] В Release прикреплён `EasyEDA2KiCad-portable.zip`.
- [ ] Проверено: архив распаковывается, `EasyEDA2KiCad.exe` запускается на чистой машине.
- [ ] В репозитории нет токенов, паролей и личных путей вида `C:\Users\ИМЯ\...`
      (в коде путей быть не должно — проверьте `grep` по `C:\Users`).

---

## Если что-то пошло не так

| Проблема | Решение |
|---|---|
| GitHub Desktop не видит изменения | Проверьте, что файлы лежат внутри папки репозитория, а не рядом |
| При push просит пароль | Используйте Git Credential Manager или personal access token |
| GitHub ругается на размер | Уберите из коммита `dist/`, `vendor/`, `.venv/`; `.exe` — только в Releases |
| Картинка в README не открывается | Проверьте регистр пути: `docs/screenshots/main.png` |
| Случайно закоммитили лишнее | `git rm -r --cached <папка>`, добавьте в `.gitignore`, закоммитьте |
