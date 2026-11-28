# HexaVeil — CODEBASE INDEX

> Реестр контрактов: маршруты, схемы, API-клиенты, сторы, навигация.
> Источник истины — код на диске. Сверено: 2026-11-21.
> **Правило:** при любом изменении сигнатуры этот файл обновляется в том же коммите (см. `AGENTS.md` → DEFINITION OF DONE).

## Обозначения

- `W<D>` = `{"success": true, "data": <D>}` — стандартный конверт.
- `ERR` = `{"success": false, "error": str, "code": str}` (см. `core/errors.py:api_error`).
- `AUTH` = обязательный `Authorization: Bearer <JWT>` (`api/deps.py:get_current_admin`).
- `P` = `Promise<any>` (фронтенд без generic).
- ⚠ = отклонение от инварианта `{success, data, error}` — форма ответа другая (указана явно).

## Критично: префикс API

`web/backend/main.py` монтирует роутеры с `prefix="/api"`. **Префикса `/api/v1` в коде нет.**
`redirect_slashes=False` → пути с пустой частью (`""`) работают без завершающего слэша.
Ни один эндпоинт не объявляет `response_model` (0 совпадений). Все ответы — `dict` / `JSONResponse` / `FileResponse` / `StreamingResponse`.

---

# 1. Backend API Endpoints (FastAPI)

## 1.1 App-level (`main.py`)

| | |
|---|---|
| `GET /api/health` | → `{"status","service","version","database"}` (`HealthResponse`) |
| `GET /` | → `{"service","version","docs"}` |
| `GET /api/docs` | Swagger UI, только при `APP_DEBUG=true` |
| `GET /api/redoc` | ReDoc, только при `APP_DEBUG=true` |
| `GET /api/openapi.json` | OpenAPI, только при `APP_DEBUG=true` |

Старт (`lifespan`): `integrations.bootstrap` → `ensure_configured_async()` (Bedolaga) и
`bot_db.ensure_config()` — каждый в своём `try/except`, затем сводный лог `Интеграции: ... bootstrap=...`.

## 1.2 `api/v1/auth.py` — tags `auth`

```
POST /api/auth/login            req: {login, password}                       -> ⚠ {"success":true,"token":str,"user":{id,login,email,role}}
GET  /api/auth/me               req: AUTH                                    -> ⚠ {"success":true,"user":{id,login,email,role}}
POST /api/auth/change-password  req: AUTH + {current_password,new_password}  -> ⚠ {"success":true}
ERR: api_error(400|401|429) -> ERR
```

## 1.3 `api/v1/dashboard.py` — tags `dashboard`

```
GET /api/dashboard/stats  req: AUTH -> ⚠ {"success":true,"stats":DashboardStats}
```

## 1.4 `api/v1/posts.py` — tags `posts`

```
GET    /api/posts              req: AUTH + q{page=1,per_page=20,sort=created_at,dir=DESC,search=""} -> ⚠ {success,data[],total,page,per_page}
GET    /api/posts/{post_id}    req: AUTH + path int                                            -> W<PostResponse> (поля — §2)
POST   /api/posts              req: AUTH + json{title,slug,content,excerpt,category_id,status,image,seo_title,seo_description,canonical,featured,comments_enabled,publish_date,tags[]} -> W<{id}> (201)
POST   /api/posts/{post_id}    req: AUTH + path int + json(partial same)                        -> ⚠ {"success":true}
DELETE /api/posts/{post_id}    req: AUTH + path int                                            -> ⚠ {"success":true}
```
Тело читается вручную через `json_body(request)`; Pydantic-схемы для входа не применяются.

## 1.5 `api/v1/categories.py` — tags `categories`

```
GET    /api/categories           req: AUTH                       -> W<CategoryResponse[]>
POST   /api/categories           req: AUTH + {name,slug,description} -> W<{id}> (201)
POST   /api/categories/{cat_id}  req: AUTH + path int + same      -> ⚠ {"success":true}
DELETE /api/categories/{cat_id}  req: AUTH + path int             -> ⚠ {"success":true}
```
⚠ `GET /api/categories/{id}` отсутствует (фронтенд `categoriesApi.get` вызывает несуществующий путь).

## 1.6 `api/v1/pages.py` — tags `pages`

```
GET    /api/pages              req: AUTH                                        -> W<PageResponse[]>
GET    /api/pages/{page_id}    req: AUTH + path int                             -> W<PageResponse>
POST   /api/pages              req: AUTH + {title,slug,content,meta_description,status} -> W<{id}> (201)
POST   /api/pages/{page_id}    req: AUTH + path int + same                      -> ⚠ {"success":true}
DELETE /api/pages/{page_id}    req: AUTH + path int                             -> ⚠ {"success":true}
```

## 1.7 `api/v1/users.py` — tags `users`

```
GET    /api/users/names        req: AUTH -> W<[{id,username,display_name}]>
GET    /api/users             req: AUTH -> W<UserResponse[]>
GET    /api/users/{user_id}   req: AUTH + path int -> W<UserResponse> (поле password вырезается)
POST   /api/users             req: AUTH + {login,password,email,role,display_name,status,avatar_url,bio,phone,telegram,website,location} -> W<{id}> (201)
POST   /api/users/avatar      req: AUTH + multipart file:UploadFile|None -> W<{url}>
POST   /api/users/{user_id}   req: AUTH + path int + {login,email,role,display_name,status,password,avatar_url,bio,phone,telegram,website,location} -> ⚠ {"success":true}
DELETE /api/users/{user_id}   req: AUTH + path int -> ⚠ {"success":true}
```

## 1.8 `api/v1/logs.py` — tags `logs`

```
GET  /api/logs         req: AUTH + q{level="",category="",categories="csv",channel="",source="",q="",days=0,page=1,per_page=50} -> ⚠ {success,data[],total,page,per_page}
POST /api/logs/clear   req: AUTH + {channel?,category?,categories[]?} -> ⚠ {"success":true,"deleted":int}
```

## 1.9 `api/v1/widgets.py` — tags `widgets`

```
GET    /api/widgets              req: AUTH -> W<WidgetResponse[]>
GET    /api/widgets/{widget_id}  req: AUTH -> W<WidgetResponse>
POST   /api/widgets              req: AUTH + {area,title,content,sort_order} -> W<{id}> (201)
POST   /api/widgets/{widget_id}  req: AUTH + path int + same -> ⚠ {"success":true}
DELETE /api/widgets/{widget_id}  req: AUTH -> ⚠ {"success":true}
```

## 1.10 `api/v1/menus.py` — tags `menus`

```
GET    /api/menus            req: AUTH -> W<MenuResponse[]>
GET    /api/menus/{menu_id}  req: AUTH -> W<MenuResponse>
POST   /api/menus            req: AUTH + {name,url,location} -> W<{id}> (201)
POST   /api/menus/{menu_id}  req: AUTH + path int + same -> ⚠ {"success":true}
DELETE /api/menus/{menu_id}  req: AUTH -> ⚠ {"success":true}
```

## 1.11 `api/v1/themes.py` — tags `themes`

```
GET  /api/themes           req: AUTH -> W<[{value,label}]>
GET  /api/themes/settings  req: AUTH -> W<{theme,label,options,groups}>
POST /api/themes/settings  req: AUTH + flat dict<str,str> -> ⚠ {"success":true,"saved":[keys]}
```

## 1.12 `api/v1/settings.py` — tags `settings`

```
GET    /api/settings        req: AUTH -> ⚠ {success,data{key:str},items[RegistryItem],categories{cat:[RegistryItem]}}
POST   /api/settings        req: AUTH + {key: value} (фильтр ALLOWED_KEYS) -> ⚠ {"success":true,"saved":int,"runtime":{...}}
PUT    /api/settings/{key}  req: AUTH + path str + {value} -> W<RegistryItem> + "runtime"
DELETE /api/settings/{key}  req: AUTH -> W<RegistryItem> | ⚠ {"success":true,"runtime":{...}}
POST   /api/settings/integrations/proxy/test
       req: AUTH + draft{proxy_url?,proxy_no_proxy?,test_url?}
       -> W<{ok,status,message,egress_ip,http_status,elapsed_ms,test_url,proxy{mode,url,applied}}>
POST   /api/settings/integrations/{id}/test
       id ∈ {bedolaga,support,bot_db,platega,yookassa}
       req: AUTH + draft{proxy_mode?,proxy_url?,proxy_no_proxy?}
       -> W<{id,ok,status,message,elapsed_ms,egress_ip,proxy{mode,effective,url,applied,no_proxy},details}>
# runtime: {bedolaga: applied|skipped|error, support: reloaded|disabled|error,
#          bot_db: applied|skipped|error, warnings[]}; ошибка runtime не отменяет сохранение.
# Успешный тест bedolaga/bot_db: инвалидация снимка аналитики; для bot_db — ещё bot_db.refresh_config(db)
#          (сброс circuit breaker и перечитывание конфига), всё best-effort с warning.
# Неудачная проверка = HTTP 200 + data.ok=false; неизвестный id -> 404; невалидный ввод -> 400;
# bot_db + любое proxy-поле -> 400 (TCP, HTTP-прокси не применим).
```

## 1.13 `api/v1/notifications.py` — tags `notifications` (заглушки)

```
GET  /api/notifications/unread-count  req: AUTH -> ⚠ {"count":0}
GET  /api/notifications               req: AUTH -> ⚠ {"items":[],"data":[],"total":0,"page":1,"per_page":8}
POST /api/notifications/mark-read     req: AUTH (тело не читается) -> ⚠ {"success":true}
```
⚠ Остальные методы фронтенда (`DELETE /api/notifications/{id}`, `/api/notification-channels`, `/api/smtp-config`, `/api/alert-rules`, `/api/alert-logs`, `/api/alert-templates`) в бэкенде **не реализованы**.

## 1.14 `api/v1/media.py` — tags `media`

```
GET  /api/media         req: AUTH -> W<[{path,url,name,size,modified}]>
POST /api/media/upload  req: AUTH + multipart(file|image|upload) -> W<{path,url,name}>
POST /api/media/delete  req: AUTH + {path} -> ⚠ {"success":true} (всегда)
```

## 1.15 `api/v1/public.py` — tags `public` (без AUTH)

```
GET /api/public/branding -> W<{site_name,admin_title,browser_title,title_separator,favicon_url}>
```

## 1.16 `api/v1/preferences.py` — mount `/admin/settings` (⚠ не `/api`)

```
GET  /admin/settings/preferences           req: AUTH -> ⚠ {"ok":true,"data":<panel_ui_state JSON>}
POST /admin/settings/save-all-preferences  req: AUTH + произвольный JSON -> ⚠ {"ok":true}
POST /admin/settings/save-preference       req: AUTH + {key,value}; whitelist: theme,mode,density,radius,fontSize,use_react_admin -> ⚠ {"ok":true}
```

## 1.17 `api/v1/diagnostics.py` — mount `/admin/diagnostics/api`

```
GET  /admin/diagnostics/api/data     req: AUTH -> ⚠ {success:true,collected_at,nodes[],summary{total,reachable,unreachable,problems,avgLoad},is_collecting}
POST /admin/diagnostics/api/collect  req: AUTH -> ⚠ {success:true,message}; 409 ERR(ALREADY_EXISTS); 404 ERR(NOT_FOUND); 500 ERR(INTERNAL_ERROR)
```

## 1.18 `api/v1/finance.py` — mount `/admin/finance/api`

```
GET  /admin/finance/api/data            req: AUTH + q{page=1,per_page=25,sort=date,dir=desc,month,since,until,type,category,participant,q}
                                        -> ⚠ БЕЗ success: {summary,averages,chart{daily,weekly,monthly,yearly},categories[],transactions[],pagination,settings,all_months,all_categories,all_participants,anomalies}; 500 -> {"error":str}
POST /admin/finance/api/add             req: AUTH + {date,type,category,participant,amount,description} -> ⚠ {"success":true,"id":int}
POST /admin/finance/api/edit            req: AUTH + {id,date,type,category,participant,amount,description} -> ⚠ {"success":true}
POST /admin/finance/api/delete          req: AUTH + {id} -> ⚠ {"success":true}
POST /admin/finance/api/delete-bulk     req: AUTH + {ids[]} (<=1000) -> ⚠ {"success":true,"deleted":int}
POST /admin/finance/api/bulk/type        req: AUTH + {ids[],type:income|expense} -> ⚠ {"success":true,"updated":int}
POST /admin/finance/api/bulk/category    req: AUTH + {ids[],category} -> ⚠ {"success":true,"updated":int}
POST /admin/finance/api/bulk/participant req: AUTH + {ids[],participant} -> ⚠ {"success":true,"updated":int}
POST /admin/finance/api/bulk/description req: AUTH + {ids[],description} -> ⚠ {"success":true,"updated":int}
GET  /admin/finance/api/export/csv       req: AUTH + те же фильтры -> CSV (text/csv; BOM; ';'; header date;type;category;participant;amount;description;record_id)
POST /admin/finance/api/export/selected  req: AUTH + {ids[]} -> CSV (finance_selected_*.csv)
POST /admin/finance/api/import           req: AUTH + multipart file -> ⚠ {"success":true,"imported","skipped","errors":[]}
GET  /admin/finance/api/settings         req: AUTH -> ⚠ raw dict fin_settings (без конверта)
POST /admin/finance/api/settings         req: AUTH + subset(currency,decimals,auto_refresh,avg_period,avg_exclude_*,quick_*,platega_*,yookassa_*) -> ⚠ {"success":true}
```

## 1.19 `api/v1/finance_payments.py` — mount `/admin/finance/api`

```
POST /admin/finance/api/platega/preview      req: AUTH + {merchant_id?,secret?,days_back?=150 (1..730)} -> ⚠ {"success":true,"transactions":[{record_id,date,type,participant,category,amount,gross,description,status}]}
POST /admin/finance/api/platega/import       req: AUTH + {transactions:[{<preview-row>, include, record_id}]} -> ⚠ {"success":true,"added","skipped"}
POST /admin/finance/api/platega/sync         req: AUTH -> ⚠ {success,added,skipped,new[,skipped_lock]}
GET  /admin/finance/api/platega/cron-sync    req: НЕТ AUTH; q{token} -> ⚠ {"success":true,"added","skipped","new","cron":true}; 403 {"success":false,"error":"forbidden"}
GET  /admin/finance/api/platega/settings     req: AUTH -> ⚠ raw {merchant_id,secret:"***"+last4,secret_raw,days_back,auto_sync,last_sync,last_sync_ok,last_error}
POST /admin/finance/api/platega/settings     req: AUTH + {merchant_id?,secret?,days_back?,auto_sync?} -> ⚠ {"success":true}
POST /admin/finance/api/yookassa/preview     req: AUTH + {shop_id?,secret?,days_back?=30 (1..730)} -> ⚠ {"success":true,"transactions":[{record_id,date,type,participant,category,amount,gross,description,status,method,method_label,commission_pct}]}
POST /admin/finance/api/yookassa/import      req: AUTH + {transactions:[{<preview-row>, include}]} -> ⚠ {"success":true,"added","skipped"}
POST /admin/finance/api/yookassa/sync        req: AUTH -> ⚠ {success,added,skipped,new[,skipped_lock]}
GET  /admin/finance/api/yookassa/cron-sync   req: НЕТ AUTH; q{token} -> ⚠ {"success":true,"added","skipped","new","cron":true}
GET  /admin/finance/api/yookassa/settings    req: AUTH -> ⚠ raw {shop_id,secret,secret_raw,days_back,auto_sync,commissions{bank_card,sbp,yoo_money,sberbank,tinkoff_bank,mobile,cash,qiwi},last_sync,last_sync_ok,last_error}
POST /admin/finance/api/yookassa/settings    req: AUTH + {shop_id?,secret?,days_back?,auto_sync?,commissions{}} -> ⚠ {"success":true}
GET  /admin/finance/api/sync/history         req: AUTH + q{provider:platega|yookassa (required),limit=20 (1..100)} -> W<[{id,created_at,level,channel,message,category,source,context}]>
GET  /admin/finance/api/sync/status          req: AUTH -> ⚠ {"success":true,"providers":[{provider,configured,auto_sync,interval,last_sync,last_sync_ok,last_error,next_run,lock_active}]}
```

## 1.20 `api/v1/bedolaga/dashboard.py` — prefix `/api/bedolaga`

```
GET /api/bedolaga/overview      req: AUTH -> ⚠ upstream passthrough; ТОЛЬКО subscriptions.active
                                перезаписывается из /stats/full -> subscriptions.paid_subscriptions
                                (активные ПЛАТНЫЕ, триалы исключены; кэш 60с, negative 30с);
                                subscriptions.expired НЕ подменяется (значение бота); ошибка /stats/full -> ответ бота как есть
GET /api/bedolaga/full          req: AUTH -> ⚠ upstream passthrough
GET /api/bedolaga/health        req: AUTH -> ⚠ upstream passthrough
GET /api/bedolaga/capabilities  req: AUTH -> ⚠ {"activity":bool} (кэш 60с)
GET /api/bedolaga/maintenance   req: AUTH -> ⚠ upstream passthrough
GET /api/bedolaga/status        req: AUTH -> ⚠ {"configured":bool}  # ensure_configured_async(): реестр → ENV-fallback;
                                # hard-off (bedolaga_enabled=0) приоритетнее ENV; при пустом ENV читает Настройки → Интеграции
GET /api/bedolaga/tariffs       req: AUTH -> ⚠ {"items":[<tariff row, см. §2A>],"total":int,"status":str,"error":str|null}
                                # status ∈ disabled|ok|error|timeout (bot_db.get_tariffs_result); error — причина
                                # status="ok" + items=[] — валидный пустой каталог, прочие статусы — БД недоступна
                                # каталог из read-only БД бота, НЕ источник аналитики: цены/аналитика — §1.27
```

## 1.21 `api/v1/bedolaga/customers.py` — prefix `/api/bedolaga/customers`

```
GET   /api/bedolaga/customers                        req: AUTH + q{limit=20 (1..200),offset=0,status,search,promo_group_id,subscription_status,tariff_id,tariff_missing=false,sort,order} -> ⚠ {"items":[],"total":int} | upstream
                                                     # локально: tariff_id / tariff_missing / sort=tariff (нормализованное имя, пустые в конце)
                                                     # в каждый item добавлены tariff_id, tariff_name, tariff_missing (из subscription / subscriptions[])
GET   /api/bedolaga/customers/transactions           req: AUTH + q{limit=20 (1..100),offset,user_id,transaction_type,payment_method,is_completed,date_from,date_to} -> ⚠ upstream
GET   /api/bedolaga/customers/events                 req: AUTH + q{limit=20 (1..200),offset,event_type[]} -> ⚠ upstream
GET   /api/bedolaga/customers/subscriptions/list     req: AUTH + q{limit=20 (1..100),offset,status,user_id} -> ⚠ upstream
GET   /api/bedolaga/customers/subscriptions/{sub_id} req: AUTH -> ⚠ upstream
POST  /api/bedolaga/customers/subscriptions/{sub_id}/extend       req: AUTH + SubscriptionExtendRequest -> ⚠ upstream
POST  /api/bedolaga/customers/subscriptions/{sub_id}/traffic      req: AUTH + TrafficAddRequest -> ⚠ upstream
POST  /api/bedolaga/customers/subscriptions/{sub_id}/devices      req: AUTH + DevicesAddRequest -> ⚠ upstream
POST  /api/bedolaga/customers/subscriptions/{sub_id}/reset-devices req: AUTH -> 501 {"success":false,"error":str}
GET   /api/bedolaga/customers/by-telegram/{telegram_id} req: AUTH -> ⚠ upstream
GET   /api/bedolaga/customers/{user_id}              req: AUTH -> ⚠ upstream + нормализованные tariff_id/tariff_name/tariff_missing
PATCH /api/bedolaga/customers/{user_id}              req: AUTH + UserUpdateRequest -> ⚠ upstream
POST  /api/bedolaga/customers/{user_id}/balance      req: AUTH + BalanceModifyRequest -> ⚠ upstream
POST  /api/bedolaga/customers/{user_id}/subscription req: AUTH + SubscriptionCreateRequest -> ⚠ upstream
DELETE /api/bedolaga/customers/{user_id}/subscription req: AUTH -> ⚠ upstream
GET   /api/bedolaga/customers/{user_id}/activity     req: AUTH + q{limit=50 (1..200),offset,types="csv"} -> ⚠ {**, "available":true} | {"items":[],"total":0,"limit","offset","available":false}
```

## 1.22 `api/v1/bedolaga/promo.py` — prefix `/api/bedolaga/promo`

```
GET    /api/bedolaga/promo               req: AUTH + q{limit=20 (1..100),offset,is_active,search} -> ⚠ upstream
GET    /api/bedolaga/promo/{promo_id}    req: AUTH -> ⚠ upstream
GET    /api/bedolaga/promo/{promo_id}/stats req: AUTH -> ⚠ upstream
POST   /api/bedolaga/promo               req: AUTH + dict (без схемы) -> ⚠ upstream
PATCH  /api/bedolaga/promo/{promo_id}    req: AUTH + dict -> ⚠ upstream
DELETE /api/bedolaga/promo/{promo_id}    req: AUTH -> ⚠ upstream
```

## 1.23 `api/v1/bedolaga/marketing.py` — prefix `/api/bedolaga/marketing`

```
GET    /api/bedolaga/marketing/campaigns                 req: AUTH + q{limit=20 (1..100),offset,is_active,search} -> ⚠ upstream
POST   /api/bedolaga/marketing/campaigns                 req: AUTH + dict -> ⚠ upstream
PATCH  /api/bedolaga/marketing/campaigns/{campaign_id}   req: AUTH + dict -> ⚠ upstream
DELETE /api/bedolaga/marketing/campaigns/{campaign_id}   req: AUTH -> ⚠ upstream
GET    /api/bedolaga/marketing/broadcasts                req: AUTH + q{limit=20 (1..100),offset,status} -> ⚠ upstream
POST   /api/bedolaga/marketing/broadcasts                req: AUTH + dict -> ⚠ upstream
POST   /api/bedolaga/marketing/broadcasts/{broadcast_id}/stop req: AUTH -> ⚠ upstream
GET    /api/bedolaga/marketing/partners                  req: AUTH + q{limit=20 (1..100),offset,search} -> ⚠ upstream
```

## 1.24 `api/v1/bedolaga/referrals.py` — prefix `/api/bedolaga/referrals`

```
GET /api/bedolaga/referrals/stats            req: AUTH -> ⚠ upstream + "top_referrers":[] | {}
GET /api/bedolaga/referrals/referrers        req: AUTH + q{limit=50 (1..200),offset,sort=invited_desc,search,top_only=false,min_refs=0} -> ⚠ upstream
GET /api/bedolaga/referrals/referrers/{id}/refs req: AUTH -> ⚠ upstream (get_all_users(200,0); id не используется)
```

## 1.25 `api/v1/docs.py` — tags `docs`

```
GET    /api/docs/list                        req: AUTH -> W<[{name,title,editable}]> (changelog/history: editable=true)
GET    /api/docs/{name}                      req: AUTH + name:changelog|history
                                             -> W<{name,title,editable:true,raw,html,updated_at?}>
                                             history: из docs_documents (+updated_at) + sections:[{title,level,html}] (split по '## ')
                                             changelog: генерируется из changelog_entries (без sections)
GET    /api/docs/{name}/entries              req: AUTH -> W<{name,title,editable:true,header,entries[]}>
                                             history: + document:{raw,html,updated_at|null} + sections:[{title,level,html}];
                                                      entries = history_entries, каждый + body_html (python-markdown от body)
                                             changelog: entries = changelog_entries (без document/sections, без body_html)
POST   /api/docs/{name}/entries              req: AUTH + EntryIn{date,time,author,title,body,also_history} -> W<{id}> (201)
                                             history: origin='manual', also_history игнорируется
                                             changelog: also_history=true -> второй INSERT в history_entries
                                                        (origin='changelog', source_changelog_id), одна транзакция
PUT    /api/docs/{name}/entries/{entry_id}   req: AUTH + EntryUpdate{date,time,author,title,body} -> ⚠ {"success":true}
                                             history: 404 NOT_FOUND; changelog: ⚠ success:false NOT_FOUND
DELETE /api/docs/{name}/entries/{entry_id}   req: AUTH -> ⚠ {"success":true} (history: 404 NOT_FOUND)
PUT    /api/docs/history                     req: AUTH + DocumentUpdate{content,expected_updated_at?} -> W<{updated_at}>
                                             optimistic lock: stale expected_updated_at -> 409 CONFLICT
POST   /api/docs/history/import              req: AUTH + multipart file (.md <=1 МБ, UTF-8)
                                             -> W<{updated_at,chars}> (content перезаписывается, блоки не трогаются)
GET    /api/docs/history/export              req: AUTH -> text/markdown attachment (документ + '## Дополнения';
                                             filename HISTORY_TECHNICAL_<YYYYmmdd_HHMMSS>.md)
POST   /api/docs/changelog/import            req: AUTH + multipart file -> W<{imported}>
GET    /api/docs/changelog/export            req: AUTH -> text/markdown attachment (CHANGELOG_CMS_<YYYYmmdd_HHMMSS>.md)
POST   /api/docs/render                      req: AUTH + {"markdown": str} (<=1 МБ, пусто разрешено)
                                             -> W<{html}> — python-markdown (tables/fenced_code/nl2br/sane_lists), БЕЗ prose-обёртки;
                                             400 INVALID_INPUT (не JSON / markdown не str), 413 FILE_TOO_LARGE
Ошибки: {"success":false,"error":str,"code":"NOT_FOUND"|"FORBIDDEN"|"INVALID_INPUT"|"CONFLICT"|"FILE_TOO_LARGE"|"DB_ERROR"}
Хранилище: docs_documents(name PK, content, updated_at) — базовый markdown технической истории;
            history_entries(id, entry_date, entry_time, author, title, body, origin, source_changelog_id) — блоки «Дополнения».
            ensure_docs_tables()/seed_history_document() — DDL + seed при старте; docs/*.md — источник seed и цель экспорта.
```

## 1.26 `api/v1/support/*` — prefix `/api/support`

```
GET  /api/support/health                     без AUTH -> W<{status:"ok"|"degraded",db:boolean,pollers:{channel:status}}>
                                             # db — реальный SELECT 1 через session factory; ошибка/нет сервиса -> db:false, status:"degraded"
                                             # pollers — живые app.state.support.pollers ({} без сервиса); всегда HTTP 200
GET  /api/support/config-status              req: AUTH -> W<{channels[],poll_interval_seconds,reply_window_hours,
                                               media_max_mb,upload_max_bytes,ai{mode,effective_mode,has_key,paused,model}}>
                                             # приоритет: реестр (support_*, db/env) → support_setting → SupportSettings
                                             # registry-дефолты legacy-runtime не перетирают
                                             # media_max_mb: support_media_max_mb, кламп 1..50; upload_max_bytes = media_max_mb*1024*1024
GET  /api/support/conversations              req: AUTH + q{status:^(open|pending|resolved|closed)$, channel:^[a-z0-9_]{1,32}$, priority:^(low|normal|high|urgent)$,
                                               assignee_id:int, customer_id:int, unread_only=false, q<=200, page=1 (>=1), per_page=50 (1..200)}
                                             -> W<{items[],total,page,per_page}>  # неверные status/channel/priority -> 422
GET  /api/support/conversations/{id}         req: AUTH -> W<{conversation,messages[],customer,suggestion}>  # messages <=200, пагинации в API нет
                                             # suggestion — pending-предложка в публичной форме §5.2 (level/gate/used без chunk)
                                             # или null; shadow тоже попадает в ответ — скрывает фронт
POST /api/support/conversations/{id}/reply   req: AUTH + ReplyIn{text<=4000, attachment_ids[]<=10, client_msg_id?, force=false}
                                             -> W<{message_id,conversation_id,external_msg_id,repeated?}|{conversation_id,message_ids[],count}>
                                             # client_msg_id (^[A-Za-z0-9_-]{8,64}$) — идемпотентность текстового ответа:
                                             # повтор тем же ключом -> {message_id, repeated:true} без переотправки; ключ не пишется при attachment_ids
                                             # force=false + активный lease другого оператора (claimed_at <=15 мин) -> 409 LOCKED_BY_OTHER;
                                             # force=true перехватывает диалог (set_assignee на текущего оператора) и отправляет
                                             # пустой text без вложений -> 400 INVALID_INPUT; окно 24ч -> 409 REPLY_WINDOW_CLOSED
POST /api/support/conversations/{id}/read    req: AUTH -> W<{conversation_id,unread:0}>
POST /api/support/conversations/{id}/state   req: AUTH + StateIn{status:open|pending|resolved|closed, priority?:low|normal|high|urgent, seen_at?:ISO-8601}
                                             -> W<{conversation_id,status,priority,synced,priority_synced}>
                                             # seen_at + статус resolved|closed + входящее после seen_at -> 409 CLIENT_WROTE (статус не меняется)
                                             # synced/priority_synced: "synced"|"unchanged"|"skipped"|"error"; error не откатывает локальное значение
POST /api/support/conversations/{id}/assignee req: AUTH + AssigneeIn{assignee_id:int|null} -> W<{conversation_id,assignee_id}>
GET  /api/support/conversations/{id}/customer req: AUTH -> W<SupportCustomerCard>
POST /api/support/conversations/{id}/customer/refresh req: AUTH -> W<SupportCustomerCard>
GET  /api/support/pollers                    req: AUTH -> W<{pollers:{channel:status}}>
GET  /api/support/kb                         req: AUTH + q{status:^(draft|published|archived|all)$, q<=200, page>=1, per_page 1..100}
                                             -> W<{items:[{id,slug,title,source,status,version,updated_at,updated_by,excerpt}],total,page,per_page}>
                                             # status не задан -> только published; status=all -> все статусы
GET  /api/support/kb/search                  req: AUTH + q{1..200, limit 1..20} -> W<{items:[{id,slug,title,rank,snippet<=300}]}>
                                             # только published; to_tsvector('russian') @@ websearch_to_tsquery('russian', :q), ts_rank_cd
GET  /api/support/kb/candidates              req: AUTH + q{status:^(new|accepted|rejected|all)$=new, page>=1, per_page 1..100}
                                             -> W<{items:[{id,topic,question,answer,occurrences,source,status,created_at}],total,page,per_page}>
POST /api/support/kb/candidates/{id}         req: AUTH + {decision:accept|reject, reason?<=500, title?<=200, body?<=200000}
                                             -> W<{id,status,doc_id?}>  # accept -> draft-статья source='candidate', кандидат линкуется doc_id
POST /api/support/messages/{id}/feedback     req: AUTH + {verdict:correct|partial|wrong, note?<=1000, correct_answer?<=4000}
                                             -> W<{qa_pair_id:int|null}>  # question = последнее входящее до сообщения
                                             # correct/partial -> support_qa_pair(source='feedback', answer=correct_answer|текст сообщения)
                                             # wrong -> кандидат source='feedback' (тема из вопроса, occurrences++);
                                             #          + qa_pair, если передан correct_answer; нет сообщения -> 404 NOT_FOUND
GET  /api/support/suggestions                req: AUTH + q{status:^(pending|sent|edited|rejected|superseded|all)$=all,
                                               conversation_id?>=1, page>=1, per_page 1..100=50}
                                             -> W<{items:[SupportAiSuggestion],total,page,per_page}>  # публичная форма §5.2
GET  /api/support/suggestions/{id}           req: AUTH -> W<SupportAiSuggestion>  # level/gate/used без chunk; нет -> 404
POST /api/support/suggestions/{id}/decide    req: AUTH + DecideIn{decision:send|edit|reject, final_text?<=4000, reason?<=64}
                                             -> W<{status:'sent',message_id}|{status:'edited',text}|{status:'rejected'}>
                                             # не pending -> 409 CONFLICT; send проходит lease-проверку и Outbox
                                             # (окно 24ч -> 409 REPLY_WINDOW_CLOSED); reject требует reason из
                                             # REJECT_REASONS (wrong_facts|unclear|off_topic|too_formal|sensitive|other), иначе 400
GET  /api/support/assistant/settings         req: AUTH -> W<SupportAiSettings>  # без api_key; без ключа effective_mode='off'
PUT  /api/support/assistant/settings         req: AUTH + {mode?, min_confidence? 0..1, require_kb?, auto_per_hour?>=0,
                                               debounce_seconds? 3..60} -> W<SupportAiSettings> + runtime{}
                                             # пишет support_ai_* в регистр и перезагружает runtime без рестарта
POST /api/support/assistant/pause            req: AUTH + {hours? 1..744 | until?, note?<=500} -> W<{until,by,note}>
                                             # ровно одно из hours/until; until не дальше +31 дня; иначе 400
DELETE /api/support/assistant/pause          req: AUTH -> W<{paused:false}>  # режим ИИ не меняется
GET  /api/support/assistant/activity         req: AUTH + q{since?, before?>=1, limit 1..100=50} -> W<{items:[SupportAiActivityItem]}>
GET  /api/support/assistant/stats            req: AUTH + q{days 1..90=30} -> W<SupportAiStats>  # + by_day[]
POST /api/support/assistant/try              req: AUTH + {text 1..2000, assume_auto=false}
                                             -> W<{draft:{reply,operator_note,used[],confidence,clarify,needs_human},
                                                   gate:{action,reason,level?}}>
                                             # без записи в БД; нет ключа -> 409 AI_KEY_MISSING; нет провайдера -> 409 AI_DISABLED;
                                             # ошибка провайдера -> 502 PROVIDER_ERROR
POST /api/support/kb/import                  req: AUTH + ImportIn{kind:'text'|'result_json', text?, payload?:object|string,
                                               operator_names?[]<=50 (каждое <=80), dry_run=false}
                                             -> W<{job_id}>  # HTTP 200, 202-семантика в теле; запускает support_job kind='kb_import'
                                             # размер до парсинга: текст >20 MiB / result.json >50 MiB -> 413 IMPORT_TOO_LARGE;
                                             # второй активный джоб того же kind -> 409 JOB_BUSY; пустой text/payload -> 400 INVALID_INPUT
GET  /api/support/kb/import/{job_id}         req: AUTH -> W<{id,kind,status,progress,total,result?,error?,started_at,finished_at}>
                                             # status: queued|running|done|error; result: {questions,pairs_created,skipped_duplicates,
                                             # candidates_created,errors[]}, у dry_run + would_create/would_skip/would_create_candidates
POST /api/support/kb/import/{job_id}/cancel  req: AUTH -> W<{status:'error',error:'cancelled'}>
                                             # отменяет queued|running; завершённый джоб возвращается как есть; нет джоба -> 404 NOT_FOUND
POST /api/support/kb                         req: AUTH + KbDocIn{title 1..200, body 1..200000, slug?, tags[]<=20, source=manual|import|candidate|faq}
                                             -> W<{id,slug,version:1,status:'draft'}>
GET  /api/support/kb/{id}                    req: AUTH -> W<{doc:{id,slug,title,body,status,version,tags,source,created_at,updated_at,published_at}}>
PUT  /api/support/kb/{id}                    req: AUTH + KbDocIn + expected_version -> W<{id,version,status,slug}>
                                             # устаревший expected_version -> 409 KB_VERSION_CONFLICT; published остаётся published (version++)
POST /api/support/kb/{id}/publish            req: AUTH + {expected_version} -> W<{id,status:'published',published_at}>
POST /api/support/kb/{id}/archive            req: AUTH -> W<{id,status:'archived',archived_at}>
POST /api/support/kb/{id}/restore            req: AUTH -> W<{id,status:'draft'}>  # archived -> draft; другие статусы не меняются
DELETE /api/support/kb/{id}                  req: AUTH -> W<{deleted:true}>; published -> 409 KB_DOC_PUBLISHED (сначала archive)
POST /api/support/attachments                req: AUTH + multipart file -> W<{token,media_type,mime_type,original_name,bytes,sha256}>
                                             # allowlist расширений/mime; лимит из support_media_max_mb (1..50, дефолт 8 МБ),
                                             # превышение -> 413 FILE_TOO_LARGE; глобальный потолок middleware/nginx — 64 МБ
                                             # upload-токен живёт 24ч (env SUPPORT_UPLOAD_TOKEN_TTL_HOURS)
GET  /api/support/attachments/{id}           req: AUTH + q{download=false,conversation_id?} -> FileResponse
                                             # ACL: attachment → message → conversation (INNER JOIN); битая связка или чужой conversation_id -> 404
GET  /api/support/sla/policies               req: AUTH -> W<{items:[{name,first_response_minutes,resolution_minutes}]}>
PUT  /api/support/sla/policies/{name}        req: AUTH + {first_response_minutes 1..100000, resolution_minutes 1..100000}
                                             -> W<{name,first_response_minutes,resolution_minutes}>; нет политики -> 404 SLA_POLICY_NOT_FOUND;
                                             аудит sla.policy_update (resource support_sla_policy)
GET  /api/support/sla/overview               req: AUTH + q{days 7..90=7} -> W<{policies:[...],breaches:{first_response,resolution},
                                             events:[{id,conversation_id,kind,due_at,notified_at,breached_at,subject,priority,status,
                                             assignee_id,overdue_minutes}]}>  # overdue_minutes < 0 — «до дедлайна»
GET  /api/support/templates                  req: AUTH + q{q?<=200, category?<=64, page>=1=1, per_page 1..100=50}
                                             -> W<{items:[{id,shortcut,title,body,category,uses,created_by,created_at,updated_at}],total,page,per_page}>
POST /api/support/templates                  req: AUTH + {shortcut ^[a-z0-9][a-z0-9_-]{0,31}$, title 1..120, body 1..4000, category?<=64}
                                             -> W<template>; дубль shortcut -> 409 TEMPLATE_EXISTS; аудит template.create
PUT  /api/support/templates/{id}             req: AUTH + TemplateIn -> W<template>; нет шаблона -> 404 NOT_FOUND; дубль -> 409 TEMPLATE_EXISTS
DELETE /api/support/templates/{id}           req: AUTH -> W<{deleted:true}>; нет шаблона -> 404 NOT_FOUND; аудит template.delete
POST /api/support/templates/{id}/use         req: AUTH -> W<{id,uses}>  # uses = uses + 1, updated_at не меняется
GET  /api/support/customers/{customer_id}/notes req: AUTH -> W<{items:[{id,text,actor_id,actor_name,created_at}]}>  # новые сверху
                                             # нет клиента -> 404 NOT_FOUND
POST /api/support/customers/{customer_id}/notes req: AUTH + {text 1..2000} -> W<note>
                                             # автор — текущий админ (actor_key=str(id)); аудит note.create
DELETE /api/support/notes/{note_id}          req: AUTH -> W<{deleted:true}>; нет заметки -> 404 NOTE_NOT_FOUND; аудит note.delete
POST /api/support/presence                   req: AUTH + {conversation_id, state:viewing|typing} -> W<{ok:true,throttled:boolean}>
                                             # heartbeat не чаще 1 раза в 5 с на пару (оператор, диалог);
                                             # запись публикует WS-кадр presence; нет диалога -> 404 NOT_FOUND
GET  /api/support/presence/{conversation_id} req: AUTH -> W<{items:[{actor_id,actor_name,state,seen_at}]}>  # TTL 120 с; нет диалога -> 404
GET  /api/support/analytics                  req: AUTH + q{days 7..365=30} -> W<{range_days,totals,by_day[],by_channel[],by_priority[],
                                             first_response,by_operator[],ai}>  # единый снимок; ошибка любого блока -> 5xx
GET  /api/support/operators                  req: AUTH -> W<{items:[{id,login,display_name,status,active_dialogs,replies_30d,present}]}>
GET  /api/support/audit                      req: AUTH + q{action?<=64, actor_id?>=1, page>=1=1, per_page 1..100=50}
                                             -> W<{items:[{id,actor_id,actor_name,action,resource,resource_id,payload,ip,created_at}],
                                                   total,page,per_page}>  # новые сверху
GET  /api/support/audit/actions              req: AUTH -> W<{items:[{action,count}]}>  # уникальные действия, частые сверху
WS   /api/support/ws                         auth-кадр обрабатывает SupportWebSocketManager; без app.state.support — close(NOT_READY)
Ошибки: HTTPException(detail = ERR); прикладные коды CLIENT_WROTE, LOCKED_BY_OTHER, REPLY_WINDOW_CLOSED,
        NOT_FOUND, INVALID_INPUT, NOT_IMPLEMENTED, UPSTREAM_ERROR, CONFLICT,
        KB_VERSION_CONFLICT, KB_DOC_PUBLISHED, IMPORT_TOO_LARGE, IMPORT_PARSE_FAILED, JOB_BUSY,
        AI_KEY_MISSING, AI_DISABLED, AI_PAUSED, PROVIDER_ERROR, SLA_POLICY_NOT_FOUND, TEMPLATE_EXISTS
```

## 1.27 `api/v1/bedolaga/analytics.py` — prefix `/api/bedolaga/analytics`

```
GET /api/bedolaga/analytics/tariffs        req: AUTH + q{days_back=365 (30..3650),refresh=false,include_inactive=true}
                                           -> ⚠ {generated_at,as_of,currency,price_source_priority,coverage,items[],totals,warnings[],partial,sources}
                                           # items: все тарифы (вкл. is_active=false и 0 ₽) + строка «Не определён»;
                                           # price_source=bot_db|transactions|unknown, price_kind=list|realized|unknown,
                                           # price_basis=exact_period|proportional|30_day|per_day|realized_per_day|daily|free|unknown,
                                           # clients_paid/clients_trial/share_pct, mrr_kopeks, paid_forward_kopeks,
                                           # next_month_expected_kopeks, unknown_price_clients
GET /api/bedolaga/analytics/overview       req: AUTH + q{month=YYYY-MM (текущий MSK),months=6 (1..24),days_back=365 (30..3650),basis=cash|accrual,refresh=false}
                                           -> ⚠ {month,next_month,basis,coverage,kpis{},by_tariff[],monthly[],warnings[],partial,sources}
                                           # kpis: mrr(+rubles/basis/is_lower_bound/unknown), cash_forecast_next_month,
                                           # renewals_due_next_month(+count), paid_forward, accrual_revenue_current_month(+unknown),
                                           # accrual_revenue_month(+unknown), cash_received_current_month, cash_received_month,
                                           # payments_current_month, active_paid_clients/subscriptions, autopay_enabled_subscriptions
                                           # by_tariff[]: tariff_id,name,clients_paid/trial,share_pct,monthly_price_kopeks,
                                           # price_source/kind,mrr,paid_forward,next_month_expected,unknown_price_clients,is_free
                                           # monthly[]: cash_received(+rubles),payments_count,unique_payers,renewal_payments,purchase_payments,
                                           # renewal_proxy,avg_payment_kopeks,accrual_revenue (null для прошлых месяцев, accrual_is_estimate=true)
GET /api/bedolaga/analytics/forecast       req: AUTH + q{month=YYYY-MM (следующий месяц),basis=cash|renewal,refresh=false}
                                           -> ⚠ {month,basis,totals{expected_kopeks,expected_rubles,payments_count,unknown_count,autopay_enabled_count},
                                                 by_day[{date,expected_kopeks,payments_count}],
                                                 by_tariff[{tariff_id,tariff_name,expected_kopeks,payments_count,unknown_count}],
                                                 items[] (<=500, sort expected_charge_date,user_id),items_total,warnings[],partial,sources}
GET /api/bedolaga/analytics/customers/{user_id} req: AUTH + q{days_back=3650 (1..3650),refresh=false}
                                           -> ⚠ {user,primary_subscription|null,tariff,subscriptions[],payments[] (<=50),
                                                 money{paid_total,paid_last_12m,paid_current_month,paid_forward,
                                                       next_payment_date,expected_charge_date,next_payment_kopeks,next_payment_known}}
Ошибки: 400 (month/basis), 404 (user не найден), 502 (upstream/таймаут), 503 (Bedolaga не настроена)
Формат ошибки: {"success":false,"error":str} (unwrapped на app-handler)
Кэш: снимок (users+transactions+bot_db+/stats/full) — 60с, single-flight по days_back; refresh=true обходит снимок
      users — 200/страница; transactions — 100/страница, concurrency<=4, partial при сбое страницы;
      bot_db — success 60с / error 45с / circuit breaker 300с (см. core/bot_db.py)
      снимок инвалидируется при сохранении/успешном тесте Bedolaga/Bot DB
      (integrations.on_settings_changed, bootstrap, POST /settings/integrations/{id}/test)
```

**Итого:** 170 маршрутов (169 HTTP + 1 WS), `response_model` — 0.

---

# 2. Backend Pydantic Schemas

`web/backend/schemas/` — 15 модулей, 38 `BaseModel`. Нет `Config`, нет валидаторов, нет Enum.

```python
# common.py
class ApiResponse(Generic[T]):         success: bool = True; data: T
class ErrorResponse:                   success: bool = False; error: str; code: Optional[str] = None
class PaginatedData(Generic[DataT]):   items: List[DataT]; total: int; page: int; per_page: int   # @property pages -> int
class HealthResponse:                  status="ok"; service="hexaveil-cms-api"; version="0.1.0"; database="connected"
class SuccessMessage:                  success=True; message="OK"

# auth.py
class LoginRequest:                    login: str(1..100); password: str(1..200)
class UserInfo:                        id:int; login:str; email:str=""; role:str="admin"
class LoginResponse:                   success=True; token:str; user:UserInfo
class MeResponse:                      success=True; user:UserInfo
class ChangePasswordRequest:           current_password:str(1..200); new_password:str(1..200)

# user.py
class UserResponse:                    id:int; login:str; email:str=""; role:str="author"; display_name:str=""; status:str="active";
                                       posts_count:Optional[int]=None; comments_count:Optional[int]=None;
                                       created_at:Optional[str]=None; updated_at:Optional[str]=None
class UserCreate:                      login:str(1..100); password:str(1..200); email:str=""; role:str="author"; display_name:str=""; status:str="active"
class UserUpdate:                      login:Optional[str]=None; password:Optional[str]=None; email:Optional[str]=None; role:Optional[str]=None;
                                       display_name:Optional[str]=None; status:Optional[str]=None

# post.py
class PostResponse:                    id:int; title:str; slug:str; content:str=""; excerpt:str=""; category_id:Optional[int]=None;
                                       category_name:Optional[str]=None; status:str="draft"; image:str="";
                                       seo_title:Optional[str]=None; seo_description:Optional[str]=None; canonical:Optional[str]=None;
                                       featured:bool=False; comments_enabled:bool=True; user_id:Optional[int]=None;
                                       author_name:Optional[str]=None; views:Optional[int]=None; tags:List[str]=[];
                                       created_at:Optional[str]=None; updated_at:Optional[str]=None
class PostCreate:                      title:str(1..255); slug:Optional[str]=None; content:str=""; excerpt:str="";
                                       category_id:Optional[int]=None; status:str="draft"; image:str="";
                                       seo_title/seo_description/canonical:Optional[str]=None; featured:bool=False;
                                       comments_enabled:bool=True; publish_date:Optional[str]=None; tags:List[str]=[]
class PostUpdate:                      title/slug/content/excerpt/status/image/seo_title/seo_description/canonical/publish_date: Optional[str]=None;
                                       category_id:Optional[int]=None; featured:Optional[bool]=None; comments_enabled:Optional[bool]=None; tags:Optional[List[str]]=None

# category.py
class CategoryResponse:                id:int; name:str; slug:str; description:str=""; posts_count:Optional[int]=None
class CategoryCreate:                  name:str(1..150); slug:Optional[str]=None; description:str=""
class CategoryUpdate:                  name/slug/description:Optional[str]=None

# page.py
class PageResponse:                    id:int; title:str; slug:str; content:str=""; meta_description:str=""; status:str="draft";
                                       user_id:Optional[int]=None; author_name:Optional[str]=None; created_at/updated_at:Optional[str]=None
class PageCreate:                      title:str(1..); slug:Optional[str]=None; content:str=""; meta_description:str=""; status:str="draft"
class PageUpdate:                      title/slug/content/meta_description/status:Optional[str]=None

# menu.py
class MenuResponse:                    id:int; name:str; url:str; location:str="main"
class MenuCreate:                      name:str(1..); url:str(1..); location:str="main"
class MenuUpdate:                      name/url/location:Optional[str]=None

# widget.py
class WidgetResponse:                  id:int; area:str="footer"; title:str; content:str=""; sort_order:int=0
class WidgetCreate:                    area:str="footer"; title:str(1..); content:str=""; sort_order:int=0
class WidgetUpdate:                    area/title/content:Optional[str]=None; sort_order:Optional[int]=None

# media.py
class MediaItemResponse:               path:str; url:str; name:str; size:int; modified:int
class MediaDeleteRequest:              path:str

# theme.py
class ThemeOption:                     label:str; type:str="text"; default:str=""; value:str=""; hint:Optional[str]=None;
                                       rows:Optional[int]=None; options:Optional[Dict[str,str]]=None
class ThemeSettingsResponse:           theme:str; label:str; options:Dict[str,ThemeOption]
ThemeSettingsUpdate = Dict[str,str]    # alias, не BaseModel

# log.py
class LogResponse:                     id:int; level:str; category/channel/source:Optional[str]=None; message:str;
                                       context:Optional[str]=None; created_at:Optional[str]=None
class LogClearRequest:                 category:Optional[str]=None; channel:Optional[str]=None

# setting.py
class SettingsResponse:                site_name,site_description,meta_keywords,meta_description,active_theme,posts_per_page,
                                       comments_auto_approve,maintenance_mode,docker_config,loki_config: Optional[str]=None
class SettingsUpdate(SettingsResponse): # без собственных полей

# notification.py
class NotificationResponse:            id:int; admin_id:Optional[int]=None; type:str; severity:str="info"; title:str;
                                       body/link:Optional[str]=None; is_read:bool=False; source/source_id/group_key:Optional[str]=None;
                                       created_at:Optional[str]=None
class NotificationMarkRead:            ids:List[int]=[]
class UnreadCountResponse:             count:int=0

# dashboard.py
class DashboardStats:                  posts:int; comments:int; users:int; categories:int; posts_published:int;
                                       posts_draft:int; comments_total:int; comments_approved:int; users_active:int

# finance.py
class TransactionResponse:             id:int; date:str; date_display:str; month:str; type:str; participant:str=""; category:str="";
                                       amount:float; description:str=""
class TransactionCreate:               date:str; type:str("^(income|expense)$"); category:str=""; participant:str="";
                                       amount:float=0; description:str=""
class TransactionUpdate:               id:int; date/type/category/participant:Optional[str]=None; amount:Optional[float]=None;
                                       description:Optional[str]=None
class ChartPoint:                      key:str; label:str; income:float=0; expense:float=0; balance:float=0
class DeleteBulkRequest:               ids:List[int]=[]
```

**Inline-схемы внутри роутеров (не в `schemas/`):** `SubscriptionExtendRequest{days:int 1..}`, `TrafficAddRequest{traffic_gb:int 1..1000000}`, `DevicesAddRequest{count:int 1..10000}`, `UserUpdateRequest{first_name?,last_name?,username?}`, `BalanceModifyRequest{amount_kopeks:int,reason?}`, `SubscriptionCreateRequest{duration_days,traffic_limit_gb?,device_limit?,is_trial}`, `EntryIn{date,time,author,title,body,also_history}` (`also_history` читается только для changelog), `EntryUpdate{date,time,author,title,body}`, `DocumentUpdate{content:str 1..1_000_000,expected_updated_at?:str|null}`, `ReplyIn{text<=4000,attachment_ids[]<=10,client_msg_id?:str(pattern ^[A-Za-z0-9_-]{8,64}$),force:bool=false}`, `StateIn{status:^(open|pending|resolved|closed)$,priority?:^(low|normal|high|urgent)$,seen_at?:datetime|null}`, `AssigneeIn{assignee_id:int|null}`.

---

# 2A. Backend Core Public Interfaces

## `core/database.py`

```python
class Base(DeclarativeBase): pass
async def get_engine() -> AsyncEngine
async def get_session_factory() -> async_sessionmaker[AsyncSession]
async def get_db() -> AsyncGenerator[AsyncSession, None]     # FastAPI dependency
async def check_connection() -> bool
async def close_engine() -> None
# engine: pool_pre_ping=True, pool_recycle=3600, echo=SQL_ECHO ("1"); session: expire_on_commit=False
# transaction-helper и row->dict helper отсутствуют
```

## `core/security.py`

```python
def create_access_token(user: dict) -> str      # payload: sub=user["id"], login=user.get("login",""), role=user.get("role","admin"), iat, exp
def decode_token(token: str) -> Optional[dict]  # payload | None при любой ошибке; verify_sub отключён (sub — int из PHP)
def verify_admin_password(password: str, hash: str) -> bool   # bcrypt $2a/$2b/$2y
def hash_password(password: str) -> str                        # bcrypt gensalt(rounds=10)
# JWT: settings.jwt_algorithm (HS256), settings.jwt_secret_resolved, settings.jwt_ttl (86400)
# FastAPI-зависимости и role-check здесь ОТСУТСТВУЮТ — см. api/deps.py:get_current_admin
```

## `core/bot_db.py` (read-only БД бота)

```python
@dataclass(frozen=True) class BotDbConfig(host, port=5434, name="remnawave_bot", user="cms_ro", password="")
  property url -> str                        # postgresql+asyncpg, URL.create (пароль экранируется)
def env_config() -> BotDbConfig | None        # legacy BOT_DB_* из core/config.py
def is_configured() -> bool                   # _config или ENV — для стартового лога
async def ensure_config() -> bool             # ленивое чтение реестра: fast path → negative TTL 60с →
                                              # lock/double-check → wait_for(refresh_config, 3с); ошибки → warning, False
async def refresh_config(db=None) -> bool     # эффективные bot_db_* из реестра; clear_cache() + dispose при смене URL
                                              # + сброс _circuit_until = 0 (восстановление без рестарта)
async def invalidate() -> None                # clear_cache + сброс circuit breaker + dispose engine
async def get_tariffs_result(*, timeout=2.0, use_cache=True) -> dict
    # {status:"disabled|ok|error|timeout", tariffs:list, error:str|None, checked_at:ISO, cached:bool}
    # status="ok" + tariffs=[] — валидный пустой каталог (отличается от error/timeout)
    # при _config=None сначала await ensure_config()
async def get_tariffs() -> list[dict]         # legacy-контракт: список, [] при disabled/error/timeout (лог warning)
def clear_cache() -> None                     # сброс TTL-кэша каталога (вызывается refresh_config при сохранении настроек)
async def close_engine() -> None
# engine ленивый; конфиг из реестра имеет приоритет над env
# SELECT <32 колонки> FROM tariffs ORDER BY display_order, id
# таймауты: pool_timeout 2с, asyncpg connect 2с, command_timeout 5с, asyncio.wait_for ≤2с
# кэш: ok 60с / error|timeout 45с, circuit breaker 300с; single-flight через asyncio.Lock
# битая JSON-строка тарифа пропускается (не обнуляет весь каталог)

# Ключи элемента списка (SELECT):
id, name, description, is_active, display_order, traffic_limit_gb, device_limit, device_price_kopeks,
max_device_limit, period_prices, tier_level, is_trial_available, trial_duration_days, is_daily,
daily_price_kopeks, custom_days_enabled, price_per_day_kopeks, min_days, max_days, custom_traffic_enabled,
traffic_price_per_gb_kopeks, min_traffic_gb, max_traffic_gb, allow_traffic_topup, traffic_topup_enabled,
show_in_gift, is_highlighted, highlight_period_days, traffic_reset_mode, external_squad_uuid, panel_tag,
lava_product_id, allowed_squads, server_traffic_limits, created_at, updated_at
# Дополнительно: period_prices/allowed_squads/server_traffic_limits/traffic_topup_packages -> json.loads если str;
# period_prices_list: [{days:int, price_kopeks:int, price_rubles:float}]; created_at/updated_at -> ISO строки
```

## `core/bedolaga_analytics.py` (чистое ядро аналитики, без FastAPI)

```python
MSK = timezone(timedelta(hours=3))            # Europe/Moscow, без DST
UNKNOWN_TARIFF_NAME = "Не определён"; UNKNOWN_TARIFF_KEY = "unknown"

def now_msk() -> datetime
def parse_ts(value) -> datetime | None        # ISO/int/float; naive -> UTC -> MSK
def iso(value) / date_str(value) -> str | None
def parse_month("YYYY-MM") -> (start, end)    # MSK, end exclusive; ValueError на мусор
def month_key(dt) / shift_month(month, delta) / month_days(month)

def normalize_name(name) -> str               # emoji/пунктуация -> пробел, casefold, ё->е
def parse_days(description) -> int | None
def parse_payment_description(description, fallback_tariff_name=None)
    # -> {name, days, kind: "purchase"|"renewal"|"autorenewal"|None}
    # «Покупка тарифа X на N дней» / «Продление подписки на N дней (X)» / «Автопродление ...»
def payment_kind(description) -> str | None

def user_subscriptions(user) -> list[dict]    # subscription + subscriptions[], dedupe by id
def is_paid_active(sub, now=None) -> bool     # end>now, не trial, status/actual_status не expired/disabled/...; limited = платная
def is_trial_sub(sub) -> bool
def primary_subscription(user, now=None) -> dict | None  # paid: max(end_date,tariff_id); иначе trial
def period_days(sub) -> int                   # autopay_period_days -> фактический интервал -> 30
def remaining_days(sub, now=None) -> int      # ceil, >=0
def expected_charge_date(sub) -> datetime     # end_date - autopay_days_before при autopay_enabled
def tariff_of(sub) -> {tariff_id,tariff_name,tariff_key,tariff_missing}
def user_tariff(user, now=None) -> тот же dict по primary
def normalize_user_subscription(user, now=None) -> dict
    # копия user: заполняет subscription первичной из subscriptions[] (аддитивно),
    # добавляет top-level tariff_id/tariff_name/tariff_missing

class PriceCatalog(bot_tariffs, transactions, users, *, now, days_back=365)
  def quote(tariff_id, tariff_name, days=30) -> PriceQuote
  def monthly(tariff_id, tariff_name) -> PricePart | None
# приоритет цен: bot_db.period_prices(exact) -> price_per_day -> transactions median/per-day -> daily_price
# нулевые subscription_payment (смена тарифа/массовое действие) не участвуют в медиане;
# нет точной цены периода, но есть месячная -> round(monthly * days / 30)
# 0 — валидная цена только для явно бесплатного тарифа bot_db; иначе unknown при отсутствии данных
# PriceQuote.to_dict(prefer="monthly"|"period"):
#   price_known, price_source, price_kind, price_basis, confidence, is_free,
#   monthly_price_kopeks/rubles, monthly_basis/source, period_price_*, period_basis,
#   period_days, price_per_day_kopeks, samples, last_seen_at

@dataclass PageResult: items,total,pages_loaded,partial,error
@dataclass RawData: users,transactions,bot_db,full_stats,fetched_at,warnings; property partial
async def fetch_all_users(client=None, *, page_size=200, max_pages=100, timeout=15.0) -> PageResult
async def fetch_all_transactions(client=None, *, page_size=100, concurrency=4, max_pages=200,
                                 timeout=15.0, date_from=None) -> PageResult   # partial при сбое страницы
async def fetch_full_stats(client=None, *, timeout=10.0) -> dict | None
async def load_raw_data(*, days_back=365, refresh=False) -> RawData
    # TTL 60с, single-flight (asyncio.Lock) по days_back; refresh=True обходит кэш
def invalidate_snapshot_cache() -> None

class AnalyticsEngine(raw, *, now=None, price_days_back=365)
  def tariffs(*, include_inactive=True) -> dict    # F1-F5, per-tariff MRR/forward/next month
  def overview(*, month, months=6, basis="cash") -> dict  # F4,F5,F8-F10,F12,F14,F15 + monthly[]
  def forecast(*, month, basis="cash") -> dict     # F7,F8,F9,F13; items<=500
  def customer(user_id, *, days_back=3650) -> dict | None # F6,F7,F11-F13; payments<=50
# Деньги считаются в копейках (int), рубли — ROUND_HALF_UP до 2 знаков;
# MRR: mrr_basis=list|realized|mixed|unknown, mrr_is_lower_bound при unknown;
# trial в деньги не входит; free (0 ₽) входит с нулём; кэш снимка 60с
```

## `core/bedolaga_client.py`

```python
bedolaga_client: BedolagaClient
async def ensure_configured_async(db=None) -> bool
    # request-путь: disabled → False; is_configured → True; иначе lock/double-check →
    # apply_bedolaga(db | сессия get_session_factory) → ENV-fallback при ошибке чтения реестра
def ensure_configured() -> bool     # ENV-only fallback: BEDOLAGA_API_URL + BEDOLAGA_API_TOKEN; False если disabled
class BedolagaClient:
  configure(base_url: str, api_token: str, *, timeout: float = 15.0,
            proxy_kwargs: dict | None = None) -> None   # сбрасывает кэш клиента и снимает disable
  reset() -> None                                      # сбрасывает URL/токен/клиент/proxy (не трогает disabled)
  disable() -> None                                    # hard-off: reset() + запрет ENV-подъёма в ensure_configured
  property disabled -> bool
  property is_configured -> bool
# httpx.AsyncClient(base_url, X-API-Key, Timeout(timeout), trust_env=False, **proxy_kwargs)
```
Кастомных исключений нет: пробрасываются `httpx.HTTPStatusError` / `httpx.HTTPError` / `json.JSONDecodeError`.

```
GET    /stats/overview                                  get_overview() -> dict
GET    /stats/full                                      get_full_stats() -> dict
GET    /health                                          get_health() -> dict
GET    /maintenance/status | /admin/maintenance          get_maintenance() -> {"available":bool,"enabled":bool,<upstream keys>}
GET    /users                                           list_users(limit=20, offset=0, **filters) -> dict
GET    /users/{id}                                      get_user(user_id) -> dict
GET    /users/by-telegram-id/{tg}                        get_user_by_telegram(telegram_id) -> dict
GET    /users?search=                                    get_user_by_email(email, page_size=200, max_pages=50) -> Optional[dict]
POST   /users/{id}/notify                                notify_user(user_id, text, channels=None, email_subject=None, email_html=None) -> dict
PATCH  /users/{id}                                       update_user(user_id, data) -> dict
POST   /users/{id}/balance                               modify_balance(user_id, data) -> dict
GET    /subscriptions                                    list_subscriptions(limit=20, offset=0, **filters) -> dict
GET    /subscriptions/{id}                               get_subscription(sub_id) -> dict
POST   /users/{id}/subscription                          create_subscription(user_id, data) -> dict
DELETE /users/{id}/subscription                          deactivate_subscription(user_id) -> dict
POST   /subscriptions/{id}/extend                        extend_subscription(sub_id, data) -> dict
POST   /subscriptions/{id}/traffic                       add_traffic(sub_id, data) -> dict
POST   /subscriptions/{id}/devices                       add_devices(sub_id, data) -> dict
GET    /users                                           get_all_users(limit=200, offset=0) -> dict
GET    /transactions                                    list_transactions(limit=20, offset=0, **filters) -> dict
GET    /tickets                                         list_tickets(limit=50, offset=0, **filters) -> list
GET    /tickets/{id}                                    get_ticket(ticket_id) -> dict
POST   /tickets/{id}/reply                              reply_ticket(ticket_id, message_text, media_type=None, media_file_id=None) -> dict
POST   /upload                                          upload_media(content, filename, media_type="document") -> dict
POST   /tickets/{id}/status                             set_ticket_status(ticket_id, status) -> dict
POST   /tickets/{id}/priority                           set_ticket_priority(ticket_id, priority) -> dict
GET    /media/{file_id}                                 download_media(file_id) -> bytes
GET    /tickets/{id}/messages/{mid}/media               get_ticket_message_media(ticket_id, message_id) -> dict
GET    /users/{id}/activity                             get_user_activity(user_id, limit=50, offset=0, types=None) -> dict
GET    /notifications/subscriptions                     list_subscription_events(limit=20, offset=0, event_types=None) -> dict
GET    /promo-codes                                     list_promos(limit=20, offset=0, **filters) -> dict
GET    /promo-codes/{id}                                get_promo(promo_id) / get_promo_stats(promo_id) -> dict
POST   /promo-codes                                     create_promo(data) -> dict
PATCH  /promo-codes/{id}                                update_promo(promo_id, data) -> dict
DELETE /promo-codes/{id}                                delete_promo(promo_id) -> dict
GET    /campaigns                                       list_campaigns(limit=20, offset=0, **filters) -> dict
POST   /campaigns                                       create_campaign(data) -> dict
PATCH  /campaigns/{id}                                  update_campaign(campaign_id, data) -> dict
DELETE /campaigns/{id}                                  delete_campaign(campaign_id) -> dict
GET    /partners/referrers                              list_partners(limit=20, offset=0, **filters) -> dict
GET    /partners/referrers/{user_id}                    get_partner(user_id) -> dict
PATCH  /partners/referrers/{id}/commission              update_partner_commission(user_id, data) -> dict
GET    /partners/stats                                  get_partner_global_stats() -> dict
GET    /partners/stats/top-referrers                    get_partner_top_referrers() -> dict
GET    /broadcasts                                      list_broadcasts(limit=20, offset=0, **filters) -> dict
POST   /broadcasts                                      create_broadcast(data) -> dict
POST   /broadcasts/{id}/stop                            stop_broadcast(broadcast_id) -> dict
```

## `core/settings_values.py`

```python
async def stored_merged(db: AsyncSession) -> dict[str, str]
    # SELECT setting_key, setting_value из settings + fin_settings; setdefault
    # отсутствующая таблица (UndefinedTableError / "does not exist") — пустая, warning один раз;
    # остальные ProgrammingError пробрасываются
def resolve_with_source(defn: SettingDef, db_value: str | None) -> tuple[str, str]
    # (value, source) по тем же приоритетам, что settings_registry.resolve:
    # fin_settings -> env→db→default; иначе db→env→default
async def effective_values(db: AsyncSession, keys: Iterable[str]) -> dict[str, str]
    # эффективные значения с расшифровкой is_secret (crypto.decrypt)
```

## `core/outbound_proxy.py`

```python
GLOBAL_ID = "global"
MODES = ("inherit", "direct", "custom")
SUPPORTED_SCHEMES = ("http", "https", "socks5", "socks5h")

@dataclass(frozen=True)
class ProxyResolution:
    integration: str; mode: str; effective: str; url: str; no_proxy: str; source: str

def validate_proxy_url(url: str) -> str | None       # None = валидно, строка = ошибка
def parse_no_proxy(raw: str) -> tuple[str, ...]
def host_bypassed(host: str, no_proxy: tuple[str, ...] | str) -> bool
def redact_url(url: str) -> str                      # убирает userinfo
def client_kwargs(resolution: ProxyResolution, target_host: str | None) -> dict
    # всегда {"trust_env": False}; + {"proxy": url}, если proxy применим
async def resolve_proxy(db, integration: str) -> ProxyResolution
    # inherit -> глобальный URL; direct -> без прокси; custom -> свой URL;
    # no_proxy: свой, иначе глобальный; CIDR не поддерживается
```

## `core/integrations.py`

```python
@dataclass(frozen=True)
class IntegrationDef: id: str; label: str; category: str; proxy_supported: bool;
                      proxy_target_host: str | None; keys: tuple[str, ...]
INTEGRATIONS: tuple[IntegrationDef, ...]             # bedolaga/support/bot_db/platega/yookassa
INTEGRATIONS_BY_ID: dict[str, IntegrationDef]

async def effective(db, integration_id) -> dict[str, str]
async def test_connection(db, integration_id, *, overrides=None, transport=None) -> dict
    # data-словарь §5.1 спеки; ошибки подключения -> ok:false, HTTP 200
    # support/getMe: top-level bot_username (@username или None) + details.bot_username на успехе
async def apply_bedolaga(db=None) -> bool            # configure; disabled -> disable(), пустой URL/токен -> reset()
async def reload_support(app, db=None) -> str        # in-place reload каналов
async def _refresh_bot_db(db=None) -> bool
async def on_settings_changed(app, db, keys) -> dict # runtime + warnings, не бросает;
                                                     # Bedolaga/Bot DB-ключи инвалидируют снимок аналитики
async def bootstrap(app) -> dict                     # старт: отдельная сессия + try/except на каждую интеграцию
                                                     # ("applied|skipped|error", <name>_error=ExcName);
                                                     # всегда инвалидирует снимок аналитики
BEDOLAGA_TRIGGER_KEYS / SUPPORT_TRIGGER_KEYS / BOT_DB_TRIGGER_KEYS
```

## Support: настройки и runtime

```python
# core/support/settings.py
SUPPORT_OVERRIDES: dict[str, tuple[str, str]]        # registry key -> (field|runtime|tri, target)
async def load_support_config(db=None) -> tuple[SupportSettings, dict[str, str]]
    # env → legacy support_setting → registry (support_*)
# core/support/__init__.py
async def init_support(existing: SupportService | None = None, db: Any = None) -> SupportService
    # existing -> in-place reload: store/outbox/event_bus сохраняются
# core/support/tg/api.py
TelegramClient(token, *, api_url=API_URL, http_client=None, proxy_kwargs=None)
    # owned httpx.AsyncClient(timeout, trust_env=False, **proxy_kwargs)
TelegramConflict(TelegramAPIError)                   # HTTP 409 / error_code=409 на getUpdates
# core/support/tg/poller.py
# tick: TelegramConflict → last_error="conflict", publish status, raise (offset не двигается)
# run_loop: TelegramConflict → один logger.error + sleep(300), цикл жив (без минутного спама)
# /start в личке: record_inbound(text="/start") → MESSAGE_CREATED + ensure_topic →
#   sendMessage(GREETING) → record_outbound(author="bot"); только при message_created=true,
#   ошибка отправки → logger.warning (тик живёт)
# /myid в личке: sendMessage("Ваш Telegram ID: <id>"), диалог/сообщения не создаются
GREETING = DEFAULT_TG_GREETING          # core/support/defaults.py — дефолт
# TelegramPoller(greeting=settings.tg_greeting) — текст из настройки support_tg_greeting
# (textarea, env SUPPORT_TG_GREETING, hot reload через SUPPORT_TRIGGER_KEYS)
# init_support: service.upload_max_size = settings.media_max_mb * 1024 * 1024
#   support_media_max_mb (number, 1..50, default 8, env SUPPORT_MEDIA_MAX_MB, hot reload)
#   -> web-upload 413 FILE_TOO_LARGE; poller/forum получают лимит через service.upload_max_size
# core/support/schema.py
ensure_support_schema()  # применяет по порядку 004-support-foundation.sql, 005-support-reply-idempotency.sql,
                         # 006-support-ai-kb.sql, затем idempotent ALTER: support_message.author CHECK расширен
                         # до client|agent|system|bot (приветствие /start). Отсутствие 005/006 логируется и
                         # пропускается; 004 обязательна.
                         # 005-support-reply-idempotency.sql: support_reply_key(actor_id BIGINT, conversation_id BIGINT,
                         #   client_msg_id TEXT, message_id BIGINT, created_at TIMESTAMPTZ; PK(actor_id,conversation_id,client_msg_id);
                         #   FK conversation/message ON DELETE CASCADE; idx_support_reply_key_message(message_id))
                         # 006-support-ai-kb.sql: KB/suggestion/qa_pair/operator_draft/candidate/job поля, partial unique
                         #   uq_support_ai_suggestion_pending(conversation_id) WHERE status='pending'
                         # 008-support-stage-c.sql (Этап C): support_message.author_id, support_template.category/created_by/
                         #   updated_at, support_sla_event(id,conversation_id,kind,due_at,breached_at,notified_at,closed_at;
                         #   UNIQUE(conversation_id,kind); partial idx due WHERE notified_at IS NULL AND closed_at IS NULL)

# core/support/store/conversations.py
async def record_inbound(..., is_backfill: bool = False)
    # is_backfill: unread не растёт, last_inbound_at не двигается
async def record_outbound(..., is_backfill: bool = False) -> int
    # INSERT support_message.is_backfill; при True first_response_at не пишется,
    # last_message_at = GREATEST(last_message_at, :ts); last_inbound_at не трогается
async def fill_conversation_mapping(db, conversation_id, *, tg_user_id=None, source_id=None) -> bool
    # заполняет только NULL (COALESCE), не перетирает значения живого канала

# tools/support_import_history.py — mapping-only импорт 24 пар legacy topics.json
python tools/support_import_history.py --topics <path> [--dry-run|--apply] [--limit N]
    # dry-run по умолчанию; channel='telegram', external_id=str(userId), source_id=str(topicId),
    # tg_user_id=userId, created -> status='closed'; тела не пишутся, Outbox не используется;
    # повторный --apply идемпотентен (UNIQUE(channel, external_id), 0 create)

# tools/tgexport_html_parse.py — dev-парсер Telegram Desktop HTML-экспорта (bs4, вне runtime)
python tools/tgexport_html_parse.py --dir ChatExport_... --out _tgexport_normalized.json
    # messages.html → messages2.html → messages3.html; темы из `created topic «…»`,
    # forwarded=клиент, plain=оператор, joined наследует отправителя; фото/видео href
# tools/support_import_tgexport.py — импорт тел/медиа в support_message/support_attachment
python tools/support_import_tgexport.py --input <json> --media-root <dir> [--dry-run|--apply]
    # is_backfill=True: без Outbox/уведомлений/unread/SLA/first_response; dedup по
    # (conversation_id, external_msg_id); медиа копируется в upload_dir/support/exp_<sha>.<ext>
```

## Support: ИИ-ядро и store (Этап B, B1b-2a)

```python
# core/support/ai/provider.py
ProviderError(RuntimeError)                      # .status/.code/.model; текст и repr без api_key
AiCompletion(draft, model, tokens_in, tokens_out, latency_ms)   # __getitem__/get/as_dict
AiProvider(*, transport=None, sleep=None)        # ленивый httpx.AsyncClient(trust_env=False)
    async complete_json(messages, config: AiConfig) -> AiCompletion
    # 429 → 1 retry по Retry-After; 5xx/таймаут → 1 retry; затем fallback_model;
    # 401/403 → dead до reset(); response_format=json_object, temperature/max_tokens из AiConfig
    reset() / mark_dead() / aclose(); свойства has_client, dead
# core/support/ai/prompt.py
DRAFT_SCHEMA = '{"reply":"","operator_note":"","reason":"","needs_human":false,"no_request":false,"clarify":false,"used":[],"confidence":0.0}'
build_system_prompt(config, *, links=None) -> str
build_user_prompt(*, config, kb_chunks=(), examples=(), messages=(), customer_card=None,
                  client_text="", messages_newest_first=True, links=None) -> tuple[str, tuple[Citation, ...]]
build_prompt(**same) -> PromptBundle(system, user, messages, citations, draft_schema)
    # scrub переписки/примеров/вопроса; KB [1]..[n]; безопасная карточка (SAFE_CARD_FIELDS)
# core/support/store/ai.py  (raw SQL, без commit)
create_suggestion / get_suggestion / get_pending_suggestion / list_suggestions
decide_suggestion / mark_suggestion_sent / supersede_pending
ai_replies_since / last_human_reply_at / human_hold_active
assistant_stats / list_activity
get_pause / set_pause / clear_pause               # support_setting['aiPause'], ≤ +31 день
get_operator_draft / put_operator_draft / delete_operator_draft
# core/support/kb/fts.py  (чистые функции, без I/O)
build_query(q) -> str                            # NFKC, control chars→space, ≤200; кавычки/|/: сохраняются для websearch
doc_tsvector_sql(alias="") / search_predicate(alias="", param="q") / rank_sql(alias="", param="q")
slugify(title) -> str                            # RU→EN транслит, [a-z0-9-], ≤80, fallback "article"
# core/support/ai/examples.py  (примеры манеры оператора)
MAX_EXAMPLE_CHARS=600 / MAX_EXAMPLES_CHARS=900 / EXAMPLES_LIMIT=3
render_examples(examples) -> str                 # scrub + clip каждой пары, весь блок ≤900
similar_examples(store, query, *, limit=3, exclude_conversation_id=None)  # обёртка над store, ошибки → []
store_examples(store) -> async search            # привязка для AiRuntime.examples
# core/support/ai/chunks.py
KbChunk(title, body, rank, position, score, section=None, doc_id=None)  # doc_id → used[].doc_id
# core/support/ai/public.py  (публичная форма предложки; без I/O, один источник истины)
used_items(raw) -> [{doc_id:int|null,title}]        # из JSONB used; chunk отбрасывается, doc_id → int|None
level(suggestion, config) -> 'sure'|'check'|'unsure'  # confidence_level от min_confidence
public_suggestion(suggestion, config) -> {id,conversation_id,message_id,text,final_text,operator_note,
                                          confidence,level,used,reason,gate{action,reason},model,status,created_at}
config_for(service) -> AiConfig                     # runtime.config, иначе AiConfig.from_settings(service.settings)
                                                    # используется в api/v1/support/{suggestions,conversations}.py
# core/support/store/qa.py  (raw SQL, без commit)
normalize(text) / external_key(question, answer) # lower, ё→е, пунктуация/пробелы, сортировка слов; sha256(q \x1f a)
clean_example(text, max=600) / is_meaningful(text)  # scrub, [номер], filler «ок/спасибо» отбрасывается
add_qa_pair(db, question, answer, source='operator', conversation_id?, external_key?) -> int|None
                                                 # ON CONFLICT (external_key) DO NOTHING; дубль/мусор -> None
add_qa_pairs(db, pairs, source='import') -> (created:int, duplicates:int)
                                                 # батч в одной транзакции; пары dict{question,answer} или tuple; мусор не считается дублем
similar_examples(db, query, limit=3) -> [{id,question,answer,rank}]  # FTS russian + ts_rank_cd, каждая ≤600
get_message(db, id) / last_inbound_before(db, conversation_id, message_id)
# core/support/store/jobs.py  (raw SQL, без commit)
JobsError / JobBusy(kind)                        # активный queued|running того же kind -> JobBusy
create_job(db, *, kind, payload?, created_by?, total?) -> job  # app-проверка + uq_support_job_active ловит гонку
get_job(db, id) -> job|None
claim_job(db, id) -> job|None                    # queued -> running + started_at, иначе None
update_job(db, id, *, progress?, total?, result?, error?) -> job|None
finish_job(db, id, *, status='done'|'error', result?, error?) -> job|None  # + finished_at
cancel_job(db, id) -> job|None                   # active -> status='error', error='cancelled'; иначе текущее состояние
# core/support/store/sla.py  (raw SQL, без commit; Этап C, C2)
list_policies(db) / get_policy(db, name) / update_policy(db, name, first_response_minutes, resolution_minutes)
sync_events(db, *, now=None) -> int              # upsert first_response|resolution по priority; due=first_inbound_at+N мин;
                                                 # reopen: closed_at=NULL, notified_at/breached_at=NULL если due изменился
                                                 # ИЛИ событие было closed_at IS NOT NULL; закрывает resolved/closed и
                                                 # first_response при first_response_at IS NOT NULL; вернуть active count
claim_due_alerts(db, *, limit=5) -> [alert]      # UPDATE … FOR UPDATE SKIP LOCKED; notified_at=now() (ровно один раз);
                                                 # alert={id,conversation_id,kind,due_at,overdue_minutes}
list_overview(db) -> [event]                     # closed_at IS NULL и due_at <= now()+1h; join conversation; overdue_minutes
count_breaches(db) -> {first_response:int, resolution:int}  # breached_at IS NOT NULL AND closed_at IS NULL
# SupportStore: list_policies/get_policy/update_policy/sync_events(now?)/claim_due_alerts(limit=5)/sla_overview/count_breaches
# core/support/sla.py
SlaWatcher(service, *, interval=60, batch=5)     # run_loop: sleep → pass_once; исключения логируются; stop() идемпотентен
pass_once(now=None) -> int                        # sync_events → claim_due_alerts(limit=batch) → SLA_ALERT + staff TG + audit
                                                 # текст staff: «⏰ SLA: диалог #ID, <kind>, просрочка N мин, приоритет X»
# core/support/workers.py: start_support_workers добавляет _sla_loop (интервал 60 с); watcher → service.sla_watcher
# core/support/imports/*  (каталог назван imports: `import` — зарезервированное слово Python,
#                           обычный `from ... import ...` с таким пакетом невозможен)
# imports/errors.py
ImportParseError(ValueError)                     # → IMPORT_PARSE_FAILED / 422-семантика
ImportTooLarge(ValueError)                       # → IMPORT_TOO_LARGE / 413
# imports/tg_text.py  (чистые функции, парсинг в to_thread)
DEFAULT_OPERATOR_NAMES = ('Поддержка HexaVeil','Поддержка','Support','HexaVeil','Администратор')
HEADER_RE / decode_bytes(bytes)                  # utf-8-sig → cp1251 → ImportParseError
check_text_size(text) / parse_text(text|bytes, operator_names?) -> [messages]
build_pairs(messages, max_side=3) -> [{question,answer,messages}]
parse_pairs(text|bytes, operator_names?) -> (messages, pairs)
# imports/tg_json.py
check_json_size(payload) / parse_json(payload:str|bytes|dict, operator_names?) -> [messages]
                                                 # messages[]; type!='message' пропуск; text строка|массив строк/объектов;
                                                 # date ISO иначе date_unixtime; битый JSON → ImportParseError(line/column/char)
build_pairs(messages) -> [{question,answer,messages}]  # reply_to_message_id приоритетом, иначе чередование from_id
parse_pairs(payload, operator_names?) -> (messages, pairs)
# imports/cluster.py  (чистые функции)
RU_STOPWORDS / normalize(text) / tokenize(text) / topic_for(question) -> 'tok1-tok2-tok3'|None
build_candidates(pairs, *, limit=200, min_group_size=2) -> [{topic,question,answer,occurrences}]
                                                 # топ-3 токена (частота, затем алфавит), группы ≥2, сортировка occurrences desc
# imports/runner.py
JOB_KIND='kb_import' / BATCH_SIZE=500 / TIME_BUDGET_SECONDS=120
check_size(kind, text?, payload?)                # 20 MiB текст / 50 MiB JSON до создания джоба
run_job(service, job_id) -> result|None          # claim → to_thread(parse) → батчи 500 → кандидаты → finish; отмена/дедлайн
spawn(service, job_id) -> asyncio.Task           # задача трекается в service.import_tasks
result: {questions,pairs_created,skipped_duplicates,candidates_created,errors[]}; dry_run: +would_create/would_skip/would_create_candidates
# core/support/store/kb.py  (raw SQL, без commit)
create_doc / get_doc / update_doc / publish_doc / archive_doc / restore_doc / delete_doc
list_docs(*, status=None|'all'|draft|published|archived, q, page, per_page)  # None -> published
search_docs(query, *, limit)                     # только published, ts_rank_cd, snippet ≤300
get_published_context(query, *, limit=8)         # published статьи для ИИ: doc_id,title,body,rank
list_candidates / decide_candidate(accept → draft source='candidate' + doc_id)
create_candidate(*, question, answer, source='feedback', topic?, title?, file_name?) -> int
                                                 # upsert по topic WHERE status='new', occurrences++
# SupportStore: те же методы-обёртки через open_session(); AiRuntime.kb_search = store.get_published_context,
#               AiRuntime.examples = store_examples(store) → store.similar_examples
# SupportStore (B2c): add_qa_pairs_batch(pairs, source='import') -> (created, duplicates);
#                     create_job/get_job/claim_job/update_job/finish_job/cancel_job — обёртки store/jobs.py;
#                     SupportService.import_tasks: set[asyncio.Task] — активные задачи импорта
```

## `core/errors.py`

```python
class ErrorCode(str, Enum): INVALID_CREDENTIALS, TOKEN_REQUIRED, INVALID_TOKEN, TOKEN_EXPIRED, FORBIDDEN,
  ACCOUNT_DISABLED, NOT_FOUND, ALREADY_EXISTS, CREATE_FAILED, UPDATE_FAILED, DELETE_FAILED, INVALID_INPUT,
  VALIDATION_ERROR, UPLOAD_FAILED, FILE_TOO_LARGE, INVALID_FILE_TYPE, DB_ERROR, DB_CONNECTION_FAILED,
  REPLY_WINDOW_CLOSED, CLIENT_WROTE, LOCKED_BY_OTHER,
  AI_DISABLED, AI_PAUSED, AI_KEY_MISSING, AI_UPSTREAM_ERROR, PROVIDER_ERROR,
  KB_VERSION_CONFLICT, KB_DOC_PUBLISHED, IMPORT_TOO_LARGE, IMPORT_PARSE_FAILED, JOB_BUSY,
  TEMPLATE_EXISTS, SLA_POLICY_NOT_FOUND, NOTE_NOT_FOUND,
  INTERNAL_ERROR, NOT_IMPLEMENTED, RATE_LIMITED     # каждый member = собственное имя
E = ErrorCode
def api_error(status_code: int, code: ErrorCode, detail: Optional[str] = None) -> JSONResponse   # ERR
def api_raise(status_code: int, code: ErrorCode, detail: Optional[str] = None) -> NoReturn        # HTTPException(detail=ERR)
```

## `core/config.py`

```python
class CmsSettings(BaseSettings):   # env_file=".env", populate_by_name=True, extra="ignore"
  debug: bool = False                     # APP_DEBUG
  host: str = "0.0.0.0"                   # API_HOST
  port: int = 8000                        # API_PORT
  db_driver: str = "pgsql"                # DB_DRIVER
  db_host: str = "db"                     # DB_HOST
  db_port: int = 5432                     # DB_PORT
  db_name: str = "cms"                    # DB_NAME
  db_user: str = "cms"                    # DB_USER
  db_pass: str = "cms_secret_2026"        # DB_PASS
  jwt_secret: str = ""                    # JWT_SECRET
  encryption_key: str = ""                # APP_ENCRYPTION_KEY
  jwt_algorithm: str = "HS256"            # JWT_ALGORITHM
  jwt_ttl: int = 86400                    # JWT_TTL
  bedolaga_api_url: str = ""              # BEDOLAGA_API_URL
  bedolaga_api_token: str = ""            # BEDOLAGA_API_TOKEN
  bot_db_host: str = ""                   # BOT_DB_HOST
  bot_db_port: int = 5434                 # BOT_DB_PORT
  bot_db_name: str = "remnawave_bot"      # BOT_DB_NAME
  bot_db_user: str = "cms_ro"             # BOT_DB_USER
  bot_db_pass: str = ""                    # BOT_DB_PASS
  app_encryption_key: str = ""            # APP_ENCRYPTION_KEY (тот же env, что encryption_key)
  cors_origins_raw: str = "http://localhost:3000,http://localhost:5173,http://localhost"  # CORS_ORIGINS
  upload_dir: str = "/var/www/html/public/uploads"  # UPLOAD_DIR
  public_dir: str = "/var/www/html/public"          # PUBLIC_DIR
  root_path: str = "/var/www/html"                  # ROOT_PATH
  max_upload_size: int = 67108864                   # MAX_UPLOAD_SIZE (64 MiB)
  property database_url -> str          # postgresql+asyncpg://{user}:{pass}@{host}:{port}/{name}
  property jwt_secret_resolved -> str   # jwt_secret | encryption_key | "hexaveil-cms-default-jwt-secret-change-in-production"
  property bot_database_url -> str      # "" если bot_db_host пуст
  property cors_origins -> list[str]
@lru_cache
def get_cms_settings() -> CmsSettings
```

---

# 3. Frontend API Clients & Services (TypeScript)

## 3.1 `src/api/client.ts`

```ts
const API_BASE = import.meta.env.VITE_API_URL ?? '/api'
export const api = axios.create({ baseURL: API_BASE, headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' } })
export default api
```
- Request interceptor: `localStorage['auth-store']` → `parsed.state.token` → `Authorization: Bearer <token>`.
- Response interceptor: `401` → удалить `auth-store`, `window.location.href='/admin/login'`, `Promise.reject(error)`.
- **Нет** класса `ApiError`; ошибки — сырой `AxiosError`.
- `diagnostics.ts`, `finance.ts`, `preferences.ts` создают собственный `axios.create({ baseURL: '' })` с теми же интерцепторами.

## 3.2 `auth.ts`

```ts
interface LoginResponse { success: boolean; token: string; error?: string; user: { id:number; login:string; email:string; role:string } }
authApi.login(login: string, password: string): Promise<LoginResponse>          // POST /api/auth/login
authApi.me(): Promise<{ success: boolean; user: LoginResponse['user'] }>          // GET  /api/auth/me
authApi.changePassword(current_password: string, new_password: string): Promise<{ success: boolean; error?: string }> // POST /api/auth/change-password
```

## 3.3 `posts.ts`

```ts
interface Post { id:number; title:string; slug:string; content:string; excerpt?:string; status:'draft'|'published'|'archived';
  category_id?:number; category_name?:string; image?:string; user_id?:number; author_name?:string; views?:number;
  seo_title?:string|null; seo_description?:string|null; canonical?:string|null; featured?:boolean;
  comments_enabled?:boolean; tags?:string[]; created_at:string; updated_at:string }
postsApi.list(params?: { page?:number; per_page?:number; sort?:string; dir?:string; search?:string }): P  // GET /api/posts
postsApi.get(id:number): P                        // GET /api/posts/{id}
postsApi.create(data: Partial<Post>): P           // POST /api/posts
postsApi.update(id:number, data: Partial<Post>): P// POST /api/posts/{id}
postsApi.delete(id:number): P                     // DELETE /api/posts/{id}
```

## 3.4 `categories.ts`

```ts
interface Category { id:number; name:string; slug:string; description?:string; parent_id?:number }
categoriesApi.list(): P                                   // GET /api/categories
categoriesApi.get(id:number): P                           // GET /api/categories/{id}  ⚠ эндпоинта нет
categoriesApi.create(data: Partial<Category>): P          // POST /api/categories
categoriesApi.update(id:number, data: Partial<Category>): P // POST /api/categories/{id}
categoriesApi.delete(id:number): P                        // DELETE /api/categories/{id}
```

## 3.5 `pages.ts`

```ts
interface Page { id:number; title:string; slug:string; content:string; meta_description?:string; status:string;
  template?:string; is_home?:number; created_at:string; updated_at?:string }
pagesApi.list(): P; get(id): P; create(Partial<Page>): P; update(id, Partial<Page>): P; delete(id): P
// GET /api/pages | GET /api/pages/{id} | POST /api/pages | POST /api/pages/{id} | DELETE /api/pages/{id}
```

## 3.6 `users.ts`

```ts
interface User { id:number; login:string; email:string; role:'admin'|'editor'|'author'; display_name?:string|null;
  status:'active'|'inactive'|'banned'; avatar_url?:string|null; bio?:string|null; phone?:string|null;
  telegram?:string|null; website?:string|null; location?:string|null; posts_count?:number; comments_count?:number;
  created_at:string; updated_at:string }
interface UserPayload { login:string; email?:string; role?:string; display_name?:string; status?:string; avatar_url?:string;
  bio?:string; phone?:string; telegram?:string; website?:string; location?:string; password?:string }
usersApi.list(): P; get(id): P; create(UserPayload): P; update(id, UserPayload): P; delete(id): P; uploadAvatar(file: File): P
// GET /api/users | GET /api/users/{id} | POST /api/users | POST /api/users/{id} | DELETE /api/users/{id} | POST /api/users/avatar
```

## 3.7 `menus.ts` / `widgets.ts`

```ts
interface MenuItem { id:number; name:string; url:string; location:string }
menusApi.list(): P; get(id): P; create(Partial<MenuItem>): P; update(id, Partial<MenuItem>): P; delete(id): P

interface Widget { id:number; area:string; title:string; content:string; sort_order:number; created_at:string }
widgetsApi.list(): P; get(id): P; create(Partial<Widget>): P; update(id, Partial<Widget>): P; delete(id): P
```

## 3.8 `media.ts`

```ts
interface MediaItem { path:string; url:string; name:string; size:number; modified:number }
mediaApi.list(): P                                      // GET /api/media
mediaApi.upload(formData: FormData): P                  // POST /api/media/upload
mediaApi.delete(path: string): P                        // POST /api/media/delete {path}
```

## 3.9 `settings.ts`

```ts
interface RegistryItem { key:string; label:string; description:string; category:string; tab:string;
  type:'text'|'textarea'|'number'|'bool'|'select'|'secret'|'json'; default:string; value:string;
  source:'db'|'env'|'default'; is_set:boolean; store:string; options:string[]|null; options_source:string|null;
  is_secret:boolean; is_readonly:boolean; is_env_override:boolean; env_var_name:string|null; sort_order:number }
interface SettingsResponse { success:boolean; data:Record<string,string>; items:RegistryItem[]; categories:Record<string,RegistryItem[]> }
interface RegistryItemResponse { success:boolean; data?:RegistryItem }
settingsApi.getAll(): Promise<SettingsResponse>                       // GET /api/settings
settingsApi.update(data: Record<string,string>): P                    // POST /api/settings
settingsApi.setKey(key: string, value: string): Promise<RegistryItemResponse>  // PUT /api/settings/{key}
settingsApi.resetKey(key: string): Promise<RegistryItemResponse>      // DELETE /api/settings/{key}
settingsApi.testIntegration(id: string, body?: Record<string,string>): Promise<TestEnvelope<IntegrationTestResult>>
                                                                      // POST /api/settings/integrations/{id}/test
settingsApi.testProxy(body?: Record<string,string>): Promise<TestEnvelope<ProxyTestResult>>
                                                                      // POST /api/settings/integrations/proxy/test
# типы: ProxyInfo{mode,effective,url,applied,no_proxy?}, IntegrationTestResult{id,ok,status,message,
#       elapsed_ms,egress_ip?,bot_username?,proxy,details?}, ProxyTestResult{ok,status,message,egress_ip?,
#       http_status?,elapsed_ms,test_url?,proxy{mode,url,applied}}
```

## 3.10 `themes.ts`

```ts
interface ThemeListItem { value:string; label:string }
interface ThemeOption { label:string; type:string; default:string; value:string; hint?:string; rows?:number; options?:Record<string,string> }
interface ThemeGroup { name:string; options:Record<string,ThemeOption> }
interface ThemeSettingsResponse { success:boolean; data:{ theme:string; label:string; options:Record<string,ThemeOption>; groups:ThemeGroup[] } }
themesApi.list(): Promise<{success:boolean;data:ThemeListItem[]}>       // GET /api/themes
themesApi.getSettings(): Promise<ThemeSettingsResponse>                // GET /api/themes/settings
themesApi.updateSettings(data: Record<string,string>): P               // POST /api/themes/settings
```

## 3.11 `logs.ts`

```ts
interface LogEntry { id:number; level:string; category?:string; channel:string; source?:string; message:string; context?:string; created_at:string }
logsApi.list(params?: { level?:string; category?:string; categories?:string; channel?:string; source?:string; q?:string;
  days?:number; page?:number; per_page?:number }): P                    // GET /api/logs
logsApi.clear(data?: { category?:string; categories?:string[]; channel?:string }): P // POST /api/logs/clear
```

## 3.12 `dashboard.ts` / `public.ts` / `preferences.ts` / `diagnostics.ts`

```ts
interface DashboardStats { posts:number; comments:number; users:number; categories:number; posts_published:number;
  posts_draft:number; comments_total:number; comments_approved:number; users_active:number }
dashboardApi.getStats(): Promise<{ success:boolean; stats:DashboardStats }>   // GET /api/dashboard/stats

interface Branding { site_name:string; admin_title:string; browser_title:string; title_separator:string; favicon_url:string }
publicApi.getBranding(): Promise<{ success:boolean; data:Branding }>          // GET /api/public/branding

interface PreferencesResponse { ok:boolean; data:Record<string,unknown> }
preferencesApi.getPreferences(): Promise<PreferencesResponse>                 // GET  /admin/settings/preferences
preferencesApi.savePreferences(data: Record<string,unknown>): Promise<{ok:boolean}> // POST /admin/settings/save-all-preferences

interface PingEntry { ms:number|null; loss:number|null }
interface NodeTCP { retrans_pct?:number|null; timeouts?:number; in_segs?:number; out_segs?:number }
interface NodeNetworkErrors { rx_err?:number; tx_err?:number }
interface NodeLoad { '1m'?:number; '5m'?:number; '15m'?:number }
interface NodeRAM { used?:string; total?:string }
interface NodeDisk { used?:string; total?:string; pct?:string }
interface NodeDockerContainer { name:string }
interface NodeNginx { status?:string; error?:string }
interface NodeCert { [key:string]: unknown }
interface NodeData { hostname?:string; uptime?:string; cpu_cores?:number; load?:NodeLoad; ram?:NodeRAM; disk?:NodeDisk;
  docker?:NodeDockerContainer[]; nginx?:NodeNginx; speed_download_mbps?:number|null; tcp?:NodeTCP;
  network_errors?:NodeNetworkErrors; pings?:Record<string,PingEntry>; certs?:NodeCert[] }
interface Node { id:string; name:string; reachable:boolean; error?:string; data?:NodeData }
interface DiagnosticsSummary { total:number; reachable:number; unreachable:number; problems:number; avgLoad:number }
interface DiagnosticsData { success:boolean; collected_at:string|null; nodes:Node[]; summary:DiagnosticsSummary; is_collecting:boolean }
diagnosticsApi.getData(): Promise<DiagnosticsData>                            // GET  /admin/diagnostics/api/data
diagnosticsApi.collect(): Promise<{success:boolean;message?:string;error?:string}> // POST /admin/diagnostics/api/collect
```

## 3.13 `docs.ts`

```ts
interface DocInfo { name:string; title:string; editable:boolean }
interface DocContent { name:string; title:string; editable:boolean; raw:string; html:string; updated_at?:string|null }
interface DocumentPayload { raw:string; html:string; updated_at:string|null }
interface DocEntry { id:number; day_of_week?:string; date:string; time:string; author:string; title:string; body:string;
                     origin?:'manual'|'changelog'; source_changelog_id?:number|null }
interface EntriesResponse { success:boolean; data:{ name:string; title:string; editable:boolean; header:string;
                                                   document?:DocumentPayload; entries:DocEntry[] } }
interface UserName { id:number; username:string; display_name:string }
class DocsApiError extends Error { readonly status?:number; readonly code?:string }
docsApi.list(): Promise<{success:boolean;data:DocInfo[]}>                                  // GET /api/docs/list
docsApi.get(name:string): Promise<{success:boolean;data:DocContent}>                        // GET /api/docs/{name}
docsApi.getEntries(name:string): Promise<EntriesResponse>                                   // GET /api/docs/{name}/entries
docsApi.putDocument(name:string, content:string, expectedUpdatedAt?:string|null):
  Promise<{success:boolean;data:{updated_at:string|null}}>                                  // PUT /api/docs/{name} (history); 409 -> DocsApiError
docsApi.importDocument(name:string, file:File):
  Promise<{success:boolean;data:{updated_at:string|null;chars:number}}>                     // POST /api/docs/{name}/import (multipart)
docsApi.createEntry(name:string, data:{date,time,author,title,body,also_history?}): Promise<{success:boolean;data:{id:number}}>  // POST
docsApi.updateEntry(name:string, id:number, data:{date,time,author,title,body}): Promise<{success:boolean}> // PUT
docsApi.deleteEntry(name:string, id:number): Promise<{success:boolean}>                     // DELETE
docsApi.getUserNames(): Promise<{success:boolean;data:UserName[]}>                          // GET /api/users/names
docsApi.importFile(file:File): Promise<{success:boolean;data:{imported:number}}>            // POST /api/docs/changelog/import
docsApi.getExportUrl(name:string='changelog'): string                                       // '/api/docs/{name}/export'
```

`putDocument`/`importDocument` оборачивают ошибки в `DocsApiError` (`status`, `code`; для устаревшего `expected_updated_at` — 409/`CONFLICT`). Остальные методы пробрасывают ошибки axios как есть.

## 3.14 `finance.ts`

```ts
interface Transaction { id:number; date:string; date_display:string; month:string; type:'income'|'expense';
  participant:string; category:string; amount:number; description:string }
interface ChartPoint { key:string; label:string; income:number; expense:number; balance:number }
interface FinanceData { summary:{income,expense,balance,count};
  averages:{income,expense,balance,total,avg_days,avg_weeks,avg_months,avg_years,
            avg_income:{day,week,month,year}, avg_expense:{day,week,month,year}};
  chart:{daily:ChartPoint[]; weekly:ChartPoint[]; monthly:ChartPoint[]; yearly:ChartPoint[]};
  categories:{category:string;income:number;expense:number}[]; transactions:Transaction[];
  pagination:{page,per_page,total,pages}; settings:Record<string,unknown>; all_months:string[];
  all_categories:string[]; all_participants:string[]; anomalies:number[] }
interface PaymentPreviewRow { record_id:string; date:string; type:string; participant:string; category:string; amount:number;
  gross?:number; description:string; status:'new'|'duplicate'|'skipped'; method?:string; method_label?:string;
  commission_pct?:number|null }
interface PaymentSettings { last_sync:string; last_sync_ok:number; last_error:string; auto_sync:number; days_back:number; [k:string]:unknown }
interface PaymentImportResult { success:boolean; added?:number; skipped?:number; new?:number; error?:string }
interface SyncHistoryEntry { id:number; created_at:string; level:string; channel:string; message:string; category:string;
  source:string; context:{provider?,source?,ok?,added?,skipped?,new?,error?,duration_ms?,[k:string]:unknown}|null }
interface SyncProviderStatus { provider:string; configured:boolean; auto_sync:number; interval:number; last_sync:string;
  last_sync_ok:number; last_error:string; next_run:string|null; lock_active:boolean }

financeApi.getData(params?: Record<string,unknown>): Promise<FinanceData>       // GET /admin/finance/api/data
financeApi.add(data:{date,type,category,participant,amount,description}): P      // POST /admin/finance/api/add
financeApi.edit(data:{id,date,type,category,participant,amount,description}): P  // POST /admin/finance/api/edit
financeApi.delete(id:number): P                                                  // POST /admin/finance/api/delete {id}
financeApi.deleteBulk(ids:number[]): P                                           // POST /admin/finance/api/delete-bulk {ids}
financeApi.bulkType(ids:number[], value:string): P                                // POST /admin/finance/api/bulk/type {ids,type}
financeApi.bulkCategory(ids:number[], value:string): P                            // POST /admin/finance/api/bulk/category {ids,category}
financeApi.bulkParticipant(ids:number[], value:string): P                         // POST /admin/finance/api/bulk/participant {ids,participant}
financeApi.bulkDescription(ids:number[], value:string): P                         // POST /admin/finance/api/bulk/description {ids,description}
financeApi.exportCsv(params?: Record<string,unknown>): P                          // GET /admin/finance/api/export/csv (blob)
financeApi.exportSelected(ids:number[]): P                                        // POST /admin/finance/api/export/selected (blob)
financeApi.getSettings(): P                                                       // GET /admin/finance/api/settings
financeApi.saveSettings(data: Record<string,unknown>): P                          // POST /admin/finance/api/settings
financeApi.payments.platega  = paymentsProvider('platega')                        // /admin/finance/api/platega/*
financeApi.payments.yookassa = paymentsProvider('yookassa')                       // /admin/finance/api/yookassa/*

// paymentsProvider(base) — методы:
preview(body = {}): Promise<{success:boolean; transactions?:PaymentPreviewRow[]; error?:string}>   // POST /admin/finance/api/{base}/preview
import(transactions: (PaymentPreviewRow & {include:boolean})[]): Promise<PaymentImportResult>       // POST /admin/finance/api/{base}/import
sync(): Promise<PaymentImportResult>                                                               // POST /admin/finance/api/{base}/sync
settings(): Promise<PaymentSettings>                                                               // GET  /admin/finance/api/{base}/settings
saveSettings(body: Record<string,unknown>): P                                                      // POST /admin/finance/api/{base}/settings
history(limit = 10): Promise<{success:boolean; data:SyncHistoryEntry[]}>                            // GET /admin/finance/api/sync/history?provider={base}
status(): Promise<{success:boolean; providers:SyncProviderStatus[]}>                                // GET /admin/finance/api/sync/status
```

## 3.15 `bedolaga.ts`

```ts
interface BedolagaOverview { users?:{total?,active?,blocked?,balance_kopeks?,balance_rubles?};
  subscriptions?:{active?,expired?}; support?:{open_tickets?}; payments?:{today_rubles?,today_kopeks?} }
interface BedolagaFullStats { users?:{total_users?,active_users?,blocked_users?,new_today?,new_week?,new_month?};
  subscriptions?:{active_subscriptions?,trial_subscriptions?,paid_subscriptions?,trial_to_paid_conversion?,
                  trial_statistics?:{used_trials?,active_trials?,resettable_trials?}};
  transactions?:{totals?:{income_rubles?,expenses_rubles?,profit_rubles?,subscription_income_rubles?};
                 today?:{transactions_count?,income_rubles?};
                 by_type?:Record<string,{count?,amount?}>; by_payment_method?:Record<string,{count?,amount?}>};
  referrals?:{users_with_referrals?,active_referrers?,total_paid_rubles?,today_earnings_rubles?,
              week_earnings_rubles?,month_earnings_rubles?,
              top_referrers?:Array<{user_id?,display_name?,username?,total_earned_kopeks?,referrals_count?}>} }
interface BedolagaSubscription { id?:number; status?:string; actual_status?:string; start_date?:string; end_date?:string;
  is_trial?:boolean; tariff_id?:number|null; tariff_name?:string|null; autopay_enabled?:boolean;
  autopay_days_before?:number|null; autopay_period_days?:number|null; traffic_used_gb?:number; traffic_limit_gb?:number;
  device_count?:number; device_limit?:number; subscription_url?:string }
interface BedolagaUser { id:number; telegram_id?:number; username?:string; first_name?:string; last_name?:string;
  email?:string; status?:string; balance_kopeks?:number; balance_rubles?:number; created_at?:string; last_activity?:string;
  referral_code?:string; referred_by_id?:number; promo_group?:{id?,name?};
  tariff_id?:number|null; tariff_name?:string|null; tariff_missing?:boolean;   // §1.21 — нормализовано бэкендом
  subscription?:BedolagaSubscription }
interface BedolagaAnalyticsTariff { tariff_id:number|null; tariff_name:string; normalized_name:string; is_active:boolean;
  is_free:boolean; price_known:boolean; price_source:string; price_kind:string; confidence:string;
  period_prices?:Array<{days:number; price_kopeks:number; price_rubles:number}>;
  monthly_price_kopeks:number|null; monthly_price_rubles:number|null; price_per_day_kopeks:number|null; price_basis:string;
  clients_paid:number; clients_trial:number; clients_total:number; share_pct:number; mrr_kopeks:number;
  paid_forward_kopeks:number; next_month_expected_kopeks:number; unknown_price_clients:number }
interface BedolagaAnalyticsTariffs { currency:string; price_source_priority:string[];
  coverage:{users_total:number; clients_with_paid:number; active_paid_subscriptions:number; trial_subscriptions:number;
            clients_without_subscription:number; price_known_subscriptions:number; price_unknown_subscriptions:number;
            price_coverage_pct:number};
  items:BedolagaAnalyticsTariff[];
  totals:{clients_paid:number; clients_trial:number; clients_without_subscription:number; mrr_kopeks:number;
          mrr_basis:string; mrr_is_lower_bound:boolean; mrr_unknown_subscriptions:number; paid_forward_kopeks:number;
          next_month_expected_kopeks:number; unknown_price_clients:number};
  generated_at:string; as_of:string; partial:boolean; warnings:BedolagaAnalyticsWarning[]; sources:Record<string,unknown> }
interface BedolagaAnalyticsWarning { code:string; message:string; [key:string]:unknown }
interface BedolagaAnalyticsSources { bot_db?:{status?:string; checked_at?:string|null; tariffs?:number};
  transactions?:{status?:string; scanned?:number; named_price_samples?:number; total?:number};
  users?:{status?:string; loaded?:number; total?:number}; full_stats?:{status?:string} }
interface BedolagaAnalyticsOverviewTariff { tariff_id:number|null; tariff_name:string; clients_paid:number; clients_trial:number;
  share_pct:number; monthly_price_kopeks:number|null; price_source:string; price_kind:string; mrr_kopeks:number;
  paid_forward_kopeks:number; next_month_expected_kopeks:number; unknown_price_clients:number; is_free:boolean }
interface BedolagaAnalyticsOverviewKpis { mrr_kopeks:number; mrr_rubles:number; mrr_basis:string; mrr_is_lower_bound:boolean;
  mrr_unknown_subscriptions:number; cash_forecast_next_month_kopeks:number; cash_forecast_unknown_count:number;
  renewals_due_next_month_kopeks:number; renewals_due_next_month_count:number; paid_forward_kopeks:number;
  accrual_revenue_current_month_kopeks:number|null; accrual_unknown_subscriptions:number;
  accrual_revenue_month_kopeks:number|null; accrual_month_unknown_subscriptions:number;
  cash_received_current_month_kopeks:number; cash_received_month_kopeks:number; payments_current_month:number;
  active_paid_clients:number; active_paid_subscriptions:number; autopay_enabled_subscriptions:number }
interface BedolagaAnalyticsMonthlyPoint { month:string; cash_received_kopeks:number; cash_received_rubles:number;
  payments_count:number; unique_payers:number; renewal_payments:number; purchase_payments:number;
  renewal_proxy:number|null; avg_payment_kopeks:number|null; accrual_revenue_kopeks:number|null; accrual_is_estimate:boolean }
interface BedolagaAnalyticsOverview { month:string; next_month:string; basis:string; coverage:BedolagaAnalyticsCoverage;
  kpis:BedolagaAnalyticsOverviewKpis; by_tariff:BedolagaAnalyticsOverviewTariff[];
  monthly:BedolagaAnalyticsMonthlyPoint[]; generated_at:string; as_of:string; partial:boolean;
  warnings:BedolagaAnalyticsWarning[]; sources:BedolagaAnalyticsSources }
interface BedolagaAnalyticsForecastDay { date:string; expected_kopeks:number; payments_count:number }
interface BedolagaAnalyticsForecastTariff { tariff_id:number|null; tariff_name:string; expected_kopeks:number;
  payments_count:number; unknown_count:number }
interface BedolagaAnalyticsForecastItem { user_id:number|null; username:string; subscription_id:number|null;
  tariff_id:number|null; tariff_name:string; period_days:number; period_price_kopeks:number|null; end_date:string|null;
  expected_charge_date:string|null; autopay_enabled:boolean; autopay_days_before:number|null;
  amount_kopeks:number|null; price_known:boolean; price_source:string }
interface BedolagaAnalyticsForecast { month:string; basis:string;
  totals:{expected_kopeks:number; expected_rubles:number; payments_count:number; unknown_count:number;
          autopay_enabled_count:number};
  by_day:BedolagaAnalyticsForecastDay[]; by_tariff:BedolagaAnalyticsForecastTariff[];
  items:BedolagaAnalyticsForecastItem[]; items_total:number; generated_at:string; as_of:string;
  partial:boolean; warnings:BedolagaAnalyticsWarning[]; sources:BedolagaAnalyticsSources }
interface BedolagaAnalyticsCustomer { user:{id:number|null; username?:string|null; telegram_id?:number|null; first_name?:string|null};
  primary_subscription:{id:number|null; status?:string|null; actual_status?:string|null; is_trial:boolean;
    tariff_id:number|null; tariff_name:string; start_date:string|null; end_date:string|null; days_left:number;
    autopay_enabled:boolean; autopay_days_before:number|null; autopay_period_days:number|null; period_days:number}|null;
  tariff:{price_known:boolean; price_source:string; price_kind:string; price_basis:string; confidence:string; is_free:boolean;
    monthly_price_kopeks:number|null; monthly_price_rubles:number|null; monthly_basis:string; monthly_source:string;
    period_price_kopeks:number|null; period_price_rubles:number|null; period_basis:string; period_days:number;
    price_per_day_kopeks:number|null; samples:number; last_seen_at:string|null}|null;
  money:{paid_total_kopeks:number; paid_last_12m_kopeks:number; paid_current_month_kopeks:number;
    paid_forward_kopeks:number|null; next_payment_date:string|null; expected_charge_date:string|null;
    next_payment_kopeks:number|null; next_payment_known:boolean};
  subscriptions:Array<{id:number|null; tariff_id:number|null; tariff_name:string; end_date:string|null; is_trial:boolean;
    status?:string|null; actual_status?:string|null}>;
  payments:Array<{id:number|null; created_at:string|null; amount_kopeks:number|null; description?:string|null; type?:string|null}>;
  generated_at:string; as_of:string; partial:boolean; warnings:BedolagaAnalyticsWarning[]; sources:Record<string,unknown> }
// Все методы: Promise<any>; params: Record<string,string> -> URLSearchParams
// Исключение: getAnalyticsTariffs/getAnalyticsCustomer/getAnalyticsOverview/getAnalyticsForecast типизированы
// (Promise<BedolagaAnalytics*>), params — объект axios
bedolagaApi.getStatus() / getOverview() / getFull() / getHealth() / getCapabilities() / getMaintenance() / getTariffs()
bedolagaApi.listUsers(params) / getUser(id) / updateUser(id, data) / getUserByTelegram(tgId)
bedolagaApi.modifyBalance(userId, {amount_kopeks, reason?}) / createSubscription(userId, data) / deactivateSubscription(userId)
bedolagaApi.getSubscription(subId) / extendSubscription(subId, {days}) / addTraffic(subId, {traffic_gb})
bedolagaApi.addDevices(subId, {count}) / resetDevices(subId)
bedolagaApi.listTransactions(params) / getUserActivity(userId, params) / listEvents(params)
bedolagaApi.listPromos(params) / getPromo(id) / getPromoStats(id) / createPromo(data) / updatePromo(id, data) / deletePromo(id)
bedolagaApi.listCampaigns(params) / createCampaign(data) / updateCampaign(id, data) / deleteCampaign(id)
bedolagaApi.listBroadcasts(params) / createBroadcast(data) / stopBroadcast(id) / listPartners(params)
bedolagaApi.getReferralStats() / listReferrers(params) / getReferrerRefs(id)
bedolagaApi.getAnalyticsTariffs(params?) -> Promise<BedolagaAnalyticsTariffs>        // GET /api/bedolaga/analytics/tariffs
bedolagaApi.getAnalyticsCustomer(userId, params?) -> Promise<BedolagaAnalyticsCustomer> // GET /api/bedolaga/analytics/customers/{id}
bedolagaApi.getAnalyticsOverview(month?, basis='cash', months=6) -> Promise<BedolagaAnalyticsOverview> // GET /api/bedolaga/analytics/overview
bedolagaApi.getAnalyticsForecast(month?, basis='cash') -> Promise<BedolagaAnalyticsForecast> // GET /api/bedolaga/analytics/forecast
```

## 3.16 `support.ts`

```ts
type ConversationStatus = 'open'|'pending'|'resolved'|'closed'
type ConversationPriority = 'low'|'normal'|'high'|'urgent'
interface SupportConversation { id:number; channel:string; external_id:string; tg_user_id:number|null; source_id:string|null;
  status:ConversationStatus; priority:ConversationPriority; subject:string|null; assignee_id:number|null;
  claimed_at:string|null; first_inbound_at:string|null; last_inbound_at:string|null; first_response_at:string|null;
  last_message_at:string|null; unread:number; suspicious:boolean; sub_link:string|null;
  customer_profile_id:number|null; created_at:string; updated_at:string }
interface SupportMessage { id:number; conversation_id:number; direction:'in'|'out'; author:'client'|'agent'|'system'|'bot';
  text:string|null; media_type:string|null; media_file_id:string|null; external_msg_id:string|null;
  reply_to_external_id:string|null; reply_excerpt:string|null; is_backfill:boolean; created_at:string;
  attachment?:{ id:number; mime_type?:string|null; original_name?:string|null; size?:number|null; media_type?:string|null }|null }
interface SupportCustomerProfileBrief { id:number; identity_key:string; tg_user_id:number|null; username:string|null;
  display_name:string|null; email:string|null; phone:string|null }
interface SupportCustomerCard { provider:string; id:number|null; telegram_id:number|null; username:string; display_name:string;
  balance_kopeks:number|null; balance_rub:number|null;
  subscription:{status?:string; end_date?:string; is_trial?:boolean; tariff_name?:string|null;
    device_limit?:number|null; device_count?:number|null; subscription_url?:string|null;
    traffic_used_gb?:number|null; traffic_limit_gb?:number|null;
    traffic?:{used_bytes?:number|null; limit_bytes?:number|null}};
  tickets_total:number; last_activity:string|null; recent_transactions:number;
  remnawave:{available?:boolean; note?:string}; fetched_at:string }
interface SupportListResult { items:SupportConversation[]; total:number; page:number; per_page:number }
interface SupportConversationDetail { conversation:SupportConversation; messages:SupportMessage[]; customer:SupportCustomerProfileBrief|null;
  /** Последняя pending-предложка (публичная форма `core/support/ai/public.py`); shadow тоже приходит — скрывает фронт. */
  suggestion?:SupportAiSuggestion|null }
interface PollerStatus { enabled?:boolean; running?:boolean; last_poll?:string|null; last_offset?:number;
  last_error?:string|null; ingested?:number }
interface SupportPollersResult { pollers:Record<string,PollerStatus> }
interface SupportConfigStatus { channels:string[]; poll_interval_seconds:number; reply_window_hours:number;
  media_max_mb:number; upload_max_bytes?:number }
interface ListConversationParams { status?:string; channel?:string; priority?:string; assignee_id?:number; customer_id?:number;
  unread_only?:boolean; q?:string; page?:number; per_page?:number }
interface SupportUploadResult { token:string; media_type:string; mime_type:string; original_name:string; bytes:number; sha256:string }

interface ReplyPayload { text:string; attachment_ids?:string[]; client_msg_id?:string; force?:boolean }
interface ReplyResult { conversation_id:number; message_id?:number; external_msg_id?:string|null; message_ids?:number[];
  count?:number; repeated?:boolean }
interface StatePayload { status:ConversationStatus; priority?:ConversationPriority; seen_at?:string }
type PrioritySyncResult = 'synced'|'unchanged'|'skipped'|'error'
interface StateResult { conversation_id:number; status:ConversationStatus; priority?:ConversationPriority|null;
  synced?:string; priority_synced?:PrioritySyncResult|string }
type SupportErrorCode = 'CLIENT_WROTE'|'LOCKED_BY_OTHER'|'REPLY_WINDOW_CLOSED'
  |'KB_VERSION_CONFLICT'|'KB_DOC_PUBLISHED'|'IMPORT_TOO_LARGE'|'IMPORT_PARSE_FAILED'|'JOB_BUSY'
  |'AI_DISABLED'|'AI_PAUSED'|'AI_KEY_MISSING'|'PROVIDER_ERROR'|'CONFLICT'
  // объявлены в core/errors.py:47-61; прочие (INVALID_INPUT, NOT_FOUND, NOT_IMPLEMENTED, UPSTREAM_ERROR,
  // AI_UPSTREAM_ERROR) приходят как string — getSupportErrorCode возвращает union со string
interface SupportErrorDetail { code:SupportErrorCode|string; error?:string; message?:string }
function getSupportErrorCode(err:unknown): SupportErrorCode|string|undefined  // detail.code | detail:str | error.code
function getSupportErrorMessage(err:unknown): string|undefined                // detail.error | error.message | error:str

// База знаний (B3a)
type KbDocStatus = 'draft'|'published'|'archived'
type KbDocSource = 'manual'|'import'|'candidate'|'faq'
type KbCandidateStatus = 'new'|'accepted'|'rejected'
interface SupportKbListItem { id:number; slug:string|null; title:string; source:string; status:KbDocStatus; version:number;
  updated_at:string; updated_by:number|null; excerpt:string }
interface SupportKbListResult { items:SupportKbListItem[]; total:number; page:number; per_page:number }
interface SupportKbDoc { id:number; slug:string|null; title:string; body:string; status:KbDocStatus; version:number; tags:string[];
  source:string; updated_by:number|null; published_at:string|null; archived_at:string|null; updated_at:string; created_at?:string|null }
interface SupportKbDocInput { title:string; body:string; slug?:string|null; tags?:string[]; source?:KbDocSource }
interface SupportKbDocCreateResult { id:number; slug:string|null; version:number; status:KbDocStatus }
interface SupportKbDocUpdateResult { id:number; slug:string|null; version:number; status:KbDocStatus; updated_at:string }
interface SupportKbPublishResult { id:number; status:'published'; published_at:string|null }
interface SupportKbArchiveResult { id:number; status:'archived'; archived_at:string|null }
interface SupportKbRestoreResult { id:number; status:'draft' }
interface SupportKbSearchItem { id:number; slug:string|null; title:string; rank:number; snippet:string }
interface SupportKbCandidate { id:number; topic:string|null; question:string|null; answer:string|null; occurrences:number;
  source:string; status:KbCandidateStatus; created_at:string; doc_id:number|null }
interface SupportKbCandidateListResult { items:SupportKbCandidate[]; total:number; page:number; per_page:number }
interface SupportKbCandidateDecision { decision:'accept'|'reject'; reason?:string; title?:string; body?:string }
interface SupportKbCandidateDecisionResult { id:number; status:KbCandidateStatus; doc_id?:number }
interface ListKbParams { status?:'draft'|'published'|'archived'|'all'; q?:string; page?:number; per_page?:number }
interface ListKbCandidatesParams { status?:KbCandidateStatus|'all'; page?:number; per_page?:number }

// Импорт базы знаний
type SupportImportKind = 'text'|'result_json'
type SupportImportJobStatus = 'queued'|'running'|'done'|'error'
interface SupportImportRequest { kind:SupportImportKind; text?:string; payload?:Record<string,unknown>|string;
  operator_names?:string[]; dry_run?:boolean }
interface SupportImportStartResult { job_id:number }
interface SupportImportResult { questions:number; pairs_created:number; skipped_duplicates:number; candidates_created:number;
  errors:string[]; dry_run?:boolean; would_create?:number; would_skip?:number; would_create_candidates?:number }
interface SupportImportJob { id:number; kind:SupportImportKind; status:SupportImportJobStatus; progress:number; total:number|null;
  result:SupportImportResult|null; error:string|null; started_at:string|null; finished_at:string|null }
interface SupportImportCancelResult { status:SupportImportJobStatus|null; error:string|null }

// ИИ: предложки, настройки, статистика, песочница
type SupportAiMode = 'off'|'shadow'|'suggest'|'auto'
type SupportAiLevel = 'sure'|'check'|'unsure'
type SupportSuggestionStatus = 'pending'|'sent'|'edited'|'rejected'|'superseded'
type SupportSuggestionDecision = 'send'|'edit'|'reject'
interface SupportAiGate { action:string|null; reason:string|null }
interface SupportAiUsedDoc { doc_id:number|null; title:string }
interface SupportAiSuggestion { id:number; conversation_id:number|null; message_id:number|null; text:string|null; final_text:string|null;
  operator_note:string|null; confidence:number|null; level:SupportAiLevel; used:SupportAiUsedDoc[]; reason:string|null;
  gate:SupportAiGate; model:string|null; status:SupportSuggestionStatus|null; created_at:string|null }
interface SupportAiSuggestionListResult { items:SupportAiSuggestion[]; total:number; page:number; per_page:number }
interface SupportSuggestionDecisionPayload { decision:SupportSuggestionDecision; final_text?:string; reason?:string }
type SupportSuggestionDecisionResult = {status:'sent'; message_id:number}|{status:'edited'; text:string}|{status:'rejected'}
interface SupportAiPause { until:string; by:string; note:string }
interface SupportAiSettings { mode:SupportAiMode; effective_mode:SupportAiMode; has_key:boolean; paused:SupportAiPause|null;
  model:string; fallback_model:string; base_url:string; min_confidence:number; require_kb:boolean; auto_per_hour:number;
  human_hold_minutes:number; debounce_seconds:number; kb_budget_chars:number; language:string; brand:string; allowed_domains:string[] }
interface SupportAiSettingsUpdate { mode?:SupportAiMode; min_confidence?:number; require_kb?:boolean; auto_per_hour?:number;
  debounce_seconds?:number }
interface SupportAiPauseRequest { hours?:number; until?:string; note?:string }
interface SupportAiActivityParams { since?:string; before?:number; limit?:number }
interface SupportAiActivityItem { id:number; conversation_id:number|null; action:string|null; gate_reason:string|null;
  confidence:number|null; model:string|null; tokens_in:number|null; tokens_out:number|null; status:string|null;
  created_at:string; gate_action:string|null }
interface SupportAiStatsDay { date:string; generated:number; sent:number }
interface SupportAiStats { generated:number; sent:number; edited:number; rejected:number; superseded:number; auto_sent:number;
  suggest_sent:number; shadow:number; sent_rate:number; avg_confidence:number; tokens_in:number; tokens_out:number;
  by_day:SupportAiStatsDay[] }
interface SupportAiTryRequest { text:string; assume_auto?:boolean }
interface SupportAiTryResult { draft:{ reply:string; operator_note:string; used:SupportAiUsedDoc[]; confidence:number|null;
  clarify:boolean; needs_human:boolean }; gate:{ action:string; reason:string; level?:SupportAiLevel } }

// Фидбек по ответу
type SupportFeedbackVerdict = 'correct'|'partial'|'wrong'
interface SupportFeedbackPayload { verdict:SupportFeedbackVerdict; note?:string; correct_answer?:string }
interface SupportFeedbackResult { qa_pair_id:number|null }

// SLA (C2)
type SupportSlaKind = 'first_response'|'resolution'
interface SupportSlaPolicy { name:string; first_response_minutes:number; resolution_minutes:number }
interface SupportSlaEvent { id:number; conversation_id:number; kind:SupportSlaKind; due_at:string; notified_at:string|null;
  breached_at:string|null; subject:string|null; priority:ConversationPriority; status:ConversationStatus;
  assignee_id:number|null; overdue_minutes:number|null }
interface SupportSlaBreaches { first_response:number; resolution:number }
interface SupportSlaOverview { policies:SupportSlaPolicy[]; breaches:SupportSlaBreaches; events:SupportSlaEvent[] }

// Шаблоны ответов (C1)
interface SupportTemplate { id:number; shortcut:string; title:string; body:string; category:string|null; uses:number;
  created_by:number|null; created_at:string; updated_at:string }
interface SupportTemplateInput { shortcut:string; title:string; body:string; category?:string|null }
interface SupportTemplateListResult { items:SupportTemplate[]; total:number; page:number; per_page:number }
interface ListTemplatesParams { q?:string; category?:string; page?:number; per_page?:number }

// Заметки о клиенте и присутствие (C4)
interface SupportNote { id:number; text:string; actor_id:number|null; actor_name:string; created_at:string|null }
type SupportPresenceState = 'viewing'|'typing'
interface SupportPresenceItem { actor_id:number|null; actor_name:string; state:SupportPresenceState; seen_at:string }
interface SupportPresencePing { conversation_id:number; state:SupportPresenceState }
interface SupportPresencePingResult { ok:boolean; throttled:boolean }

// Аналитика и команда (C3)
interface SupportAnalyticsTotals { conversations_created:number; conversations_resolved:number; messages_in:number;
  messages_out:number; open_now:number; unassigned_now:number }
interface SupportAnalyticsDay { date:string; created:number; resolved:number; incoming:number; outgoing:number }
interface SupportAnalyticsChannel { channel:string; conversations:number; messages:number }
interface SupportAnalyticsPriority { priority:string; conversations:number; breached_first_response:number }
interface SupportAnalyticsFirstResponse { median_minutes:number|null; p90_minutes:number|null; count:number }
interface SupportAnalyticsOperator { actor_id:number; login:string; display_name:string; replies:number;
  conversations:number; last_reply_at:string|null }
interface SupportAnalyticsAi { generated:number; sent:number; edited:number; rejected:number; auto_sent:number;
  suggest_sent:number; shadow:number }
interface SupportAnalytics { range_days:number; totals:SupportAnalyticsTotals; by_day:SupportAnalyticsDay[];
  by_channel:SupportAnalyticsChannel[]; by_priority:SupportAnalyticsPriority[]; first_response:SupportAnalyticsFirstResponse;
  by_operator:SupportAnalyticsOperator[]; ai:SupportAnalyticsAi }
interface SupportOperator { id:number; login:string; display_name:string; status:string; active_dialogs:number;
  replies_30d:number; present:boolean }
interface SupportAuditItem { id:number; actor_id:number|null; actor_name:string|null; action:string; resource:string;
  resource_id:string|null; payload:Record<string,unknown>; ip:string|null; created_at:string }
interface SupportAuditListResult { items:SupportAuditItem[]; total:number; page:number; per_page:number }
interface SupportAuditActionCount { action:string; count:number }
interface ListAuditParams { action?:string; actor_id?:number; page?:number; per_page?:number }

supportApi.listConversations(params?: ListConversationParams): Promise<SupportListResult>   // GET /api/support/conversations
supportApi.getConversation(id): Promise<SupportConversationDetail>                          // GET  /api/support/conversations/{id}
supportApi.replyConversation(id, {text, attachment_ids?, client_msg_id?, force?}): Promise<ReplyResult> // POST /api/support/conversations/{id}/reply
supportApi.readConversation(id): Promise<{conversation_id, unread}>                         // POST /api/support/conversations/{id}/read
supportApi.setState(id, {status, priority?, seen_at?}): Promise<StateResult>                 // POST /api/support/conversations/{id}/state
supportApi.setAssignee(id, {assignee_id}): Promise<{conversation_id, assignee_id}>         // POST /api/support/conversations/{id}/assignee
supportApi.getCustomer(id): Promise<SupportCustomerCard>                                   // GET  /api/support/conversations/{id}/customer
supportApi.refreshCustomer(id): Promise<SupportCustomerCard>                                // POST /api/support/conversations/{id}/customer/refresh
supportApi.uploadAttachment(file): Promise<SupportUploadResult>                             // POST /api/support/attachments
supportApi.getAttachmentBlob(id, download=false): Promise<Blob>                             // GET /api/support/attachments/{id}
supportApi.getPollers(): Promise<SupportPollersResult>                                      // GET /api/support/pollers
supportApi.getConfigStatus(): Promise<SupportConfigStatus>                                  // GET /api/support/config-status
supportApi.listKb(params?: ListKbParams): Promise<SupportKbListResult>                      // GET /api/support/kb
supportApi.getKb(id): Promise<{doc: SupportKbDoc}>                                          // GET /api/support/kb/{id}
supportApi.createKb(data: SupportKbDocInput): Promise<SupportKbDocCreateResult>             // POST /api/support/kb
supportApi.updateKb(id, data & {expected_version:number}): Promise<SupportKbDocUpdateResult> // PUT /api/support/kb/{id}
supportApi.publishKb(id, expected_version): Promise<SupportKbPublishResult>                 // POST /api/support/kb/{id}/publish
supportApi.archiveKb(id): Promise<SupportKbArchiveResult>                                   // POST /api/support/kb/{id}/archive
supportApi.restoreKb(id): Promise<SupportKbRestoreResult>                                   // POST /api/support/kb/{id}/restore
supportApi.deleteKb(id): Promise<{deleted:boolean}>                                         // DELETE /api/support/kb/{id}
supportApi.searchKb(q, limit=10): Promise<{items: SupportKbSearchItem[]}>                   // GET /api/support/kb/search
supportApi.listCandidates(params?: ListKbCandidatesParams): Promise<SupportKbCandidateListResult> // GET /api/support/kb/candidates
supportApi.decideCandidate(id, data: SupportKbCandidateDecision): Promise<SupportKbCandidateDecisionResult> // POST /api/support/kb/candidates/{id}
supportApi.importKb(data: SupportImportRequest): Promise<SupportImportStartResult>          // POST /api/support/kb/import
supportApi.getImportJob(jobId): Promise<SupportImportJob>                                   // GET /api/support/kb/import/{jobId}
supportApi.cancelImport(jobId): Promise<SupportImportCancelResult>                          // POST /api/support/kb/import/{jobId}/cancel
supportApi.getSuggestion(id): Promise<SupportAiSuggestion>                                  // GET /api/support/suggestions/{id}
supportApi.decideSuggestion(id, data): Promise<SupportSuggestionDecisionResult>             // POST /api/support/suggestions/{id}/decide
supportApi.getAssistantSettings(): Promise<SupportAiSettings>                               // GET /api/support/assistant/settings
supportApi.updateAssistantSettings(data: SupportAiSettingsUpdate): Promise<SupportAiSettings> // PUT /api/support/assistant/settings
supportApi.pauseAssistant(data: SupportAiPauseRequest): Promise<SupportAiPause>             // POST /api/support/assistant/pause
supportApi.resumeAssistant(): Promise<{paused:false}>                                      // DELETE /api/support/assistant/pause
supportApi.assistantActivity(params?): Promise<{items: SupportAiActivityItem[]}>            // GET /api/support/assistant/activity
supportApi.assistantStats(days=30): Promise<SupportAiStats>                                 // GET /api/support/assistant/stats
supportApi.tryAssistant(data: SupportAiTryRequest): Promise<SupportAiTryResult>             // POST /api/support/assistant/try
supportApi.messageFeedback(messageId, data: SupportFeedbackPayload): Promise<SupportFeedbackResult> // POST /api/support/messages/{id}/feedback
supportApi.listSlaPolicies(): Promise<{items: SupportSlaPolicy[]}>                          // GET /api/support/sla/policies
supportApi.updateSlaPolicy(name, data): Promise<SupportSlaPolicy>                            // PUT /api/support/sla/policies/{name}
supportApi.getSlaOverview(days=7): Promise<SupportSlaOverview>                               // GET /api/support/sla/overview
supportApi.listTemplates(params?: ListTemplatesParams): Promise<SupportTemplateListResult>   // GET /api/support/templates
supportApi.createTemplate(data: SupportTemplateInput): Promise<SupportTemplate>              // POST /api/support/templates
supportApi.updateTemplate(id, data: SupportTemplateInput): Promise<SupportTemplate>          // PUT /api/support/templates/{id}
supportApi.deleteTemplate(id): Promise<{deleted:boolean}>                                    // DELETE /api/support/templates/{id}
supportApi.useTemplate(id): Promise<{id, uses}>                                              // POST /api/support/templates/{id}/use
supportApi.listNotes(customerId): Promise<{items: SupportNote[]}>                             // GET /api/support/customers/{customerId}/notes
supportApi.createNote(customerId, {text}): Promise<SupportNote>                               // POST /api/support/customers/{customerId}/notes
supportApi.deleteNote(noteId): Promise<{deleted:boolean}>                                     // DELETE /api/support/notes/{noteId}
supportApi.pingPresence({conversation_id, state}): Promise<SupportPresencePingResult>         // POST /api/support/presence
supportApi.getPresence(conversationId): Promise<{items: SupportPresenceItem[]}>               // GET /api/support/presence/{conversationId}
supportApi.getAnalytics(days=30): Promise<SupportAnalytics>                                  // GET /api/support/analytics?days=
supportApi.listOperators(): Promise<{items: SupportOperator[]}>                              // GET /api/support/operators
supportApi.listAudit(params?: ListAuditParams): Promise<SupportAuditListResult>              // GET /api/support/audit
supportApi.listAuditActions(): Promise<{items: SupportAuditActionCount[]}>                   // GET /api/support/audit/actions
// getSupportErrorMessage: TEMPLATE_EXISTS -> «Шаблон с таким ярлыком уже существует»; SLA_POLICY_NOT_FOUND -> «Политика SLA не найдена»
```

## 3.16a Support: страницы и компоненты ИИ/КБ

```
pages/support/Queue.tsx          // очередь: каналы/pollers, список, тред (MessageThread с AiDraftCard над композером), композер
pages/support/Kb.tsx             // `/support/kb`: табы «Статьи»/«Черновики»/«Идеи», поиск (debounce 300 мс), редактор справа
pages/support/Assistant.tsx      // `/support/ai`: настройки + статистика (7/30 дней) + песочница; query-keys support-assistant-settings/-stats
pages/support/Sla.tsx            // `/support/sla`: 4 политики (low/normal/high/urgent) с PUT по строке, счётчики просрочек, события с дедлайнами
pages/support/Templates.tsx      // `/support/templates`: поиск (debounce 300 мс), список, редактор (shortcut /..., title, category, body), use/delete
pages/support/Analytics.tsx      // `/support/analytics`: 7/30/90 дней; 6 метрик, первый ответ (медиана/P90/count), CSS-бары by_day,
                                 // таблицы by_channel / by_priority / by_operator, блок ИИ; query-key ['support','analytics',days]
pages/support/Team.tsx           // `/support/team`: карточки операторов (status, present → «в панели»/«не в сети», active_dialogs,
                                 // replies_30d) + журнал аудита с фильтром action, per_page=25 и пагинацией; только чтение
pages/support/Placeholder.tsx    // не смонтирован: `/support/analytics` и `/support/team` заменены на Analytics/Team
pages/support/components/AiDraftCard.tsx      // карточка предложки: уровень, used[], «Почему так?», operator_note, Отправить/Править/Отклонить, «Это неверно»
                                             // при suggestion.gate.action === 'shadow' не рендерится
pages/support/components/MessageThread.tsx    // переписка, цитата reply_excerpt, фидбек по исходящему; присутствие «Смотрит: … / печатает: …»,
                                             // пинг viewing при открытии и typing при вводе (троттлинг 5 с), `/shortcut`-подсказка (до 5)
pages/support/components/TemplatePicker.tsx   // попап «Шаблоны» над композером (поиск, debounce 250 мс) + экспорт useSupportTemplates(q, enabled)
                                             // query-key ['support','templates','picker',q], per_page=50, staleTime 30 с; выбор → onPick(body) + useTemplate(id)
pages/support/components/ConversationList.tsx // список диалогов + фильтры
pages/support/components/CustomerCard.tsx     // карточка клиента Bedolaga (refresh) + внутренние заметки;
                                             // props: card, isLoading, isRefreshing, onRefresh, customerProfileId?, currentUserId?

components/kb/KbList.tsx         // список статей/идей, excerpt и total (без пагинации)
components/kb/KbEditor.tsx       // форма статьи + кнопки Сохранить/Опубликовать/В архив/Восстановить/Удалить (мутации и диалоги — в Kb.tsx)
components/kb/CandidateList.tsx  // идеи статей: принять (→ draft-статья) / отклонить
components/kb/ImportPanel.tsx    // импорт текста чата или result.json: dry-run по умолчанию, прогресс support_job, отмена

pages/support/components/assistant/ModeCard.tsx    // off|shadow|suggest|auto + «фактически: …»; без ключа suggest/auto заблокированы
pages/support/components/assistant/PauseCard.tsx   // пауза 1 ч / 4 ч / 24 ч / «до утра», снятие паузы (режим не меняется)
pages/support/components/assistant/ParamsCard.tsx  // порог уверенности, require_kb, автоответов в час, debounce 3..60 с
pages/support/components/assistant/StatsCard.tsx   // агрегаты + CSS-бары by_day (без chart-библиотек)
pages/support/components/assistant/TryPanel.tsx    // песочница «Проверить»: draft + gate, в БД не пишет

lib/supportSocket.ts
  type SupportEventPayload = { type:'message'|'message_updated'|'conversation'|'poller'|'ai_suggestion'|'presence'|'sla_alert'|'ping'; data? }
  handlers: onMessage, onMessageUpdated, onConversation, onPoller, onAiSuggestion, onPresence, onSlaAlert, onAuthExpired, onStatusChange
  кадр ai_suggestion.data = { conversation_id, suggestion_id, status }   // ws.py:127 + suggestions.py:208-262
  кадр presence.data = { conversation_id, actor_id, state:'viewing'|'typing' }   // presence.py:52-61; только при реальной записи (не throttled)
  кадр sla_alert.data = { conversation_id, kind:'first_response'|'resolution', due_at:ISO, overdue_minutes }  // ws.py mapping + core/support/sla.py:106
  useSupportSocket(handlers): реконнект 2→5→10→30 с; close 4401 → /admin/login
```
Компоненты КБ физически лежат в `src/components/kb/` (план Этапа B §9 B3 указывал `pages/support/components/kb/` — фактический путь другой).

## 3.17 `notifications.ts` — фронтенд шире бэкенда

```ts
interface Notification { id:number; admin_id:number|null; type:string; severity:string; title:string; body:string|null;
  link:string|null; is_read:boolean; source:string|null; source_id:string|null; group_key:string|null; created_at:string|null }
interface NotificationChannel { id:number; admin_id:number; channel_type:string; is_enabled:boolean;
  config:Record<string,string>; created_at:string|null; updated_at:string|null }
interface SmtpConfig { id:number; host:string; port:number; username:string|null; from_email:string; from_name:string;
  use_tls:boolean; use_ssl:boolean; is_enabled:boolean; updated_at:string|null }
interface AlertRule { id:number; name:string; description:string|null; is_enabled:boolean; rule_type:string; metric:string|null;
  operator:string|null; threshold:number|null; duration_minutes:number; channels:string[]; severity:string;
  cooldown_minutes:number; group_key:string|null; escalation_admin_id:number|null; escalation_minutes:number;
  title_template:string; body_template:string; topic_type:string|null; max_offline_minutes:number;
  last_triggered_at:string|null; last_value:number|null; trigger_count:number; created_by:number|null;
  created_at:string|null; updated_at:string|null }
interface AlertLog { id:number; rule_id:number|null; rule_name:string|null; metric_value:number|null; threshold_value:number|null;
  severity:string|null; channels_notified:string[]; acknowledged:boolean; acknowledged_by:number|null;
  acknowledged_at:string|null; details:string|null; created_at:string|null }
interface PaginatedResponse<T> { items:T[]; total:number; page:number; per_page:number; pages:number }
interface AlertTemplate { id:string; name:string; description:string; metric:string; operator:string; threshold:number;
  duration_minutes:number; cooldown_minutes:number; severity:string; channels:string[]; title_template:string;
  body_template:string; is_activated:boolean }
notificationsApi: list, unreadCount, markRead, delete, deleteOld, create,
  listChannels, createChannel, updateChannel, deleteChannel,
  getSmtpConfig, updateSmtpConfig, testSmtp,
  listAlertRules, createAlertRule, updateAlertRule, deleteAlertRule, toggleAlertRule,
  listAlertLogs, acknowledgeAlerts, listAlertTemplates, activateAlertTemplate
```
Пути: `/api/notifications*`, `/api/notification-channels*`, `/api/smtp-config*`, `/api/alert-rules*`, `/api/alert-logs*`, `/api/alert-templates*`.
⚠ В бэкенде реализованы только 3 маршрута из §1.13 — остальные вернут 404.

**Итого функций API-клиентов:** 163 (включая 7 методов `paymentsProvider` для каждого из провайдеров `platega`/`yookassa`).

---

# 4. Frontend State Management (Zustand Stores)

```
src/store/authStore.ts
  interface AuthState { token: string|null; user: {id:number;login:string;email:string;role:string}|null;
                        setAuth(token,user): void; clearAuth(): void }
  useAuthStore = create<AuthState>()(persist(stateCreator, { name: 'auth-store' }))          // localStorage, без partialize
  init: token=null, user=null

src/store/permissionStore.ts
  interface Permission { resource:string; action:string }
  interface PermissionState { permissions:Permission[]; role:string|null; roleId:number|null; isLoaded:boolean;
                              mustChangePassword:boolean;
                              loadPermissions(): Promise<void>; hasPermission(resource,action): boolean;
                              clearPermissions(): void; setMustChangePassword(v): void }
  usePermissionStore = create<PermissionState>(stateCreator)                                  // без persist
  init: permissions=[], role=null, roleId=null, isLoaded=false, mustChangePassword=false
  hasPermission: true если role ∈ {null,'admin','superadmin'}, иначе поиск в permissions

src/store/useAppearanceStore.ts
  type UIDensity='compact'|'comfortable'|'spacious'; BorderRadius='sharp'|'default'|'rounded';
       FontSize='small'|'default'|'large'; ThemePreset='obsidian'|'arctic'|'sakura'|'twilight'|'ember';
       ColorMode='dark'|'light'|'auto'
  interface AppearanceSettings { theme:ThemePreset; colorMode:ColorMode; density:UIDensity; borderRadius:BorderRadius;
                                 fontSize:FontSize; animationsEnabled:boolean; sidebarCollapsed:boolean }
  interface AppearanceState extends AppearanceSettings { hydrated:boolean; _fetchPromise:Promise<void>|null;
    setTheme(theme); setColorMode(mode); setDensity(d); setBorderRadius(r); setFontSize(s);
    setAnimationsEnabled(b); setSidebarCollapsed(b); toggleSidebar(); toggleColorMode(); resetToDefaults();
    loadFromServer(): Promise<void> }
  useAppearanceStore = create<AppearanceState>()(persist(stateCreator, { name:'remnawave-appearance',
      storage: createJSONStorage(()=>localStorage), partialize: 7 полей, onRehydrateStorage: hydrated=true }))
  defaults: obsidian / dark / comfortable / default / default / animations=true / collapsed=false
  debounce-синк 1000мс -> preferencesApi.savePreferences({ appearance })
  export function useResolvedColorMode(): 'dark'|'light'

src/store/useBrandingStore.ts
  export const BRANDING_FALLBACK: Branding = { site_name:'HexaVeil VPN', admin_title:'HexaVeil CMS',
      browser_title:'HexaVeil CMS', title_separator:'—', favicon_url:'' }
  interface BrandingState extends Branding { loaded:boolean; load(): Promise<void> }
  useBrandingStore = create<BrandingState>(stateCreator)                                      // без persist
  load(): publicApi.getBranding -> set + document.title + <link rel=icon>

src/store/useFiltersStore.ts
  interface SavedFilter { id:string; name:string; page:'users'|'violations';
                          filters:Record<string,unknown>; createdAt:number }
  interface FiltersState { savedFilters:SavedFilter[];
    saveFilter(f: Omit<SavedFilter,'id'|'createdAt'>): void; deleteFilter(id): void;
    getFiltersForPage(page:'users'|'violations'): SavedFilter[] }
  useFiltersStore = create<FiltersState>()(persist(stateCreator, { name:'remnawave-saved-filters' }))
  saveFilter: id=crypto.randomUUID(), createdAt=Date.now()

src/store/useSidebarLinksStore.ts
  interface SidebarLink { id:string; label:string; url:string; icon:string; enabled:boolean }
  interface SidebarLinksState { links:SidebarLink[]; hydrated:boolean; _fetchPromise:Promise<void>|null;
    setLinks(links): void; resetToDefaults(): void; loadFromServer(): Promise<void> }
  useSidebarLinksStore = create<SidebarLinksState>()(persist(stateCreator, { name:'hexaveil-sidebar-links',
      storage: createJSONStorage(()=>localStorage), partialize:{links}, onRehydrateStorage: hydrated=true }))
  defaultLinks = []
  setLinks -> фоновый preferencesApi.savePreferences({ sidebarLinks })

src/store/useWebSocket.ts
  export function useRealtimeUpdates(): void   // no-op stub
```

---

# 5. Frontend Navigation & UI Primitives

## 5.1 Маршруты SPA — `src/App.tsx`

Провайдеры: `AppearanceProvider` → `BrandingProvider` → `ErrorBoundary` → `<BrowserRouter basename="/admin">` → `Suspense` → `Routes`.
`RequireAuth` при отсутствии `token` → `<Navigate to="/login" replace />`. Все роуты плоские, без вложенности и `*`-суффиксов.

| Путь | Компонент | Auth | lazy |
|---|---|---|---|
| `/login` | `pages/Login` | нет | нет |
| `/` | `pages/Dashboard` | да | да |
| `/posts` | `pages/PostsList` | да | да |
| `/posts/create` | `pages/PostEdit` | да | да |
| `/posts/:id` | `pages/PostEdit` | да | да |
| `/posts/categories` | `pages/CategoriesList` | да | да |
| `/pages` | `pages/PagesList` | да | да |
| `/pages/create` | `pages/PageEdit` | да | да |
| `/pages/:id` | `pages/PageEdit` | да | да |
| `/media` | `pages/MediaList` | да | да |
| `/menus` | `pages/MenusList` | да | да |
| `/menus/create` | `pages/MenuEdit` | да | да |
| `/menus/:id` | `pages/MenuEdit` | да | да |
| `/widgets` | `pages/WidgetsList` | да | да |
| `/finance` | `pages/Finance` | да | да |
| `/users` | `pages/UsersList` | да | да |
| `/settings` | `pages/Settings` | да | да |
| `/logs` | `pages/LogsViewer` | да | да |
| `/diagnostics` | `pages/Diagnostics` | да | да |
| `/bedolaga` | `pages/bedolaga/BedolagaDashboard` | да | да |
| `/bedolaga/customers` | `pages/bedolaga/BedolagaCustomers` | да | да |
| `/bedolaga/customers/:id` | `pages/bedolaga/BedolagaCustomerDetail` | да | да |
| `/bedolaga/promo` | `pages/bedolaga/BedolagaPromo` | да | да |
| `/bedolaga/marketing` | `pages/bedolaga/BedolagaMarketing` | да | да |
| `/bedolaga/referrals` | `pages/bedolaga/BedolagaReferrals` | да | да |
| `/bedolaga/tariffs` | `pages/bedolaga/BedolagaTariffs` | да | да |
| `/bedolaga/revenue` | `pages/bedolaga/BedolagaRevenue` | да | да |
| `/support` | `pages/support/Queue` (`SupportQueue`) | да | да |
| `/support/sla` | `pages/support/Sla` (`SupportSla`) | да | да |
| `/support/kb` | `pages/support/Kb` (`SupportKb`) | да | да |
| `/support/ai` | `pages/support/Assistant` (`SupportAssistant`) | да | да |
| `/support/templates` | `pages/support/Templates` (`SupportTemplates`) | да | да |
| `/support/analytics` | `pages/support/Analytics` (`SupportAnalytics`) | да | да |
| `/support/team` | `pages/support/Team` (`SupportTeam`) | да | да |
| `/changelog` | `pages/ChangelogViewer` | да | да |
| `*` | `pages/NotFound` | нет | да |

**Bedolaga tariffs (`/bedolaga/tariffs`) — `BedolagaTariffs`:** ответ типизирован
`TariffsResponse { items, total, status?, error? }`; при `status !== 'ok'` над каталогом показывается
янтарный баннер (`bedolaga.tariffs.botDbUnavailable` + `error`), пустой каталог `status='ok'` остаётся
«Тарифы не найдены». Query-key `['bedolaga-tariffs', showInactive]`, staleTime 60с.

**Bedolaga revenue (`/bedolaga/revenue`) — `BedolagaRevenue`:** отдельная страница дохода по тарифам (не смешивает
`fin_transactions`). Query keys: `['bedolaga-analytics-overview', month, basis, months]` (`getAnalyticsOverview`,
staleTime 30с, refetchInterval 60с, refetchOnWindowFocus), `['bedolaga-analytics-forecast', nextMonth]`
(`getAnalyticsForecast`, тот же polling) и `['bedolaga-analytics-tariffs']` (только для `is_active`).
Контролы: месяц `YYYY-MM`, глубина 6/12, `basis=cash|accrual`, CSV (KPI + таблица, `;`, UTF-8 BOM).
KPI: MRR (+lower bound), ожидаемо в следующем месяце, оплачено вперёд, получено/начислено за месяц (по `basis`),
активных платных, trial, покрытие цен. Таблица по тарифам: paid/trial, цена/мес (free → «Бесплатный», unknown → «—»),
MRR, оплачено вперёд, ожидаемо, доля, `price_source` (bot_db→Прайс, transactions→Факт, manual→Вручную, unknown→Нет цены),
`unknown_price_clients`; сортировка по клиентам/доходу, фильтр по unknown-тарифу из блока покрытия; строка `tariff_id=null`
(«Не определено») отдельно от бесплатных. График `ComposedChart`: bar `cash_received_rubles` + line `accrual_revenue_kopeks`
(null для прошлых месяцев → разрыв, без выдуманных точек). Календарь `forecast.by_day` по дням/неделям + top-50 `items`.
`warnings[]`/`partial` — баннеры, 503 — «Интеграция Bedolaga не настроена» + ссылка в настройки, ошибки — `QueryError`.

**Bedolaga-страницы (E3/E4):** `BedolagaCustomers` — локальный тип клиента содержит `tariff_id/tariff_name/tariff_missing`
(и те же поля в `subscription`); колонка «Тариф» (имя, `Без тарифа` muted, бейдж `Trial`, цена из `/analytics/tariffs`:
`is_free` → «Бесплатный», иначе `monthly_price_rubles` → `N ₽/мес`), сортировка `sort=tariff`, фильтр `tariff_id`
или `tariff_missing=true`, CSV-колонки `Tariff` / `Tariff price (RUB/month)` / `Paid until`, строка тарифа в мобильной карточке.
`BedolagaCustomerDetail` — тариф в «Информации» из top-level `tariff_id/tariff_name/tariff_missing` с fallback
`subscription` → `primary_subscription` (аналитика); карточка «Финансы клиента» из `GET /api/bedolaga/analytics/customers/{id}`
(`primary_subscription{tariff_id,tariff_name,end_date,days_left,autopay_*}`, `tariff{period_price_rubles,period_days,monthly_price_rubles}`,
`money{paid_total_kopeks,paid_forward_kopeks,next_payment_date,next_payment_kopeks,expected_charge_date}`),
query-key `['bedolaga-customer-analytics', id]` (staleTime 60с); ошибка/`partial` → прочерки и warning, страница не ломается.

**Support Queue (`/support`) — `pages/support/Queue`:** над очередью — панель статуса каналов
(`Card` + `Badge`) из `useQuery(['support-pollers'])` (`refetchInterval` 30с, `refetchOnWindowFocus`);
строки `telegram`/`bedolaga` показывают `enabled`, `running`, `last_poll`, `last_error`; `conflict` —
красное пояснение про второй бот/webhook, отсутствие `telegram` — подсказка про токен и
`support_tg_enabled` (при ошибке запроса статус помечается недоступным, ложных «не запущен» нет).
Композер получает `media_max_mb` из `['support-config-status']` (`mediaMaxMb`, fallback 8):
подпись «до N МБ» и клиентская проверка размера перед `uploadAttachment`; серверный 413 остаётся истиной.
WS-инвалидация `['support-pollers']` сохраняется.

**Settings (`/settings`):** вкладки `basic`, `seo`, `theme` («Сайт»), `security`, `finance`,
`support` («Поддержка»), `integrations`, `logs`; controlled `Tabs` синхронизируются с `?tab=`.
Вкладки «Поддержка» и «Интеграции» рендерятся из реестра по `tab="support"` / `tab="integrations"`
(все `support_*`, `support_tg_*`, `support_ai_*` — во вкладке «Поддержка»), у HTTP-блоков — кнопки
`settingsApi.testIntegration`, у прокси — `settingsApi.testProxy`. Deep-link `?from=`
(`bedolaga|support|support_ai|bot_db|platega|yookassa|proxy`) маппится в категорию
(`FROM_TO_CATEGORY`); `support`/`support_ai` открывают вкладку `support`, остальные — `integrations`;
без `tab` вкладка выбирается по `from`, после загрузки выполняется
`scrollIntoView` к блоку с ASCII-якорем `settings-cat-*` (`CATEGORY_ANCHOR`). Ссылка
«Саппорт → Настройки» в сайдбаре ведёт на `?tab=support&from=support`; старые ссылки
`?tab=integrations&from=support` принудительно открывают `support`. Поиск матчит
`label/key/category/description` и алиасы вкладки (`TAB_SEARCH_ALIASES`: «поддержка» → support),
сбрасывается при смене вкладки. Блоки раскрыты
по умолчанию; при заданном `from` — только целевой (при поиске — все совпавшие), а если
`from` не сопоставлен категории — раскрываются все. Смена `from` сбрасывает поисковый запрос.
Пустой реестр соответствующей вкладки показывает `EmptyState` «Настройки интеграций недоступны»
с объяснением и кнопкой «Повторить» (`load()`); при `isPending`/`error` empty-state не рендерится.
У «ИИ / Саппорт» нет `INTEGRATION_TEST_IDS` — кнопка «Проверить» не показывается (by design).
`Section` принимает `id`, заголовок — `<button aria-expanded aria-controls>`, панель — `role="region"`.
После сохранения/сброса ключа `bedolaga_*`/`bot_db_*`/`support_*`/`outbound_proxy_*`, массового сохранения с такими ключами
и любой тест-проверки `bedolaga|bot_db|support|global` (успешной или нет) страница инвалидирует react-query:
`['bedolaga-status']`, `['bedolaga-overview']`, `['bedolaga-full']`, `['bedolaga-health']`, `['bedolaga-tariffs']`,
`['bedolaga-capabilities']`, `['bedolaga-maintenance']`, `['bedolaga-customers']`, `['bedolaga-analytics-overview']`,
`['bedolaga-analytics-forecast']`, `['bedolaga-analytics-tariffs']`, `['support-pollers']`, `['support-config-status']`.
Страница `/themes` и компонент `ThemeManager` удалены: настройки темы живут во вкладке «Сайт».

⚠ `/posts/:id` объявлен раньше `/posts/categories` → ссылка «Категории» открывает `PostEdit` с `id="categories"`.

**`/changelog` — `pages/ChangelogViewer`:** вкладки `changelog` / `history`; `editable` берётся из ответа API (оба документа `true`).
Changelog: карточки записей, «Новая запись» (`ChangelogEntryModal`, `docName='changelog'`) с блоком `also_history`, «Импорт .md»/«Экспорт .md».
History: базовый документ (`document.raw/html/updated_at`) отдельной карточкой + блоки «Дополнения» (`origin='changelog'` помечается «из ленты изменений») с edit/delete; кнопки «Редактировать документ» → `components/changelog/HistoryDocumentEditor`, «Импорт .md» (перезапись документа, блоки сохраняются), «Экспорт .md», «Новая запись» (`docName='history'`, `also_history` скрыт). Поиск фильтрует только блоки, документ виден всегда.
`HistoryDocumentEditor`: Dialog + `Textarea` (monospace, `h-[60vh]`), табы «Редактирование/Предпросмотр», счётчик символов; сохранение через `docsApi.putDocument('history', content, updatedAt)`, на 409 — сообщение и кнопка «Перезагрузить».
`lib/markdown.ts`: `mdToHtml(md): string` — общий минимальный markdown→HTML для предпросмотра (`ChangelogEntryModal`, `HistoryDocumentEditor`).

## 5.2 `components/ui/` — 23 файла, 0 default-export, barrel отсутствует

```
alert-dialog.tsx   -> AlertDialog, AlertDialogPortal, AlertDialogOverlay, AlertDialogTrigger, AlertDialogContent,
                      AlertDialogHeader, AlertDialogFooter, AlertDialogTitle, AlertDialogDescription,
                      AlertDialogAction, AlertDialogCancel                                  [@radix-ui/react-alert-dialog]
badge.tsx          -> Badge, badgeVariants (cva: default|success|warning|destructive|outline|secondary); interface BadgeProps
breadcrumb.tsx     -> Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbPage, BreadcrumbSeparator,
                      BreadcrumbEllipsis
button.tsx         -> Button, buttonVariants (variants: default|destructive|outline|secondary|ghost|link;
                      sizes: default|sm|lg|icon); interface ButtonProps { asChild?: boolean }
card.tsx           -> Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent
checkbox.tsx       -> Checkbox                                                              [@radix-ui/react-checkbox]
command.tsx        -> Command, CommandDialog, CommandInput, CommandList, CommandEmpty, CommandGroup, CommandItem,
                      CommandShortcut, CommandSeparator                                        [cmdk]
dialog.tsx         -> Dialog, DialogPortal, DialogOverlay, DialogClose, DialogTrigger, DialogContent,
                      DialogHeader, DialogFooter, DialogTitle, DialogDescription
dropdown-menu.tsx  -> DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem,
                      DropdownMenuCheckboxItem, DropdownMenuRadioItem, DropdownMenuLabel, DropdownMenuSeparator,
                      DropdownMenuShortcut, DropdownMenuGroup, DropdownMenuPortal, DropdownMenuSub,
                      DropdownMenuSubContent, DropdownMenuSubTrigger, DropdownMenuRadioGroup
input.tsx          -> Input (interface InputProps)
label.tsx          -> Label                                                                  [@radix-ui/react-label]
popover.tsx        -> Popover, PopoverTrigger, PopoverContent
scroll-area.tsx    -> ScrollArea, ScrollBar
select.tsx         -> Select, SelectGroup, SelectValue, SelectTrigger, SelectContent, SelectLabel, SelectItem,
                      SelectSeparator, SelectScrollUpButton, SelectScrollDownButton
separator.tsx      -> Separator
sheet.tsx          -> Sheet, SheetPortal, SheetOverlay, SheetTrigger, SheetClose, SheetContent, SheetHeader,
                      SheetFooter, SheetTitle, SheetDescription; interface SheetContentProps (side: top|bottom|left|right)
skeleton.tsx       -> Skeleton
sonner.tsx         -> Toaster (theme from useResolvedColorMode, position=bottom-right, duration=4000)
switch.tsx         -> Switch
table.tsx          -> Table, TableHeader, TableBody, TableFooter, TableHead, TableRow, TableCell, TableCaption
tabs.tsx           -> Tabs, TabsList, TabsTrigger, TabsContent
textarea.tsx       -> Textarea (interface TextareaProps)
tooltip.tsx        -> Tooltip, TooltipTrigger, TooltipContent, TooltipProvider
```

## 5.3 Sidebar — `components/layout/Sidebar.tsx`

Источник данных: `@/config/navigation` (`NavigationEntry = NavItem | NavGroup | NavSection`), рендер в порядке массива + динамические внешние ссылки из `useSidebarLinksStore`.

```
Секция «Главное»:    Дашборд / (LayoutDashboard)
Группа «Сайт» (Globe): Посты /posts (FileText) · Категории /posts/categories (Folder) · Страницы /pages (File)
                     Меню /menus (Menu) · Медиа /media (Image) · Виджеты /widgets (Puzzle)
Секция «Финансы»:    Финансы /finance (Wallet)
Секция «Bedolaga»:   группа «Bedolaga Bot» (Bot)
                     Дашборд /bedolaga (BarChart3) · Клиенты /bedolaga/customers (Users) · Тарифы /bedolaga/tariffs (BadgeCheck)
                     Доход по тарифам /bedolaga/revenue (TrendingUp)
                     Промокоды /bedolaga/promo (Ticket) · Маркетинг /bedolaga/marketing (Megaphone) · Рефералы /bedolaga/referrals (Share2)
                     Настройки /settings?tab=integrations&from=bedolaga (SlidersHorizontal; `from` потребляет Settings)
Секция «Саппорт»:    группа «Саппорт» (LifeBuoy)
                     Очередь /support (Inbox) · Контроль SLA /support/sla (Gauge) · База знаний /support/kb (BookOpen)
                     ИИ-ассистент /support/ai (Sparkles) · Шаблоны /support/templates (FileStack)
                     Аналитика /support/analytics (BarChart3) · Команда /support/team (UserCog)
                     Настройки /settings?tab=integrations&from=support (SlidersHorizontal; `from` потребляет Settings)
Секция «Система»:    Пользователи /users (Users) · Настройки /settings (Settings) · Логи /logs (Terminal) · Диагностика /diagnostics (Monitor)
Секция «Документация»: Ченжлог /changelog (ScrollText)
```
Подсветка: `isActiveHref(href)` — для href без `?` сравнивает `pathname` (для `/settings` также требует
отсутствие `tab` и `from`); для href с `?` — точное `pathname + search`, а для `/settings?tab=…&from=…`
дополнительно нормализует: сравнивает `tab` (если `tab` нет, но есть `from` — берётся `integrations`)
и требует совпадения `from`, если он задан в href.
Контейнер дочерних пунктов раскрытой группы: `max-h-[32rem]`.
Все `permission: null` (гейтинга нет). Иконки внешних ссылок: `Github|MessageCircle|Heart|Globe|Link` → fallback `LinkIcon`.
Logout: `clearAuth()` + `window.location.href = '/admin/logout'`.
`main.tsx`: `StrictMode` → `QueryClientProvider(staleTime 3м, retry 1, refetchOnWindowFocus false)` → `TooltipProvider` → `<App/>` + `<Toaster/>`; импорт `./i18n`, `./index.css`. Router только в `App.tsx`.

---

# 6. PHP Core & Legacy Bridge

## 6.1 `core/routes.php` — только GET, middleware отсутствует

```
GET ''              -> home: Page::getHomePage() | fallback Post::getPublishedPosts + Category::getAll -> theme index
GET post/{slug}     -> Post::getBySlug + incrementViews + getComments + getTags + getRelated -> post | errors/404
GET category/{slug} -> Category::getBySlug + getAll + getPosts                              -> category | errors/404
GET page/{slug}     -> Page::getBySlug                                                      -> page/{template} | errors/404
GET blog            -> Post::getPublishedPosts + Category::getAll                           -> blog
GET {slug}          -> Page::getBySlug                                                      -> page/{template} | errors/404   ⚠ catch-all, последний
```
Хелперы: `loadMenuItems(location='main', currentUri='')`, `loadFooterMenu()`, `getSeoSettings()`, `getActiveTheme()`, `createTemplate()`.

`index.php`: при `LEGACY_PHP_ADMIN=false` URI `#^/(admin|api)(/|$)#` → HTTP 404 `{"success":false,"error":"Not Found"}` до роутера.
`core/Router.php`: точное совпадение метода, `{name}` → `(?P<name>[^/]+)`, первый матч побеждает, 404 → `errors/404`.

## 6.2 `core/models/` — 6 классов, без базового класса и статических свойств

```php
class Post {
  __construct();
  getPublishedPosts(int $limit = 10): array        // posts p JOIN categories c, users u -> p.*, category_name, author
  getBySlug(string $slug): ?array                  // + category_slug, author
  getById(int $id): ?array                         // posts.*
  incrementViews(int $id): void
  getComments(int $postId): array                  // comments WHERE post_id, status
  getTags(int $postId): array                      // tags t JOIN post_tags pt
  setTags(int $postId, array $tagNames): void      // DELETE post_tags; SELECT tags.slug; INSERT tags(name,slug); INSERT post_tags
  getRelated(?int $categoryId, int $currentId, int $limit = 3): array  // id,title,slug,image
  getAll(): array                                  // p.*, category_name, author_name
  create(array $data): int                         // INSERT posts (dynamic keys)
  update(int $id, array $data): bool               // UPDATE posts SET <keys>
  delete(int $id): bool
  getCount(): int
  getRecent(int $limit = 5): array                 // id,title,slug,status,created_at
}
class Category {
  getBySlug(string $slug): ?array; getById(int $id): ?array;
  getAll(): array                                   // c.id,name,slug,description, COUNT(p.id) posts_count
  getPosts(int $categoryId): array; create(array): int; update(int,array): bool; delete(int): bool; getCount(): int
}
class Page {
  getBySlug(string): ?array; getById(int): ?array; getHomePage(): ?array; getAll(): array  // + author_name
  setAsHome(int): bool; create(array): int; update(int,array): bool; delete(int): bool; isHomePage(int): bool
}
class Menu {
  getByLocation(string $location): array; getById(int): ?array; getAll(): array;
  create(array): int; update(int,array): bool; delete(int): bool
}
class Widget {
  getAllByArea(string $area): array; getAll(): array; getById(int): ?array;
  create(array): int; update(int,array): bool; delete(int): bool
}
class Setting {
  get(string $key): ?string; getAll(): array; set(string $key, string $value): bool; setMultiple(array $settings): bool
}
```

## 6.3 Legacy bridge — PHP-эндпоинтов НЕТ, всё проксируется в FastAPI

`Admin/*/api/*` в PHP отсутствуют полностью (нет `admin/`, нет `.htaccess`, нет route-map).

nginx `.docker/nginx/default.conf`:

```
^~ /admin/diagnostics/api/            -> http://api:8000
^~ /admin/settings/save-all-preferences -> http://api:8000
^~ /admin/settings/save-preference     -> http://api:8000
^~ /admin/finance/api/                -> http://api:8000  (proxy_read_timeout 60s)
=  /admin/logout                      -> 302 /admin/login
   /api/support/ws                    -> http://api:8000 (WS upgrade)
   /api/                              -> http://api:8000
=  /admin                             -> 302 /admin/
^~ /admin/                            -> SPA dist, try_files $uri $uri/ /admin/index.html
   /                                  -> try_files $uri $uri/ /index.php?$query_string
   ~ \.php$                           -> fastcgi_pass app:9000
```

Итоговые контракты bridge:

```
/api/*                       -> FastAPI (§1)
/admin/finance/api/*         -> finance.py + finance_payments.py (§1.18, §1.19)
/admin/diagnostics/api/*     -> diagnostics.py (§1.17)
/admin/settings/preferences  -> preferences.py (⚠ nginx не проксирует: попадает в SPA alias)
/admin/settings/save-all-preferences, /admin/settings/save-preference -> preferences.py
```

---

## Приложение A. Известные расхождения (ground truth)

1. Префикс API — `/api`, не `/api/v1` (документация местами устарела).
2. `response_model` не используется нигде; Pydantic-схемы носят декларативный характер.
3. Инвариант `{success, data, error}` соблюдается не везде: `finance /data`, `finance settings`, `preferences` (`ok`), `bedolaga` (upstream passthrough).
4. `GET /api/categories/{id}` отсутствует, но вызывается из `categoriesApi.get`.
5. 19 методов `notificationsApi` (channels/smtp/alerts) не имеют бэкенда.
6. `router.post('/posts/{post_id}')` вместо `PUT/PATCH` — историческое наследие PHP.
7. `/posts/:id` перекрывает `/posts/categories` в React Router.
8. `docs/ARCHITECTURE.md` и `PROJECT.md` всё ещё описывают `/admin/finance/api` и `/admin/diagnostics/api` как PHP.


---

# Приложение B. Модуль бэкапов (2026-11-21)

Решение: `docs/decisions/ADR-005-backup-system.md`. План: `docs/plans/2026-11-21-backup-system.md`.

## B.1 API — `/api/backups` (AUTH, конверт `W<...>`)

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/overview` | KPI + просрочки + «требует внимания» |
| GET | `/recipes` | каталог рецептов |
| GET/POST | `/hosts` | список/создание хоста |
| GET/PATCH/DELETE | `/hosts/{id}` | чтение/изменение/удаление |
| POST | `/hosts/{id}/test` | TCP/SSH-проверка |
| POST | `/hosts/{id}/agent-install` | токен + команда установки |
| POST | `/hosts/{id}/scan` | команда `scan` агенту |
| GET | `/hosts/{id}/components` | компоненты хоста |
| GET | `/components` | все компоненты (`?host_id=`) |
| PATCH | `/components/{id}` | `enabled`, `confidence` |
| GET/POST | `/storages` | хранилища |
| PATCH/DELETE | `/storages/{id}` | изменение/удаление |
| POST | `/storages/{id}/test` | проверка одного |
| POST | `/storages/test-all` | проверка всех (до `/{id}/test` по порядку) |
| GET/POST | `/policies` | политики |
| PATCH/DELETE | `/policies/{id}` | изменение/удаление |
| GET/POST | `/policies/{id}/tiers` | уровни политики |
| PATCH/DELETE | `/tiers/{id}` | изменение/удаление уровня |
| POST | `/tiers/{id}/run` | запуск уровня сейчас |
| GET | `/runs` | история (`host_id`, `status`, `kind`, `limit`, `offset`) |
| GET | `/runs/{id}` | детали + артефакты |
| GET | `/runs/{id}/log?offset=` | инкрементальный лог |
| POST | `/runs/{id}/cancel` | отмена |
| POST | `/runs` | ad-hoc запуск |
| GET | `/artifacts` | список (`host_id`, `run_id`) |
| GET | `/artifacts/{id}/download` | стрим из хранилища |
| POST | `/artifacts/{id}/verify` | пересчёт sha256 |
| DELETE | `/artifacts/{id}` | удаление объекта + записи |
| POST | `/restore/plan` | план по `group_key` |
| POST | `/restore` | запуск (`plan_token` + `confirm`) |
| GET | `/restore` / `/restore/{id}` | список/статус |
| POST | `/restore/{id}/cancel` | отмена |
| GET/POST | `/notifications/channels` | каналы |
| PATCH/DELETE | `/notifications/channels/{id}` | изменение/удаление |
| POST | `/notifications/channels/{id}/test` | тест канала |
| GET | `/notifications/events` | справочник событий |
| GET/POST | `/notifications/rules` | правила |
| PATCH/DELETE | `/notifications/rules/{id}` | изменение/удаление |
| GET/PUT | `/settings` | глобальные дефолты |

## B.2 API агента — `/api/backup-agent/v1` (Bearer-токен агента)

`GET /install.sh`, `POST /register`, `POST /heartbeat`, `GET /state` (ETag/304),
`POST /inventory`, `POST /runs`, `PATCH /runs/{id}`, `POST /runs/{id}/artifacts`,
`PUT /upload/{artifact_id}`, `GET /download/{artifact_id}`, `GET /commands`,
`POST /commands/{id}/finish`. Контракт: `backup-agent/PROTOCOL.md`.

## B.3 Таблицы (миграция `db/migrations/2026-11-21-backup-system.sql`)

`backup_storages`, `backup_hosts`, `backup_agents`, `backup_components`,
`backup_policies`, `backup_tiers`, `backup_runs`, `backup_artifacts`,
`backup_restores`, `backup_commands`, `backup_notification_channels`,
`backup_notification_rules`, `backup_settings`.

Идемпотентный DDL при старте: `core/backup/schema.py:ensure_backup_schema()`.

## B.4 Backend-файлы

`core/backup/{schema,recipes,manifest,repository,orchestrator,notifications,inline}.py`,
`core/backup/storage/{base,local,s3,sftp,rclone}.py`,
`api/v1/backups/{__init__,overview,hosts,components,storages,policies,runs,artifacts,restore,alerts,settings,common}.py`,
`api/v1/backup_agent.py`, `schemas/backup.py`.

## B.5 Frontend

- Клиент: `src/api/backups.ts` (`backupsApi.*`).
- Страницы: `src/pages/backups/BackupsPage.tsx`, `BackupsStorages.tsx`,
  `BackupsPolicies.tsx`, `BackupsOps.tsx`, `BackupsSettings.tsx`;
  `src/pages/infrastructure/{Nodes,Panel}.tsx`.
- Маршруты: `/backups`, `/infrastructure/nodes`, `/infrastructure/panel`.
- Навигация: группа «Инфраструктура» (`config/navigation.ts`).

## B.6 Интеграции

`core/integrations.py` → `IntegrationDef("backups")`, тест `_test_backups`.
Интеграция доступна в `Настройки → Интеграции → Бэкапы`.

---

# Приложение C. Deployment & Runtime (one-command install)

_Дата: 2026-11-26. Решение: `docs/decisions/ADR-006-one-command-deploy.md`,
план: `docs/plans/2026-11-26-one-command-deploy.md`._

## C.1 Compose: `deploy/compose.install.yml` (project name `hexaveil`)

Файл лежит в `deploy/`, поэтому относительные пути (`build.context`, `env_file`,
bind-mount'ы) резолвятся от `deploy/`: `..` — корень репозитория, `./` — файлы
рядом с compose. Interpolation-`.env` Compose ищет в каталоге проекта
(`deploy/`), поэтому корневой env передаётся явно:
`docker compose --env-file .env -f deploy/compose.install.yml …`.

| Сервис | Образ / сборка | Порты | Ключевые volumes / зависимости |
|--------|----------------|-------|-------------------------------|
| `caddy` | `caddy:2-alpine` | `80:80`, `443:443`, `443:443/udp` | `./Caddyfile:ro`, `caddy_data`, `caddy_config`; `depends_on: web` |
| `web` | `build: ..` + `deploy/Dockerfile.web` | нет (единственный вход — caddy) | `uploads_data:/var/www/html/public/uploads`; `depends_on: app, api` |
| `app` | `build: ..` + `Dockerfile` (PHP-FPM) | нет | `uploads_data`, `/var/run/docker.sock` (backup agent); ждёт `db: healthy` + `migrate: completed`; healthcheck `php-fpm -t` |
| `api` | `build: ..` + `web/backend/Dockerfile` | нет | `..:/var/www/html` **RW**, `uploads_data`, `backup_data:/var/lib/hexaveil/backups`; ждёт `db` + `migrate`; healthcheck `/api/health` |
| `db` | `postgres:16-alpine` | нет | `pgdata`; `POSTGRES_{DB,USER,PASSWORD}` из `DB_*`; healthcheck `pg_isready` |
| `migrate` | `postgres:16-alpine`, `entrypoint: /bin/sh /migrate.sh`, `restart: "no"` | нет | `../db:/db:ro`, `./migrate.sh:/migrate.sh:ro`; `depends_on: db: healthy` |

Volumes (project name закреплён → имена стабильны, не зависят от каталога):
`hexaveil_pgdata`, `hexaveil_uploads_data`, `hexaveil_backup_data`,
`hexaveil_caddy_data`, `hexaveil_caddy_config`.

`deploy/compose.behind-proxy.yml` — override для `--behind-proxy`: публикует
только `web` на `127.0.0.1:${CMS_HTTP_PORT:-3000}:80`. Caddy в этом режиме не
запускается.

Legacy: `docker-compose.prod.yml` — отдельный проект (имя из каталога),
контейнеры `hexacms_*`, тома `postgres_data` / `uploads_data` / `backup_data`,
`web` на `${CMS_BIND_IP:-127.0.0.1}:${CMS_HTTP_PORT:-3000}:80`, сервис
`migrate` присутствует, initdb-каталог не монтируется.

## C.2 Реестр ENV (deployment)

| Переменная | Кто читает | Смысл / дефолт |
|------------|-----------|----------------|
| `SITE_DOMAIN` | `deploy/Caddyfile`, `install.sh` | публичный домен; блок Caddy и ACME |
| `ADMIN_DOMAIN` | `deploy/Caddyfile`, `install.sh` | домен админки/API; `/` → `302 /admin/` |
| `ACME_EMAIL` | `caddy` (global `email`), certbot | ACME-аккаунт; `install.sh` валидирует формат |
| `ADMIN_LOGIN` | `deploy/bootstrap_admin.php` | логин админа, по умолчанию `admin` |
| `SITE_URL` | `config/config.php:20`, `web/backend/core/config.py:82` | публичный URL сайта; env имеет приоритет над `HTTP_HOST` |
| `CMS_PUBLIC_URL` | `web/backend/core/config.py:26` | внешний URL админки (ссылки установки агента), напр. `https://admin.example.com` |
| `CMS_HTTP_PORT` | `compose.behind-proxy.yml`, `docker-compose.prod.yml` | host-порт web в fallback/legacy, дефолт `3000` |
| `CMS_BIND_IP` | `docker-compose.prod.yml` | bind host-порта в legacy, дефолт `127.0.0.1` |
| `CORS_ORIGINS` | `web/backend/core/config.py:81` | явный список побеждает; при пустом — деривация (см. ниже) |
| `DB_NAME` / `DB_USER` / `DB_PASS` / `DB_HOST` / `DB_PORT` | `db`, `migrate`, app | `DB_PASS` — единственная обязательная interpolation-переменная compose |

Деривация CORS (`config.py:85-98`): если `CORS_ORIGINS` непустой — берётся
как есть (split по `,`); иначе собираются `CMS_PUBLIC_URL` и `SITE_URL`
(`rstrip('/')`, без дублей); если пусто и там — dev-дефолты
`http://localhost:3000`, `http://localhost:5173`, `http://localhost`.
`install.sh` пишет `CORS_ORIGINS=https://${ADMIN_DOMAIN},https://${SITE_DOMAIN}`.

ACME staging: отдельной ENV нет — раскомментировать `acme_ca
https://acme-staging-v02.api.letsencrypt.org/directory` в `deploy/Caddyfile`.

## C.3 `deploy/install.sh` — режимы и флаги

Режимы: локальный checkout (`BASH_SOURCE` → `deploy/compose.install.yml`) и
`curl | bash` (клон в `INSTALL_DIR`, prompts из `/dev/tty`). Скрипт
идемпотентен, требует bash 4+, `docker compose`, `curl`, `openssl`, `git` в
curl-режиме.

| Флаг | Env | Действие |
|------|-----|----------|
| `--site-domain` | `SITE_DOMAIN` | публичный домен |
| `--admin-domain` | `ADMIN_DOMAIN` | домен админки/API |
| `--acme-email` | `ACME_EMAIL` | ACME email |
| `--admin-login` | `ADMIN_LOGIN` | логин, дефолт `admin` |
| `--admin-password` | `ADMIN_PASSWORD` | иначе генерируется 24 символа |
| `--site-name` | `SITE_NAME` | заголовок, дефолт `HexaVeil` |
| `--repo` | `HEXAVEIL_REPO_URL` | URL клонирования (дефолт `https://github.com/imcrazymonk-pixel/cms.git`) |
| `--dir` | `INSTALL_DIR` | каталог curl-режима, дефолт `/opt/hexaveil-cms` |
| `--behind-proxy`, `--proxy=host-nginx` | — | override `compose.behind-proxy.yml`, host-nginx конфиги |
| `--adopt-existing` | — | сохранить секреты/данные, `pg_dump` перед migrate |
| `--reset-admin-password` | — | `FORCE_RESET=1` для существующего админа |
| `--reconfigure-domains` | — | разрешить смену доменов на повторном запуске |
| `--no-install-docker` | — | не ставить Docker |
| `--non-interactive` | — | без вопросов; отсутствие доменов/email — ошибка |
| `--dry-run` | — | проверки + `.env` + `caddy validate`, без контейнеров |
| `--help`, `-h` | — | справка |

Порядок: проверки (root, ОС, docker, порты, диск ≥5 ГБ, RAM, DNS — warning) →
`.env` (атомарно, `umask 077`, `chmod 600`, бэкап `.env.bak.<ts>`) →
`up -d db` + `pg_isready` (60 с) → `pg_dump` при существующей `users` →
`run migrate` → `up -d --build` → health API (90 с) → bootstrap админа →
удаление `ADMIN_PASSWORD` из `.env` → ожидание TLS (120 с) / host-nginx →
сводка.

Секреты (`DB_PASS`, `JWT_SECRET`, `APP_ENCRYPTION_KEY`) генерируются только
при отсутствии ключа. Пароль админа пишется в `.install-credentials` (0600)
только если сгенерирован. Определение «стек уже запущен» — по label
`com.docker.compose.project=hexaveil`.

## C.4 `deploy/migrate.sh` — контракт

Запуск: `postgres:16-alpine`, `/bin/sh /migrate.sh`, `/db` = `db/` (ro).
Env: `DB_PASS`, `DB_HOST` (дефолт `db`), `DB_PORT` (`5432`), `DB_USER`
(`cms`), `DB_NAME` (`cms`); из них экспортируются `PGHOST/PGPORT/PGUSER/
PGDATABASE/PGPASSWORD`. `DB_DIR` (дефолт `/db`).

Ledger:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    text PRIMARY KEY,
    checksum   text,
    applied_at timestamptz NOT NULL DEFAULT now()
);
```

Порядок: wait `pg_isready` ≤ 60 с → создать ledger → если
`to_regclass('public.users') IS NULL`, применить
`db/postgres/init/01-schema.sql` и записать версию `init/01-schema.sql` →
`db/postgres/migrations/*.sql`, затем `db/migrations/*.sql` (glob-порядок
имён). `version` = путь относительно `/db` (`postgres/migrations/003-…sql`,
`migrations/2026-…sql`), `checksum` = sha256 файла. Уже записанная версия
пропускается; расхождение checksum — `WARNING`, не ошибка; ошибка SQL —
exit 1 (сервис `restart: "no"`, `app`/`api` не стартуют). В конце —
`applied=N skipped=M`.

## C.5 `deploy/bootstrap_admin.php` — контракт

CLI-only. Env: `ADMIN_LOGIN` (дефолт `admin`), `ADMIN_PASSWORD`,
`ADMIN_EMAIL`, `FORCE_RESET=1`. Placeholder-хеш
`$2y$10$change_this_to_a_real_bcrypt_hash` (и пустой хеш) считается
незаданным.

Поведение: нет пользователя → `INSERT users(login,email,password,role='admin')`
(нужен пароль); placeholder → `UPDATE password`; реальный хеш →
«unchanged»; `FORCE_RESET=1` + пароль → `UPDATE password`.
Коды выхода: `0` — готово/нечего делать, `1` — ошибка БД/хеширования,
`2` — требуется пароль (нет пользователя или placeholder).

## C.6 Образы

| Файл | Контракт |
|------|----------|
| `deploy/Dockerfile.web` | stage 1 `node:20-alpine`: `npm ci --force --no-audit --no-fund` + `npm run build` (`base '/admin/'`); stage 2 `nginx:1.27-alpine`: `/.docker/nginx/default.conf`, `public/`, собранный `dist` → `/var/www/html/web/frontend/dist/`. Контекст — корень репозитория |
| `Dockerfile` (корень) | `php:8.1-fpm`; код из образа; `.env` не копируется (`.dockerignore`); entrypoint без секретов |
| `web/backend/Dockerfile` | FastAPI; **не содержит `COPY .env`**; переменные только через `env_file` |

`web/frontend/dist` остаётся в git для dev-compose, но **не является
источником истины для прода**: продовый `web` собирает SPA из исходников
внутри образа (см. ADR-006).

## C.7 nginx-контракты

`.docker/nginx/default.conf` (внутренний, образ `web`):

- `map $http_x_forwarded_proto $hv_proto { default $http_x_forwarded_proto; "" $scheme; }`
  — сохраняет схему клиента за Caddy/host-nginx;
- во всех `proxy_set_header` — `X-Forwarded-Proto $hv_proto`; в PHP-location
  дополнительно `fastcgi_param HTTP_X_FORWARDED_PROTO $hv_proto`;
- `server_name _;` — домены решает внешний прокси;
- `client_max_body_size 64M` + `PHP_VALUE upload_max_filesize/post_max_size = 64M`;
- bridge-пути → `api:8000`: `^~ /admin/diagnostics/api/`,
  `^~ /admin/settings/save-all-preferences`, `^~ /admin/settings/save-preference`,
  `^~ /admin/finance/api/` (timeout 60s), `/api/`;
- WebSocket `location /api/support/ws` → `api:8000` с `Upgrade`/`Connection`
  и `proxy_read_timeout 3600s`;
- `= /admin` → 302 `/admin/`; `^~ /admin/` → alias
  `/var/www/html/web/frontend/dist/`, `try_files … /admin/index.html`;
- `/` → `index.php`; `~ \.php$` → `fastcgi_pass app:9000`;
- deny для `config|core|db|templates|install|.docker|…|\.env`.

Host-nginx fallback (`deploy/nginx-host/`): `00-upgrade-map.conf`
(`map $http_upgrade $connection_upgrade`) кладётся в `/etc/nginx/conf.d/`;
`bootstrap-http.conf.template` — HTTP-only ACME webroot
`/var/www/certbot`; `site.conf.template` / `admin.conf.template` — TLS-блоки
с `proxy_pass http://127.0.0.1:3000`, `client_max_body_size 64M`;
у админ-домена `location = /` → 302 `/admin/`.

## C.8 `deploy/Caddyfile`

Global `email {$ACME_EMAIL}`; два site-блока `{$SITE_DOMAIN}` и
`{$ADMIN_DOMAIN}`; `encode zstd gzip`; `request_body { max_size 64MB }`;
`reverse_proxy web:80` с `Host`, `X-Real-IP`, `X-Forwarded-Proto {scheme}`;
у админ-домена `redir / /admin/ 302`. TLS и renewal — автоматические ACME.

## C.9 Артефакты установщика

| Путь | Права | Примечание |
|------|-------|-----------|
| `.env` | `0600` | секреты; `ADMIN_PASSWORD` удаляется после bootstrap |
| `.env.bak.<ts>` | `0600` | предыдущая версия при повторном запуске |
| `.install-credentials` | `0600` | `login=…`, `password=…` только для сгенерированного пароля; удалить после сохранения |
| `deploy/backups/pre-migrate-<ts>.sql` | `0600` | дамп перед миграциями; не публиковать |
| `deploy/compose.behind-proxy.yml` | `0644` | создаётся при `--behind-proxy`, маркер `# managed by hexaveil install.sh` |
