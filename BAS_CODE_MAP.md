# Карта коду `bas/` (конфігурація 1С MCBP+)

> Навігаційна карта вивантаження конфігурації для **аналізу переходів по коду**:
> хто кого викликає, де лежить кожна експортована функція (номер рядка),
> які точки входу (HTTP-сервіси) у які серверні функції переходять.
>
> **Підтримка:** після правок у `bas/CommonModules` чи `bas/HTTPServices` оновлюй
> відповідні розділи. Кожен розділ можна **перегенерувати** командами з §6 — звіряй
> числа й переліки після змін. Останнє звіряння: див. git-історію цього файлу.

---

## 1. Інвентар `bas/` за видами об'єктів

Код (BSL), що містить логіку переходів, зосереджений у `CommonModules` і `HTTPServices`.
Решта — переважно метадані + тонкі менеджер/об'єктні модулі.

| Вид | К-сть BSL | Роль |
|---|---|---|
| Catalogs | 137 | довідники (типові + `MCBP_*`); модулі переважно тонкі |
| InformationRegisters | 79 | регістри відомостей (`MCBP_DataExchange`, `MCBP_StatusFunctions`, …) |
| Documents | 14 | документи |
| **CommonModules** | **8** | **серверна/клієнтська логіка — головне джерело переходів** |
| CommonForms | 8 | спільні форми |
| Tasks | 4 | задачі (`MCBP_PerformerTask`) |
| DataProcessors | 3 | обробки |
| **HTTPServices** | **2** | **`MCBP_AI`, `MCBP_Exchange` — точки входу ззовні** |
| ExchangePlans | 2 | плани обміну |
| CommonCommands | 2 | команди |
| Reports | 1 | звіт |
| Ext, Enums, Roles, Subsystems, EventSubscriptions, ScheduledJobs, SessionParameters, Styles, Languages, CommonPictures, CommonTemplates | — | конфігурація/метадані |

---

## 2. Модулі з кодом: розмір і поверхня

| Модуль | Рядків | Export | Призначення |
|---|---:|---:|---|
| `CommonModules/MCBP_Server` | 8495 | 160 | **ядро**: події, ШІ, обмін, B24, метадані, з'єднання, задачі |
| `CommonModules/MCBP_ServerCode` | 445 | 19 | низькорівневі утиліти: шифрування, ключ бази, структури даних (обфусковані імена) |
| `CommonModules/MCBP_Client` | 391 | 13 | клієнтська логіка (форми, дерева об'єктів, конструктор запитів) |
| `CommonModules/MCBP_ServerEvent` | 237 | 15 | тонкі обгортки обробників подій → делегують у `MCBP_Server` |
| `CommonModules/MCBP_ServerPrivileged` | 220 | 6 | привілейовані операції (користувачі, налаштування сервісних подій) |
| `CommonModules/MCBP_ServerCall` | 89 | 7 | виклик сервера з клієнта (тонкі проксі) |
| `CommonModules/MCBP_ClientCode` | 38 | 3 | клієнтські утиліти (повідомлення, HTML-команди) |
| `CommonModules/MCBP_SSL` | 33 | 3 | інтеграція з БСП (рос. імена процедур) |
| `HTTPServices/MCBP_AI` | 735 | 9 | новий API `/ai/v1/...` — див. [пам'ять mcbp-ai-http-service] |
| `HTTPServices/MCBP_Exchange` | 497 | 3 | попередній API `/hs/mcbp/exchange/{Name}` |

---

## 3. Граф міжмодульних викликів

Стрілка `A → B (n)` = у модулі `A` є `n` звернень `B.<функція>`.

```
HTTPServices/MCBP_AI ───► MCBP_ServerCode (4)
                     ├──► MCBP_Server (2)        [GetMCBP_Plus]
                     └──► MCBP_Plus (2)*          *розширення поза вивантаженням

HTTPServices/MCBP_Exchange ─► MCBP_ServerCode (10)
                           ├─► MCBP_Server (10)
                           └─► MCBP_Plus (6)*

MCBP_Server ───► MCBP_Plus (65)*   ← найгустіша залежність; багато логіки в розширенні
            ├──► MCBP_ServerCode (42)
            ├──► MCBP_ServerCall (5)
            └──► MCBP_ServerPrivileged (2)

MCBP_ServerEvent ─► MCBP_Server (16)   ← події делегують у ядро
                 └► MCBP_ServerPrivileged (1)
MCBP_ServerCall ──► MCBP_Server (3), MCBP_ServerCode (1)
MCBP_ServerPrivileged ─► MCBP_Server (1)
MCBP_SSL ─► MCBP_Server (1)
MCBP_Client ─► MCBP_ClientCode (1)
MCBP_ServerCode ─► (нікого; листовий модуль-утиліта)
```

**Висновки для аналізу переходів:**
- `MCBP_ServerCode` — листовий: нічого не викликає, лише його викликають. Тут «дно» багатьох ланцюгів (ключ бази, структури даних).
- `MCBP_Plus` (зовнішнє розширення, **відсутнє у вивантаженні**) — 65+ викликів з ядра. Будь-який ланцюг, що в нього впирається, далі не простежити по `bas/`.
- Події (`MCBP_ServerEvent`) — лише тонкі обгортки; реальна логіка в `MCBP_Server`.

---

## 4. Точки входу (HTTP) → переходи

### `HTTPServices/MCBP_Exchange` — `/<base>/hs/mcbp/exchange/{Name}`
Диспетчер за `{Name}` у `exchange_get` (L2) / `exchange_post` (L130). Деталі методів — [пам'ять mcbp-exchange-http-service].

| `{Name}` | Локальна функція | Перехід далі |
|---|---|---|
| `functions` | — | `MCBP_Server.GetFunctions` (L3356) |
| `tasks` (GET) | `GetTasks` (L255) | `MCBP_ServerCode.GetAuditString`/`GetInformationBaseKeyExport` (ключ) |
| `document` | `GetDocumentStructure` (L300) | `MCBP_ServerCode.GetDocumentDataStructure` (L291) |
| `objects` | `GetObjects` (L323) | `MCBP_ServerCode.GetObjectData` (L402) |
| `configuration` | — | `MCBP_Server.GetConfigurationMetadata` (L5806) → лише `informationregisters` |
| `integrationexchange` (GET) | — | `MCBP_Server.GetExchangePlanUploadData` (L5730) |
| `print` | `GetPrintDocument` (L423) | `MCBP_Plus.*`* |
| `informationregisters`/`accumulationregistersbalance`/`executereport`/`executequery` | — | `MCBP_Plus.GetIntegrationExchangeDataExport`* |
| `object`/`tasks`/`support` (POST) | — | `MCBP_Plus.AddUpdateMatchingLinksExchangeExport`*, `MCBP_Server.AddSupportServiceMessage` (L6866) |
| `integrationexchange` (POST) | `PostExchangePlansLoadChangeDataForNode` (L477) | `MCBP_Server.GetExchangePlanNode` (L5746), `ExchangePlansLoadChangeDataForNode` (L5048) |

### `HTTPServices/MCBP_AI` — `/ai/v1/...`
Обробники (`Export`): `ai_health`, `ai_catalogs_get`, `ai_documents_get`,
`ai_document_schema_get`, `ai_objects_post`, `ai_register_balance_get`,
`ai_context_post`, `ai_metadata_get`, `ai_options`.

| Маршрут | Обробник | Перехід далі |
|---|---|---|
| `GET /ai/v1/metadata/{metadata}` | `ai_metadata_get` | лише `Metadata.*` (список об'єктів виду; `all` → усі види) |
| `GET /ai/v1/metadata/{metadata}/{type}` | `ai_metadata_get` | лише `Metadata.*` (дерево реквізитів + ТЧ/вимірів/ресурсів) |
| schema/objects | — | `MCBP_ServerCode.GetDocumentDataStructure`, `GetObjectData`, `GetInformationBaseKeyExport` |
| objects(POST)/balance | — | `MCBP_Server.GetMCBP_Plus`, `MCBP_Plus.AddUpdateMatchingLinksExchangeExport`*, `GetIntegrationExchangeDataExport`* |

> `ai_metadata_get` — суто інтроспекція метаданих (`Metadata.Catalogs/Documents/…`), без звернень до інших модулів і без створення об'єктів.

---

## 5. Індекс експортованих функцій (модуль → рядок)

> Файл-порядок = структура модуля. Для переходів: відкрий `Module.bsl` і перейди на `L<n>`.

### `MCBP_ServerCode` (445 р.) — листові утиліти
`GetMCBPPLUS` L2 · `ValueToStringXML` L7 · `StringXMLToValue` L15 · `EncryptDecryptCurrentString` L23 · `GetMaxCodeCharacterStrings` L46 · `GetCryptionKey` L60 · `GetInformationBaseKey` L79 · `CalculateHashing` L106 · `GetStringLanguageCode` L116 · `GetRecordMessage` L128 · `StringLatinCode` L174 · `GetChoiceListObjectType` L201 · `GetXMLObjectStructure` L232 · `FillDataTree` L274 · `GetDocumentDataStructure` L291 · `GetAuditString` L343 · `DecryptString` L368 · `GetInformationBaseKey`(2) L380 · `GetObjectData` L402

### `MCBP_ServerCall` (89 р.)
`IsMCBPConfiguration` L3 · `GetMCBP_Plus` L9 · `GetNStr` L15 · `IsSimple` L21 · `StringLatin` L38 · `GetAttributeStructure` L53 · `MyStrFind` L75

### `MCBP_ServerPrivileged` (220 р.)
`UserExists` L2 · `UserNameOutOfSync` L18 · `FillCurrentUser` L37 · `CheckDisableEventSubscriptions` L93 · `GetServiceEventsSettings` L137 · `SaveServiceEventsLog` L207

### `MCBP_ServerEvent` (237 р.) — обгортки подій → `MCBP_Server`
`MCBP_DocumentBeforeWriteBeforeWrite` L3 · `MCBP_CatalogBeforeWriteBeforeWrite` L17 · `MCBP_TaskBeforeWriteBeforeWrite` L31 · `MCBP_InformationRegisterBeforeWriteBeforeWrite` L45 · `MCBP_InformationRegisterWriteOnWrite` L59 · `MCBP_CatalogOnWriteOnWrite` L73 · `MCBP_DocumentOnWriteOnWrite` L87 · `MCBP_TaskOnWriteOnWrite` L105 · `MCBP_DocumentPostingPosting` L119 · `MCBP_TaskExecutorBeforeWriteBeforeWrite` L137 · `MCBP_TaskExecutorOnWriteOnWrite` L151 · `MCBP_eComm_Bot_MessageHistoryBeforeWrite` L166 · `MCBP_ActionHandlers` L180 · `CheckDisableEventSubscriptions` L186 · `GetMetadataNameMap` L216

### `MCBP_Client` (391 р.)
`CheckObjectType` L3 · `GetObjectTreeDescription` L21 · `GenerateRequestTextForConfigurator` L44 · `GetCurrentFormName` L98 · `MetadataCommonModule` L140 · `GetMetadataName` L154 · `IsSimple` L174 · `CheckFormProperty` L189 · `GetExchangeDataStructureList` L202 · `GetFileName` L239 · `GetValueDataStructureItem` L256 · `ChangeObjectTemplate` L285 · `QueryWizardOpenGetText` L356

### `MCBP_ClientCode` (38 р.)
`SendUserMessage` L3 · `ExecuteHTMLCommand` L11 · `FinishChangeFont` L19

### `MCBP_SSL` (33 р.)
`ПриДобавленииПодсистемы` L2 · `ПриОпределенииРежимаОбновленияДанных` L16 · `AddDataRefDescription` L22

### `MCBP_Server` (8495 р., 160 export) — тематичні групи

**Версія / метадані / прапорці**
`GetMCBPVersion` L3 · `GetMCBP_Plus` L9 · `MetadataCommonModule` L15 · `MetadataDataName` L28 · `IsMCBPConfiguration` L1302 · `isNumber` L1308 · `GetNStr` L1532

**Обробники подій / BAF (умови, дії, відкладені)**
`MCBP_DeferredActions` L51 · `MCBP_DataRegisterProcessing` L119 · `MCBP_InformationMessagesProcessing` L199 · `MCBP_DocumentBeforeWriteBeforeWrite` L254 · `MCBP_CatalogBeforeWriteBeforeWrite` L269 · `MCBP_TaskBeforeWriteBeforeWrite` L284 · `MCBP_InformationRegisterBeforeWriteBeforeWrite` L308 · `MCBP_InformationRegisterWriteOnWrite` L377 · `MCBP_CatalogOnWriteOnWrite` L383 · `MCBP_DocumentOnWriteOnWrite` L389 · `MCBP_TaskOnWriteOnWrite` L410 · `MCBP_DocumentPostingPosting` L416 · `MCBP_TaskExecutorBeforeWriteBeforeWrite` L531 · `MCBP_TaskExecutorOnWriteOnWrite` L550 · `MCBP_ActionHandlers` L564 · `MCBP_eComm_Bot_MessageHistoryBeforeWrite` L661 · `ActionHandlers` L845 · `CheckActionHandlersConditions` L889 · `CheckConditionInBuiltLanguage` L3775 · `ActionOptionsInBuiltLanguage` L3830 · `ExecuteConditionExpression` L5514 · `GetActionHandlersResults` L6339

**ШІ (черга, кеш, моделі, переклади, транскрипція, база знань)**
`MCBP_AIBusinessMessagesQueueProcessing` L684 · `MCBP_AIMessageCacheProcessingSummary` L693 · `AddAIMessageCache` L702 · `AISendModelRequestExecuteJobs` L1955 · `TranscribeAudioOpenAIAdvancedExecuteJobs` L1967 · `AISendModelRequest` L1978 · `AISendRequest` L1989 · `AIMessageCacheExecuteProcessingSummary` L2266 · `AIBusinessMessagesQueueProcessing` L2327 · `AIKnowledgeBaseAnswerStructureProcess` L2544 · `AIBusinessMessagesQueueAnswerStructure` L2709 · `AIKnowledgeBaseAnswerStructureAddComment` L2754 · `AICurrentMessageProcessing` L2825 · `AIChatUsersReplacement` L2848 · `SetMessageHistoryAIState` L2957 · `AIGetUsage` L3125 · `GetAIChat` L3147 · `AddAIKnowledgeBaseContactsMemory` L3197 · `GetAIParameters` L4455 · `GetModelParameters` L4495 · `GetAITranslations` L4585 · `AddAIRequestArchive` L4729 · `FindAITranslations` L4777 · `ConnectAIAssistant` L5201 · `ClickAIAssistant` L5210 · `GetAIFormSettings` L5221 · `TranscribeAudioOpenAIAdvanced` L6743 · `GetTranscribeAudioFile` L5560 · `AddAIMessagesLog` L3726

**Контакти / паспорти / матриця (CRM-шар ШІ)**
`SetBusinessContacts` L2860 · `GetContactPassport` L2889 · `GetProductsPassport` L2924 · `GetBusinessContacts` L2983 · `GetMatrixStructure` L3010 · `GetContactStructure` L3071 · `GetContactsInformation` L3742

**Обмін даними / плани обміну / конвертація**
`MCBP_DataExchange` L77 · `MCBP_IntegrationExchange` L86 · `MCBP_UpdateExchangeObjects` L92 · `ReadExchangeData` L1927 · `ExchangeDataConversion` L3559 · `RecordSetDataExchangeDataStructure` L3674 · `ExchangePlansUploadDataChangesForNode` L4824 · `ExchangePlansLoadChangeDataForNode` L5048 · `FindAddChangeDataConversion` L5390 · `GetExchangeDataStructure` L5477 · `IntegrationExchangePlans` L5655 · `GetExchangePlanUploadData` L5730 · `GetExchangePlanNode` L5746 · `GetIntegrationExchangePlan` L5785 · `GetDataExchangeObject` L5907 · `GetDataExchangeMetadataType` L5992 · `GetDataExchangeConversionObject` L6058 · `ExchangePlansFillRecordStructure` L6260 · `GetParametersStructureIntegrationExchange` L6391

**Метадані / структури об'єктів / реквізити**
`GetAttributesTypeStructure` L1814 · `GetInformationRegisterStructure` L5181 · `GetObjectDescriptions` L5257 · `GetObjectStructure` L5299 · `GetMetadataEmptyRef` L5327 · `FindAddChangeDataConversion` L5390 · `GetMetadataObjectsFromMetadata` L5443 · `GetConfigurationMetadata` L5806 · `GetNewObjectRef` L5831 · `GetStandardAttributeMap` L5974 · `GetMetadataUsersCatalogEmptyRef` L1104 · `GetValueTableStructure` L3914 · `GetJSONObjectDataStructure` L6836 · `GetStringXML` L6693 · `AddTreeDataStructure` L6637 · `AddTreeArray` L6670 · `GetRegistersName` L6621 · `WriteDataRegister` L6461 · `InformationRegisterQueryIsEmpty` L1495 · `GetInformationRecordKey` L1908 · `GetParametersStringBalance` L6371 · `ConnectionRequestGetResponseWriteBalance` L6428 · `CheckExistsRef` L6242 · `FindObjectSelectedValue` L6308

**З'єднання / HTTP / зовнішні бази**
`GetInformationBaseConnection` L3431 · `GetHTTPConnection` L3455 · `CheckConnectionGetResponseData` L3467 · `ConnectionRequestGetResponse` L3495 · `GetDataConnector` L3938 · `GetInformationBaseConnectionService` L5535

**Bitrix24**
`B24GetUsers` L3970 · `B24WebHookReadJSON` L3996 · `B24AddTask` L4010 · `B24GetTaskStructure` L4180 · `B24AddTasksTime` L4206 · `GetB24TasksTimeUsers` L4319 · `GeB24tTasksUsers` L4356 · `B24TaskTime` L4438

**Задачі / функції / статуси**
`MCBP_InformationMessagesProcessing` L199 · `RecordEventTask` L965 · `ReturnStatusTasks` L1364 · `GetTaskExecutor` L1425 · `GetTaskMetadataFormName` L1078 · `GetFunctions` L3356 · `WriteNewTask` L5501 · `GetConfiguringObjectEvents` L1200

**Повідомлення / email / підтримка / користувачі / налаштування**
`GetCurrentUser` L939 · `GetFullRoleTrue` L951 · `MailLogon` L991 · `GetGeneralSettings` L1026 · `GetUserMessageDeliveryPeriods` L1056 · `SendUserMessage` L1324 · `GetErrorDescription` L1348 · `GetInformationMessages` L1407 · `GetInformationMessagesSettingsForParent` L1458 · `ReturnUserMessageDeliveryChannels` L1495 · `SendMessageMessageDeliveryChannels` L3237 · `GetInformationMessageReplaceChar` L3894 · `SendEmailMessage` L6155 · `AddSupportServiceMessage` L6866 · `GetValueStorageGeneralSettings` L5359 · `CheckAdministrationRight` L41 · `SetEmptyClipboard` L1016

**Шифрування / безпека / службовий лог**
`DecryptString` L3263 · `GetWriteSecureDataStorage` L3330 · `CreatePassword` L5649 · `SaveServiceEventsLog` L5102 · `CheckServiceLog` L5110

**Мови / шаблони / форми / інше**
`GetLayoutInLanguageIB` L1157 · `InfobaseLanguageCode` L1170 · `GetTableFromTemplate` L1185 · `SetFormDesign` L1254 · `EnableHTMLEditModeAtServer` L1384 · `GetChoiceListObjectTree` L1550 · `CheckUniquenessCatalogName` L1788 · `GetDataTableFromTemplate` L4544 · `GetMapFromTemplateISO639LanguageCodes` L5139 · `GetFileName` L5632 · `GetAIFormSettings` L5221

> Групи тематичні (приблизні). Авторитетне джерело — файл-порядок; перегенеруй §6.

---

## 6. Команди підтримки (перегенерація розділів)

Запускати з `C:\PYTHON\mcbp\bas` (bash). Звіряй вивід із розділами вище.

```bash
# §1 інвентар за видами
find . -name "*.bsl" | sed -E 's|^\./([^/]+)/.*|\1|' | sort | uniq -c | sort -rn

# §2 розмір + к-сть export по модулях з кодом
for f in CommonModules/*/Ext/Module.bsl HTTPServices/*/Ext/Module.bsl; do \
  n=$(echo "$f"|sed -E 's|.*/(MCBP_[^/]+)/Ext.*|\1|'); l=$(wc -l <"$f"); \
  e=$(grep -cE '^\s*(Function|Procedure)\s+\w+.*Export' "$f"); echo "$l $e $n"; done | sort -rn

# §3 граф викликів (для кожного модуля — кого викликає)
for f in CommonModules/*/Ext/Module.bsl HTTPServices/*/Ext/Module.bsl; do \
  c=$(echo "$f"|sed -E 's|.*/(MCBP_[^/]+)/Ext.*|\1|'); echo "--- $c:"; \
  grep -oE 'MCBP_(Server|ServerCode|ServerEvent|ServerPrivileged|ServerCall|Client|ClientCode|SSL|Plus)\.' "$f" \
  | sed 's/\.$//' | sort | uniq -c | sort -rn; done

# §5 індекс експортів модуля (приклад для MCBP_Server) з номерами рядків
grep -nE '^\s*(Function|Procedure)\s+\w+.*Export' "CommonModules/MCBP_Server/Ext/Module.bsl" \
  | sed -E 's/\s*Export.*//; s/\(.*$/()/; s/^([0-9]+):\s*/L\1\t/'
```

---

## 7. Споріднені документи

- `ANALYSIS_REPORT.md` — аналіз MCBP+ та API-довідник інтеграції.
- `BACKEND_TECHNICAL.md` — backend `mcbp-ai`, що споживає ці HTTP-сервіси.
- Пам'ять проєкту: `mcbp-ai-http-service`, `mcbp-exchange-http-service`, `mcbp-project`.

> **`MCBP_Plus`** — зовнішнє розширення, **відсутнє у вивантаженні**. Усі переходи
> `… → MCBP_Plus.*` по `bas/` далі не простежуються (логіка поза цим репозиторієм).
