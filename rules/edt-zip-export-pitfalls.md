# EDT Zip Export Caveats

> Основа — правило из набора [Desko77/claude-code-skills-1c](https://github.com/Desko77/claude-code-skills-1c/blob/main/rules/edt-zip-export-pitfalls.md) (MIT), версия лета 2026. Здесь добавлен раздел 2 (объект не зарегистрирован в `Configuration.mdo`). У автора правило с тех пор дополнено, свежую версию смотрите там.

Ограничения EDT при экспорте конфигурации в инфобазу (incremental sync через zip-архив).

Применяется: при создании/правке объектов метаданных в EDT-проектах (Configuration или Extension),
особенно через MCP `edit_metadata` / прямую правку `.mdo`. Касается агента разработчика mcp-edt.

Симптомы общие: EDT-валидация (`get_project_errors`) чистая, но при запуске/обновлении ИБ платформа
падает с `RuntimeCoreException` и сообщением `Файл не обнаружен 'zip:///...'`.

---

## 1. Подсистема с командным интерфейсом без CommandInterface.cmi

### Симптом

```
Ошибка загрузки/выгрузки конфигурации
по причине:
Файл не обнаружен 'zip:///Ext/CommandInterface.xml'
```

Стек: `DesignerSessionThickClientLauncher.importIncrementalXmlToInfobase` →
`LoadFilesQuery.processExecutionResponses`.

### Условие

Создана собственная подсистема (не Adopted) с `<includeInCommandInterface>true</includeInCommandInterface>`
в `.mdo`, но рядом нет файла `CommandInterface.cmi`.

### Фикс

Создать минимальный `CommandInterface.cmi` рядом с `.mdo` подсистемы:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cmi:CommandInterface xmlns:cmi="http://g5.1c.ru/v8/dt/cmi"/>
```

Затем `clean_project` + `revalidate_objects` для подсистемы.

### Когда применять профилактически

При создании любой новой собственной подсистемы расширения через `edit_metadata create_object Subsystem`,
если предполагается `includeInCommandInterface=true` - сразу создавать пустой `CommandInterface.cmi`.

В типовой конфигурации (без расширения) у части подсистем `.cmi` отсутствует и всё работает - там
индекс EDT давно собран. Для свежедобавленных в расширение лучше создавать явно.

---

## 2. Новый объект не зарегистрирован в Configuration.mdo (file-drop .mdo без конструктора)

### Симптом

```
Ошибка загрузки/выгрузки конфигурации
по причине:
Ошибка добавления объекта Document uuid="..." : нельзя добавлять объекты
метаданных без загрузки родительского объекта.
```

Стек: `DesignerSessionThickClientLauncher.importIncrementalXmlToInfobase` →
`LoadFilesQuery.processExecutionResponses`. EDT-валидация (`get_project_errors`) при этом ЧИСТАЯ.

### Условие

Новый объект метаданных (документ / справочник / перечисление / регистр / обработка) создан
**дропом `.mdo`-файла** (генерация из эталона скриптом), а НЕ через конструктор EDT.

**F5 / Refresh перечитывает существующие файлы, но НЕ добавляет новый объект в состав
конфигурации** (`Configuration/Configuration.mdo`). Регистрацию в составе делает ТОЛЬКО конструктор
EDT при создании объекта. В итоге папка объекта на диске есть, а в `Configuration.mdo` его нет →
платформа не может добавить объект «без загрузки родительского объекта» (родитель = сам объект
Configuration и его список объектов данного типа).

### Фикс

Добавить объект в `Configuration/Configuration.mdo` в секцию своего типа (формат — как у соседних
объектов; порядок не критичен, EDT пересортирует при следующем сохранении):

```xml
<documents>Document.Имя</documents>
<catalogs>Catalog.Имя</catalogs>
<enums>Enum.Имя</enums>
<informationRegisters>InformationRegister.Имя</informationRegisters>
<accumulationRegisters>AccumulationRegister.Имя</accumulationRegisters>
<dataProcessors>DataProcessor.Имя</dataProcessors>
<commonModules>CommonModule.Имя</commonModules>
<subsystems>Subsystem.Имя</subsystems>
```

Затем F5 → `revalidate_objects` → Обновить конфигурацию БД.

### Почему это НЕ нарушает правило «не редактировать Configuration.mdo вручную»

Правило (`1c-mdo-integrity.md` / критическое правило 2.2) запрещает ручную правку, потому что она
может СОЗДАТЬ рассинхрон между составом и папками. Здесь рассинхрон **уже есть** (папка есть, записи
в составе нет), и добавление записи его **устраняет**. После правки EDT на Refresh видит согласованное
состояние (папка объекта + запись в составе совпадают), конфликта нет.

### Профилактика

При генерации `.mdo` нового объекта (не через конструктор) — **сразу** добавлять объект и в
`Configuration.mdo`, и в нужную подсистему (`<content>` подсистемы). Альтернатива без ручной правки
Configuration.mdo: создавать пустой каркас объекта в конструкторе EDT (он регистрирует в составе
автоматически), затем наполнять реквизиты/ТЧ через `.mdo` или add_metadata_attribute.

---

## 3. Профилактический чеклист при создании объекта метаданных через EDT MCP

Для агента разработчика mcp-edt - перед каждым `update_database` или запуском ИБ:

### Subsystem (новая собственная)

- [ ] `<name>` уникальное (свой уникальный префикс для расширения)
- [ ] `<includeInCommandInterface>true</includeInCommandInterface>` - **обязателен `CommandInterface.cmi` рядом**
- [ ] Все ссылки `<content>` указывают на существующие объекты конфигурации
- [ ] Объект зарегистрирован в `Configuration.mdo` (`<subsystems>Subsystem.Имя</subsystems>`)

### CommonCommand

- [ ] `<commandParameterType>` корректный (тип ссылки или Undefined для безпараметрических)
- [ ] `CommandModule.bsl` существует и содержит `Процедура ОбработкаКоманды(ПараметрКоманды, ПараметрыВыполненияКоманды)`
- [ ] Включена в подсистему через `<content>CommonCommand.Имя</content>`

### CommonForm

- [ ] `Form.form` существует и валиден (см. `1c-mdo-integrity.md` про `stringQualifiers`)
- [ ] `Module.bsl` существует (даже минимальный, иначе EDT может ругаться)
- [ ] У `.mdo` есть `<form>` ссылка на Form.form

### Adopted-объект (заимствованный)

- [ ] `<objectBelonging>Adopted</objectBelonging>` указано
- [ ] НЕ добавлять `<predefined>` блок с собственными элементами
- [ ] Реквизиты типа `DocumentRef.X` / `CatalogRef.X` и составные: `add_object_attribute` их **персистит** (main config И adopted-объект расширения; `.mdo` расширения получает `<types>CatalogRef.X</types>`). Ручная правка `.mdo` для создания реквизита не нужна. Сменить тип уже существующего реквизита на составной - `set_object_type ownerFqn=<owner>.Attribute.<имя> type="CatalogRef.A,DocumentRef.B"` (child-FQN, EDT MCP 1.43+; на старой сборке - временно правкой `.mdo`).

---

## 4. Алгоритм диагностики при ошибке `zip:///...`

При получении `RuntimeCoreException: Файл не обнаружен 'zip:///...'`:

1. **Извлечь путь из ошибки** - например `Ext/CommandInterface.xml`, `Subsystems/X/Ext/CommandInterface.xml`,
   `CommonForms/X/Ext/Form.xml` и т.п.
2. **Определить уровень** - корень `Ext/...` (конфигурация) или `Subsystems/X/Ext/...` (подсистема) или
   объектный.
3. **Найти EDT-источник** - `.cmi` / `.form` / `.mdo` рядом с соответствующим объектом.
4. **Если файл-источник отсутствует** - создать минимальный валидный.
5. **Если файл есть, но повреждён** - сравнить с эталоном (типовая конфигурация рядом).
6. **`clean_project` + `revalidate_objects`** на затронутом объекте.
7. **Повторить экспорт в ИБ.**

---

## 5. Когда обращаться к пользователю

- Если `clean_project` + создание минимального источника не помогает - возможно проблема с самой EDT (workspace .metadata).
  Тогда: попросить пользователя сделать `File → Restart` EDT и попробовать снова. Не пытаться чинить
  `.metadata` напрямую (риск потерять часть workspace-настроек).
- Если ошибка касается типового объекта (не нашего расширения) - не править. Возможна порча типовой
  конфигурации, нужен `Reset to base` со стороны пользователя.

---

## Связанные правила

- `1c-mdo-integrity.md` - целостность MDO (UUID, String length, scale, fillValue, stringQualifiers)
- `mcp-tool-priority.md` - последовательность инструментов EDT MCP
