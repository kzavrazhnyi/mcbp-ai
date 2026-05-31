# Аналіз конфігурації MCBP+ та HTTP‑сервісу `MCBP_Exchange`

> Звіт за результатами аналізу вивантаження конфігурації у `C:\PYTHON\mcbp\bas`.
> Основний акцент — **HTTP‑сервіс `MCBP_Exchange`** як інтеграційний контракт для майбутнього ШІ‑додатку (зовнішнього веб‑сервісу).
> Дата: 2026‑05‑30.

---

## 1. Резюме

**MCBP+** («Management of Cybernetic Business Processes», укр. «Управління Кібернетичними Бізнес‑Процесами») — конфігурація 1С:Підприємство 8.

| Параметр | Значення |
|---|---|
| Внутрішня назва | `ManagementCyberneticBusinessProcesses` |
| Вендор | `MCBP.PLUS` |
| Версія | `1.0.35.11` |
| Режим сумісності | `Version8_3_23` (8.3.23) |
| Режим запуску | Керований застосунок (Managed Application) |
| Варіант мови вбудованої | English (англомовні ідентифікатори) |
| Мови інтерфейсу | English, Українська, Русский, Polish, German |
| Ролі за замовчуванням | `MCBP_Basic`, `MCBP_Full` |
| Єдиний префікс об'єктів | `MCBP_` |

**Масштаб вивантаження:** 674 XML + 261 BSL‑модуль, 117 HTML (довідка), 10 PNG.

| Категорія | К‑сть | Категорія | К‑сть |
|---|---|---|---|
| Catalogs (довідники) | 95 | EventSubscriptions | 12 |
| InformationRegisters | 60 | CommonPictures | 10 |
| Enums (переліки) | 22 | ScheduledJobs | 9 |
| Roles | 16 | Documents | 8 |
| HTTPServices | **1** (`MCBP_Exchange`) | CommonModules | 8 |
| Reports | 3 | CommonForms | 8 |
| DataProcessors | 3 | SessionParameters | 8 |
| Tasks | 1 | Languages | 5 |
| ExchangePlans | 1 | CommonTemplates | 5 |
| Subsystems | 2 | Styles | 1 |

`MCBP_Exchange` — **єдина зовнішня точка входу по HTTP** для всієї конфігурації. Саме через неї зовнішній ШІ‑додаток отримуватиме дані (довідники, документи, метадані, задачі, друковані форми) та передаватиме дані назад (об'єкти, повідомлення підтримки, пакети обміну).

---

## 2. Огляд підсистем (контекст)

Конфігурація — це платформа автоматизації/інтеграції з кількома «движками»:

- **ШІ‑ядро.** Обробка `DataProcessors.MCBP_AIConnector`; довідники `MCBP_AIChats`, `MCBP_AIPrompts` (з макетами‑промптами `AIController`, `AIConsolidator`, `AIDialog`, `BAFCode`, `Service`), `MCBP_AIModelSettings`, `MCBP_AISystemRoles`; ~12 регістрів `MCBP_AI*` (черги повідомлень, кеш контексту/повідомлень, лог, архів запитів, бази знань по контактах/товарах, пам'ять). Переліки `MCBP_AI`, `MCBP_AIModelClass`, `MCBP_AISubjectRole`, `MCBP_AIMessageRecordType`.
- **BAF (Business Automation Framework).** Довідники `MCBP_EventHandlers`, `MCBP_ExecutionConditions`, `MCBP_ActionOptions`, `MCBP_ActionHandlersConditions`, `MCBP_Functions`, `MCBP_EventGroups`; 12 підписок на події (`MCBP_CatalogBeforeWrite/OnWrite`, `MCBP_DocumentPosting`, `MCBP_Task*` тощо); регламентні завдання `MCBP_ActionHandlers`, `MCBP_DeferredActions`.
- **Обмін / інтеграція.** `HTTPService.MCBP_Exchange`, `ExchangePlan.MCBP_IntegrationExchangePlan`, регістри `MCBP_DataExchange*`, `MCBP_IntegrationExchangeRegister`, `MCBP_DataConversion`; конектори **Bitrix24** (регістри `MCBP_B24Task`, `MCBP_B24Users`, `MCBP_B24UserFields`, …); довідники `MCBP_DataConversionSettings`, `MCBP_DataSources`, `MCBP_DataRecipients`, `MCBP_InformationBases`.
- **CRM‑адаптери під типові 1С.** Контрагенти/контакти/договори/організації/користувачі/товари у варіантах суфіксів: `ACC` (Бухгалтерія), `UT` (Управління торгівлею), `UTP`, `UPP`, `RT` (роздріб), `WF`. Тобто MCBP+ розрахований на роботу поверх різних типових конфігурацій.
- **E‑commerce боти.** `MCBP_eComm_Bot_ChatBots`, `…Dialogues`, `…TopicDialogues`, `…SLA`, регістр `MCBP_eComm_Bot_MessageHistory`.
- **Задачі/документообіг.** `Task.MCBP_PerformerTask`, довідники `MCBP_Documents`, `MCBP_DocumentsSections`, `MCBP_TaskStatuses`; аналітика `MCBP_AnalyticsKeys`, `MCBP_AnalyticsElements`.

**Спільні модулі** (важливо для розуміння сервісу):

| Модуль | Призначення | Рядків |
|---|---|---|
| `MCBP_Server` | Серверна бізнес‑логіка, основна | **8495** |
| `MCBP_Client` | Клієнтська логіка | 391 |
| `MCBP_ServerEvent` | Обробка подій | 237 |
| `MCBP_ServerPrivileged` | Привілейовані виклики | 220 |
| `MCBP_ServerCode` | Серіалізація даних об'єктів, ключ доступу | 445 |
| `MCBP_ServerCall` | Виклик з клієнта (`&НаСервереБезКонтекста`) | 89 |
| `MCBP_ClientCode` | Допоміжний клієнтський | 38 |
| `MCBP_SSL` | Інтеграція з БСП | 33 |

---

## 3. ★ API‑довідник `MCBP_Exchange`

Реалізація: `HTTPServices/MCBP_Exchange/Ext/Module.bsl` (497 рядків).

### 3.1. Базовий URL та налаштування

- **RootURL:** `mcbp`
- **Шаблон URL:** `/exchange/{Name}`, де `{Name}` — ім'я логічного методу.
- **Повний шлях:**
  `http(s)://<host>/<infobase>/hs/mcbp/exchange/{Name}?<query>`
  (`hs` — стандартний префікс публікації HTTP‑сервісів 1С).
- **ReuseSessions:** `AutoUse`, **SessionMaxAge:** `20` с — сервіс намагається перевикористовувати сеанси (важливо для пулу з'єднань клієнта).

### 3.2. HTTP‑методи

| HTTP | Обробник | Призначення |
|---|---|---|
| `GET` | `exchange_get` | Читання даних з бази |
| `POST` | `exchange_post` | Запис/передача даних у базу |
| `OPTIONS` | `exchange_options` | CORS preflight |

### 3.3. Автентифікація (двошарова)

1. **HTTP Basic.** Сервіс публікується з автентифікацією 1С; клієнт надсилає заголовок
   `Authorization: Basic <base64(user:password)>`. Користувач 1С повинен мати роль, що дозволяє цей сервіс (`MCBP_HTTP_Exchange`, або повну `MCBP_Full`).
2. **Внутрішній «ключ» інформаційної бази.** Для чутливих GET‑операцій (`tasks`, `document`, `objects`, `print`) код перевіряє:
   ```bsl
   If NOT MCBP_ServerCode.GetAuditString() = MCBP_ServerCode.GetInformationBaseKeyExport() Then
       Return "Key not found!";
   EndIf;
   ```
   Обидві функції (модуль `MCBP_ServerCode`, рядки 343 і 380) працюють у привілейованому режимі й формують ключ так:
   - якщо встановлено зовнішнє розширення **«MCBP Plus»** (`MCBP_PlusModule`) і воно повертає непорожнє значення — береться його значення;
   - інакше ключ виводиться з `Catalogs.MCBP_InformationBases.CurrentInformationBase` (поле `LicenseKey` / реквізити організації, напр. код ЄДРПОУ) і хешується (MD5).

   **Висновок для клієнта:** доступ до даних залежить не лише від Basic‑логіну, а й від коректно налаштованої ліцензії/поточної інфобази на боці 1С. Якщо ключ не збігається — у полі `data` повернеться рядок `"Key not found!"` (а не помилка HTTP).

### 3.4. CORS

`exchange_options` повертає:
```
Access-Control-Allow-Origin: <Origin> | *
Access-Control-Allow-Headers: Authorization,Content-type
Access-Control-Allow-Methods: GET, POST
```
Тобто браузерний клієнт підтримується; для credentials дзеркалиться `Origin`.

### 3.5. Формат відповіді

Усі відповіді — **JSON**, `Content-Type: application/json; charset=utf-8`, **HTTP‑статус завжди 200** (`ReturnResponse`).

**GET** повертає структуру:
```json
{ "request": "<name>", "success": true|false, "parameters": { ...query... }, "data": <...>, "error": "<опц.>" }
```
**POST** повертає структуру:
```json
{ "request": "<name>", "success": true|false, "answer": "<...>", "error": "<...>", "data": [ ... ] }
```

⚠️ **Модель помилок специфічна:** помилки **не** віддаються HTTP‑кодом. Ознаки збою:
- `success == false`;
- `data` (для GET) або `answer`/`error` (для POST) містить **рядок** з текстом помилки
  (`"Parameter type not found!"`, `"Key not found!"`, `"MCBP Plus not found!"`, `"Date ... format YYYYMMDD !"`).
- Для GET ознака успіху виставляється автоматично, якщо `data` — **не рядок** (`If NOT TypeOf(data) = Type("String") Then success = True`).

### 3.6. GET — методи `/exchange/{Name}`

Значення `{Name}` зводиться до нижнього регістру; значення query‑параметрів `type`/`metadata`/`number` теж зводяться до нижнього регістру (`GetQueryOption` → `Lower`).

| `{Name}` | Query‑параметри | Що повертає | Потрібен «ключ» |
|---|---|---|---|
| `mcbp` | — | health‑check: `{success:true}` | ні |
| `functions` | — | масив функцій з регістру `MCBP_StatusFunctions`; перший елемент — заголовки, далі рядки `{Number, DateExecution, Status, StatusOrder, FunctionType, Function, Version}` | ні |
| `tasks` | — | масив задач `Task.MCBP_PerformerTask`: `{Status, Description, Executed}` | **так** |
| `document` | `type` | структура‑шаблон порожнього документа (метадані + типи реквізитів) | **так** |
| `objects` | `metadata`=`document`\|`catalog`, `type`, `date`\|`begindate`+`enddate` (для документів) | `{Metadata, Type, Data:[...]}` — серіалізовані об'єкти | **так** |
| `print` | `type`, `id`, `number`, `date`, `filetype`(=`pdf`) | без `id` — список команд друку; з `id` — друкована форма (через «MCBP Plus») | **так** |
| `configuration` | `metadata`, `type` | метадані конфігурації (для `informationregisters` — виміри+ресурси як `{Name: Synonym}`) | ні |
| `integrationexchange` | `nodecode`, `documentsblockingdate` | дані вивантаження вузла плану обміну `MCBP_IntegrationExchangePlan` | **так** |
| `informationregisters` / `accumulationregistersbalance` / `executereport` / `executequery` | `type` + **тіло запиту** = фільтр | результат через «MCBP Plus» (`GetIntegrationExchangeDataExport`) | потрібен «MCBP Plus» |

`integrationexchange` шукає вузол за `ExchangePlan.MCBP_IntegrationExchangePlan.Code = nodecode` (інакше `"Node <code> not found!"`); вузол не може бути поточним (`"... is this node!"`); усередині `GetExchangePlanNode` теж перевіряється «ключ» бази.

**Деталі ключових GET‑методів:**

- **`objects`** (читання даних — найважливіше для ШІ‑додатку):
  - `metadata=catalog` → вибірка всіх елементів довідника `type`.
  - `metadata=document` → потрібна дата: `date` (один день) або `begindate`+`enddate` (період), формат `YYYYMMDD`; запит `WHERE Object.Date BETWEEN &BeginDate AND &EndDate`.
  - Кожен об'єкт серіалізується `MCBP_ServerCode.GetObjectData`: стандартні реквізити + реквізити + табличні частини; **імена полів латинізуються** (`StringLatin`), значення — через `GetAttributeStructure`. Запит виконується з `SELECT ALLOWED` (враховує RLS ролі користувача).
  - ⚠️ **Немає пагінації** — вся вибірка повертається одним масивом.

- **`document`** — повертає «каркас» документа: блок `Metadata` (по кожному реквізиту — `ТипXML (Синонім)`) і блок значень‑заготовок. Зручно для побудови форм/підказок ШІ щодо структури документа.

- **`configuration`** — інтроспекція метаданих (наразі реалізовано для регістрів відомостей: повертає виміри й ресурси з їх синонімами).

### 3.7. POST — методи `/exchange/{Name}`

Тіло читається як рядок UTF‑8 і парситься `ReadJSON`. Помилка парсингу → `answer: "Data error: ..."`.
`InformationBase` читається з query **з точним регістром** (не lower!).

| `{Name}` | Query | Тіло JSON | Дія на сервері |
|---|---|---|---|
| `tasks` | `InformationBase` (обов.) | `{ "TASKS": [ { "KEY": "...", ... } ] }` | для кожного елемента — `AddUpdateMatchingLinksExchangeExport` (реєстрація відповідностей) через «MCBP Plus» |
| `object` | `InformationBase` (обов.) | об'єкт довідника/документа | `AddUpdateMatchingLinksExchangeExport(InformationBase, JSONData, JSONString)`; у відповідь — `data:[Result]` (без `ObjectRef`) |
| `support` | `InformationBase` (обов.) | повідомлення підтримки | `MCBP_Server.AddSupportServiceMessage` → `{answer, error}` |
| `integrationexchange` | `nodecode` (обов.) | `{ "StringXML": "<xml плану обміну>" }` | завантаження змін у вузол: `ExchangePlansLoadChangeDataForNode` |

Для всіх POST з відсутнім обов'язковим параметром — `answer/data: "Parameter <name> not found!"`. Операції запису залежать від наявності «MCBP Plus».

### 3.8. Приклади запитів

Health‑check:
```bash
curl -u USER:PASS "https://host/base/hs/mcbp/exchange/mcbp"
# → {"request":"mcbp","success":true,"parameters":{},"data":[]}
```
Список елементів довідника:
```bash
curl -u USER:PASS \
  "https://host/base/hs/mcbp/exchange/objects?metadata=catalog&type=MCBP_Counterparties"
```
Документи за період:
```bash
curl -u USER:PASS \
  "https://host/base/hs/mcbp/exchange/objects?metadata=document&type=MCBP_SalesOrder&begindate=20260101&enddate=20260131"
```
Структура документа:
```bash
curl -u USER:PASS "https://host/base/hs/mcbp/exchange/document?type=MCBP_SalesOrder"
```
Передача об'єкта в базу:
```bash
curl -u USER:PASS -X POST \
  "https://host/base/hs/mcbp/exchange/object?InformationBase=MAIN" \
  -H "Content-Type: application/json" \
  -d '{ "...поля об'єкта..." }'
```

> Примітка: `type=salesorder` має спец‑обробку (`GetObjectMetadata`) — мапиться на `ЗаказПокупателя` / `ЗаказКлиента` / `MCBP_SalesOrder` залежно від базової конфігурації.

---

## 4. Серверні залежності сервісу

Сервіс — тонка оболонка; уся робота делегується спільним модулям і зовнішньому розширенню «MCBP Plus».

```
exchange_get / exchange_post (HTTPService.MCBP_Exchange)
 ├─ MCBP_Server.GetMCBP_Plus()         → Metadata.CommonModules.Find("MCBP_PlusModule") + Eval (SetSafeMode)
 ├─ MCBP_Server.GetFunctions()         → InformationRegister.MCBP_StatusFunctions
 ├─ MCBP_Server.GetConfigurationMetadata(metadata, type)
 ├─ MCBP_Server.GetExchangePlanUploadData / GetExchangePlanNode / ExchangePlansLoadChangeDataForNode
 ├─ MCBP_Server.AddSupportServiceMessage(InformationBase, JSONData, JSONString) → {answer, error}
 ├─ MCBP_ServerCode.GetAuditString() == GetInformationBaseKeyExport()   ← перевірка «ключа»
 ├─ MCBP_ServerCode.GetObjectData(meta, object)          ← серіалізація об'єкта (lat. імена полів)
 ├─ MCBP_ServerCode.GetDocumentDataStructure(meta, doc)  ← каркас документа
 └─ MCBP_Plus.*  (GetIntegrationExchangeDataExport, AddUpdateMatchingLinksExchangeExport,
                  GetPrintCommandsExport, GetSpreadsheetDocumentStructureResultExport, ...)
```

**Важливо:** «MCBP Plus» (`MCBP_PlusModule`) **відсутній** у цьому вивантаженні `bas` — це окреме розширення/постачання. Якщо його не встановлено, методи `print`, `informationregisters`, `accumulationregistersbalance`, `executereport`, `executequery`, а також POST `tasks`/`object` повернуть `"MCBP Plus not found!"` або не виконають запис. Базові читання (`objects`, `document`, `configuration`, `functions`, `tasks`) працюють без нього.

---

## 5. Рекомендації для ШІ‑додатку (веб‑сервіс‑клієнт)

1. **Перевіряйте `success` І тип `data`/`answer`.** HTTP завжди 200 — орієнтуватися на код статусу не можна. Алгоритм: `success==true` і `data` не рядок → успіх; інакше рядок у `data`/`answer`/`error` — це повідомлення про помилку.
2. **Налаштуйте «ключ» на боці 1С.** Без збігу `GetAuditString == GetInformationBaseKeyExport` усі дані‑методи віддають `"Key not found!"`. Узгодьте з адміністратором 1С `LicenseKey`/поточну інфобазу (`Catalogs.MCBP_InformationBases`).
3. **Для читання довідників/документів достатньо GET `objects` + `document`.** Це основний канал для наповнення контексту ШІ. Дати — суворо `YYYYMMDD`.
4. **Враховуйте відсутність пагінації** в `objects`: для великих довідників/періодів робіть звуження за датою (документи) або плануйте обробку великих JSON; за потреби — домовтесь про доопрацювання серверного методу.
5. **Імена полів латинізовані** (`StringLatin`) — не покладайтесь на кириличні імена реквізитів; будуйте мапінг по латинських ключах із блоку `Metadata`, який віддає `document`.
6. **Запис даних — через POST `object`** (по одному об'єкту) або `tasks`. Завжди передавайте `InformationBase` (точний регістр). Запис вимагає «MCBP Plus».
7. **CORS уже відкритий** (`*` / дзеркало Origin) — браузерний клієнт можливий; для production обмежте Origin на боці публікації/проксі.
8. **Безпека.** Basic‑автентифікація → використовуйте лише HTTPS. «Ключ» передається не клієнтом, а обчислюється сервером, тож не є секретом для клієнта, але керує доступом.
9. **Орієнтир для ШІ‑частини всередині 1С** — штатне ядро `DataProcessors.MCBP_AIConnector` (форма обробки, ~986 рядків): модель за замовчуванням `Catalogs.MCBP_AIModelSettings.openai_gpt`, є транскрибація аудіо й переклад (коди ISO‑639), доступ також гейтиться «ключем». Промпти — `Catalogs.MCBP_AIPrompts.Templates`: `AIController` («Context_Controller», протокол «Matrix 13», віддає **RAW JSON**‑об'єкт рішення), `AIDialog`, `AIConsolidator`, `BAFCode`. Якщо новий додаток має співіснувати зі штатним ШІ, узгодьте формати промптів/повідомлень (регістри `MCBP_AIMessagesQueue`, `MCBP_AIContextCache`).

---

## 6. Спостереження та технічний борг

- **Баг у `GetTasks` (Module.bsl):** при кириличній таблиці задач використовується неоголошена змінна `QueryText` замість `Query.Text`:
  ```bsl
  If MainTableName = "Задача.ЗадачаИсполнителя" Then
      QueryText = StrReplace(QueryText, ".DeletionMark", ".ПометкаУдаления"); // помилка: QueryText не визначено
  EndIf;
  ```
  Це призведе до виключення на конфігураціях з кириличними метаданими.
- **Змішування en/ru ідентифікаторів** у запитах (`Задача.ЗадачаИсполнителя`, `ЗаказПокупателя`, `КодПоЕДРПОУ`) — наслідок роботи поверх різних типових конфігурацій; ускладнює супровід.
- **Обфускований код** у `MCBP_ServerCode` (`GetObjectData`, `GetDocumentDataStructure`, `GetAuditString`, `GetInformationBaseKeyExport`) — імена змінних рандомізовані; ймовірно, захист постачання. Ускладнює аудит/відлагодження.
- **Модель помилок через тіло + статус 200** — нестандартна для REST; вимагає особливої обробки на клієнті (немає 4xx/5xx).
- **Відсутність пагінації/ліміту** в `objects` — ризик великих відповідей і таймаутів.
- **Єдиний namespace `/exchange/{Name}`** з гілкуванням `If MethodName = ...` — усе в двох великих функціях; розширення API потребує правок монолітних обробників.
- **Залежність від зовнішнього «MCBP Plus»** для половини функцій — обов'язково перевірити його наявність у цільовій базі.

---

## 7. Додаток — об'єкти за категоріями

**Спільні модулі (8):** `MCBP_Client`, `MCBP_ClientCode`, `MCBP_Server`, `MCBP_ServerCall`, `MCBP_ServerCode`, `MCBP_ServerEvent`, `MCBP_ServerPrivileged`, `MCBP_SSL`.

**Обробки (3):** `MCBP_AIConnector`, `MCBP_IntegrationRequests`, `MCBP_SupportService`.

**Звіти (3):** `MCBP_ObjectsRecordingData`, `MCBP_B24Task`, `MCBP_B24TasksTime`.

**HTTP‑сервіси (1):** `MCBP_Exchange`. **Плани обміну (1):** `MCBP_IntegrationExchangePlan`. **Задачі (1):** `MCBP_PerformerTask`.

**Ролі (16):** `MCBP_Basic`, `MCBP_Full`, `MCBP_HTTP_Exchange`, `MCBP_DataExchange`, `MCBP_DataExchangeQueue`, `MCBP_DataConversion`, `MCBP_DataRegister`, `MCBP_IntegrationExchange`, `MCBP_ArtificialIntelligence`, `MCBP_AIAssistant`, `MCBP_AdvancedAnalytics`, `MCBP_ActionMonitor`, `MCBP_CyberneticManagement`, `MCBP_InformationMessages`, `MCBP_SupportService`, `MCBP_Task`.
> Для доступу до сервісу зовнішньому користувачу 1С потрібна роль **`MCBP_HTTP_Exchange`** (або `MCBP_Full`).
> Роль `MCBP_HTTP_Exchange` надає право `Use` на методи `_get`/`_post`/`_options` сервісу,
> а з даних — лише `Read` на `Task.MCBP_PerformerTask` та довідники `MCBP_Counterparties`, `MCBP_Users`, `MCBP_Accounts`.
> Оскільки GET `objects` виконується з `SELECT ALLOWED`, під цією роллю читання обмежене переліченими об'єктами — для ширшого доступу потрібна `MCBP_Full` або розширення прав ролі.

**Документи (8):** `MCBP_ActionCard`, `MCBP_ConversionCard`, `MCBP_Operation`, `MCBP_RegistersAdjustment`(+`UT`,`RT`), `MCBP_SalesOrder`, `MCBP_SalesOrderERP`.

**Регістри відомостей, релевантні обміну/ШІ (вибірка з 60):**
`MCBP_DataExchange`, `MCBP_DataExchangeQueue`, `MCBP_DataExchangeRegistration`, `MCBP_DataExchangeSettings`, `MCBP_IntegrationExchangeRegister`, `MCBP_DataConversion`, `MCBP_DataConnectors`, `MCBP_StatusFunctions`, `MCBP_SupportServiceData`, `MCBP_SecureDataStorage`, `MCBP_AIMessagesQueue`, `MCBP_AIMessagesLog`, `MCBP_AIContextCache`, `MCBP_AIMessageCache`, `MCBP_AIRequestArchive`, `MCBP_AIContactsKnowledgeBase`, `MCBP_AIProductsKnowledgeBase`, `MCBP_B24Task`, `MCBP_B24Users`.

**Довідники (95)** — основні групи: AI (`MCBP_AIChats/AIPrompts/AIModelSettings/AISystemRoles`), CRM‑адаптери (`MCBP_Counterparties[ACC|UT|UTP|UPP|RT|WF|Segments]`, `MCBP_ContactPersons*`, `MCBP_Contracts*`, `MCBP_Organizations*`, `MCBP_Persons*`, `MCBP_Users*`, `MCBP_Products*`, `MCBP_PriceTypes*`, `MCBP_Projects*`), обмін (`MCBP_DataConversionSettings`, `MCBP_DataSources`, `MCBP_DataRecipients`, `MCBP_InformationBases`, `MCBP_DataExchangeRegistration*`), BAF (`MCBP_EventHandlers`, `MCBP_ExecutionConditions`, `MCBP_ActionOptions`, `MCBP_Functions`), боти (`MCBP_eComm_Bot_*`).

---

*Звіт згенеровано на основі статичного аналізу вивантаження `bas`. Сегменти, що залежать від розширення «MCBP Plus» (`MCBP_PlusModule`), описані за зовнішніми викликами — самого модуля у вивантаженні немає.*
