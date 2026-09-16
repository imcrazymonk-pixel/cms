<?php
/**
 * Новый редактор постов V2
 * Расширенный: SEO, теги, AI, предпросмотр, автосохранение
 */
$post = $post ?? [];
$isEdit = !empty($post['id']);
$cats = $categories ?? [];
?>
<link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/editor.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/editor.css') ?>">

<!-- ================= ВЕРХНЯЯ ПАНЕЛЬ ПОСТА ================= -->
<div class="editor-topbar">
    <div class="editor-topbar-left">
        <a href="/admin/posts" class="btn btn-ghost btn-sm"><?= icon('chevron-left') ?><span class="hide-mobile">Блог</span></a>
        <span class="editor-topbar-sep">/</span>
        <span class="editor-topbar-title" id="editor-topbar-title"><?= $isEdit ? TemplateEngine::e($post['title'] ?? '') : 'Новый пост' ?></span>
        <div class="editor-topbar-divider"></div>
        <div class="editor-save-status">
            <span id="editor-save-dot" class="editor-save-dot editor-save-dot--saved"></span>
            <span id="editor-save-text" class="editor-save-text"><?= $isEdit ? 'Загружено' : 'Новый пост' ?></span>
        </div>
    </div>
    <div class="editor-topbar-right">
        <button type="button" class="btn btn-ghost btn-sm" onclick="toggleAiDrawer()" title="AI Ассистент">
            <?= icon('sparkles') ?><span class="hide-mobile">AI</span>
        </button>
        <button type="button" class="btn btn-ghost btn-sm" onclick="runTypographer()" title="Автотипографика">
            <?= icon('type') ?>
        </button>
        <button type="button" class="btn btn-ghost btn-sm" onclick="openPreviewModal()" title="Предпросмотр">
            <?= icon('eye') ?><span class="hide-mobile">Предпросмотр</span>
        </button>
        <button type="button" class="btn btn-ghost btn-sm" onclick="manualSaveDraft()" title="Сохранить черновик">
            <?= icon('save') ?><span class="hide-mobile">Черновик</span>
        </button>
        <button type="button" class="btn btn-primary btn-sm" onclick="openPublishModal()">
            <?= icon('send') ?><span class="hide-mobile">Опубликовать</span>
        </button>
        <div class="editor-topbar-divider"></div>
        <button type="button" class="btn-icon" id="editor-sidebar-toggle" onclick="toggleSidebar()" title="Настройки">
            <?= icon('panel-right') ?>
        </button>
    </div>
</div>

<!-- ================= ОСНОВНОЙ КОНТЕЙНЕР ================= -->
<div class="editor-layout">
    <!-- Центральная область — редактор -->
    <div class="editor-main" id="editor-scroll-container">
        <div class="editor-content">

            <!-- Скрытая форма для отправки -->
            <form method="POST" id="editor-form" action="<?= $isEdit ? '/admin/posts/v2/update/' . $post['id'] : '/admin/posts/v2/store' ?>">
                <?= csrf_field() ?>

                <!-- Обложка -->
                <div id="editor-cover-container" class="editor-cover-container hidden">
                    <img id="editor-cover-preview" src="" alt="Обложка" class="editor-cover-img">
                    <div class="editor-cover-overlay">
                        <label class="btn btn-ghost btn-sm"><?= icon('upload') ?> Заменить<input type="file" accept="image/*" class="hidden" onchange="handleCoverUpload(event)"></label>
                        <button type="button" class="btn btn-ghost btn-sm btn-danger" onclick="removeCoverImage()"><?= icon('trash-2') ?> Удалить</button>
                    </div>
                </div>
                <div id="editor-cover-placeholder" class="editor-cover-placeholder">
                    <label class="editor-cover-add"><?= icon('image-plus') ?> Добавить обложку<input type="file" accept="image/*" class="hidden" onchange="handleCoverUpload(event)"></label>
                </div>

                <!-- Заголовок -->
                <textarea id="editor-title" name="title"
                    rows="1" placeholder="Заголовок поста..."
                    oninput="autoResizeTextarea(this); onTitleChange(this.value);"
                    class="editor-title-input"><?= TemplateEngine::e($post['title'] ?? '') ?></textarea>

                <!-- Лид / подзаголовок -->
                <textarea id="editor-lead" name="excerpt"
                    rows="2" placeholder="Короткое введение (отображается в карточке блога)..."
                    oninput="autoResizeTextarea(this); triggerContentChange();"
                    class="editor-lead-input"><?= TemplateEngine::e($post['excerpt'] ?? '') ?></textarea>

                <!-- TinyMCE редактор -->
                <div class="editor-tinymce-wrapper">
                    <textarea id="content" name="content" class="editor"><?= TemplateEngine::e($post['content'] ?? '') ?></textarea>
                </div>

                <!-- Скрытые поля для дополнительных данных -->
                <input type="hidden" name="tags" id="editor-tags-hidden" value="">
                <input type="hidden" name="status" id="editor-status-hidden" value="<?= TemplateEngine::e($post['status'] ?? 'draft') ?>">
                <input type="hidden" name="publish_date" id="editor-publish-date-hidden" value="">
                <input type="hidden" name="image" id="editor-image-hidden" value="<?= TemplateEngine::e($post['image'] ?? '') ?>">
                <input type="hidden" name="slug" id="editor-slug-hidden" value="<?= TemplateEngine::e($post['slug'] ?? '') ?>">
                <input type="hidden" name="seo_title" id="editor-seo-title-hidden" value="">
                <input type="hidden" name="seo_description" id="editor-seo-description-hidden" value="">
                <input type="hidden" name="category_id" id="editor-category-hidden" value="<?= $post['category_id'] ?? '' ?>">
            </form>

        </div>
    </div>

    <!-- Правый сайдбар — настройки поста -->
    <aside class="editor-sidebar" id="editor-sidebar">
        <!-- Вкладки -->
        <div class="editor-sidebar-tabs">
            <button type="button" class="editor-sidebar-tab active" id="editor-tab-btn-general" onclick="switchSidebarTab('general')">Параметры</button>
            <button type="button" class="editor-sidebar-tab" id="editor-tab-btn-seo" onclick="switchSidebarTab('seo')">SEO</button>
        </div>

        <!-- ВКЛАДКА: Параметры -->
        <div class="editor-sidebar-panel" id="editor-tab-general">
            <!-- Статус -->
            <div class="editor-sb-section">
                <label class="editor-sb-label">Статус</label>
                <div class="editor-sb-status-bar">
                    <span id="editor-status-badge" class="badge badge-<?= $post['status'] ?? 'draft' ?>"><?= $post['status'] === 'published' ? 'Опубликован' : ($post['status'] === 'archived' ? 'Архив' : 'Черновик') ?></span>
                    <div class="editor-sb-status-actions">
                        <button type="button" class="btn btn-ghost btn-xs" onclick="setPostStatus('draft')">Черновик</button>
                        <button type="button" class="btn btn-ghost btn-xs" onclick="setPostStatus('published')">Опубликовать</button>
                    </div>
                </div>
            </div>

            <!-- Дата публикации -->
            <div class="editor-sb-section">
                <label class="editor-sb-label" for="editor-publish-date-input">Дата публикации</label>
                <input type="datetime-local" id="editor-publish-date-input" class="form-control" value="">
            </div>

            <div class="editor-sb-divider"></div>

            <!-- Slug -->
            <div class="editor-sb-section">
                <label class="editor-sb-label">URL (ЧПУ)</label>
                <div class="editor-sb-slug">
                    <span class="editor-sb-slug-prefix">/blog/</span>
                    <input type="text" id="editor-slug-input" class="editor-sb-slug-input"
                        value="<?= TemplateEngine::e($post['slug'] ?? '') ?>"
                        placeholder="url-post"
                        oninput="onSlugChange(this.value)">
                </div>
            </div>

            <div class="editor-sb-divider"></div>

            <!-- Категория -->
            <div class="editor-sb-section">
                <label class="editor-sb-label" for="editor-category-select">Рубрика</label>
                <select id="editor-category-select" class="form-control" onchange="onCategoryChange(this.value)">
                    <option value="">Без категории</option>
                    <?php foreach ($cats as $cat): ?>
                    <option value="<?= $cat['id'] ?>" <?= (($post['category_id'] ?? 0) == $cat['id']) ? 'selected' : '' ?>>
                        <?= TemplateEngine::e($cat['name']) ?>
                    </option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div class="editor-sb-divider"></div>

            <!-- Теги -->
            <div class="editor-sb-section">
                <label class="editor-sb-label">Теги</label>
                <div class="editor-tags" id="editor-tags-container">
                    <?php if (!empty($post['tags'])): ?>
                        <?php foreach ($post['tags'] as $tag): ?>
                        <span class="editor-tag">
                            #<?= TemplateEngine::e($tag['name']) ?>
                            <button type="button" class="editor-tag-remove" onclick="removeTag(this)">&times;</button>
                        </span>
                        <?php endforeach; ?>
                    <?php endif; ?>
                </div>
                <input type="text" id="editor-tag-input" class="form-control"
                    placeholder="Добавить тег (Enter)..."
                    onkeydown="handleTagKeydown(event)">
            </div>

            <div class="editor-sb-divider"></div>

            <!-- Доп. опции -->
            <div class="editor-sb-section">
                <label class="editor-sb-checkbox">
                    <input type="checkbox" id="editor-featured" <?= !empty($post['featured']) ? 'checked' : '' ?>>
                    <span>Закрепить в топе блога</span>
                </label>
                <label class="editor-sb-checkbox">
                    <input type="checkbox" id="editor-comments-enabled" checked>
                    <span>Разрешить комментарии</span>
                </label>
            </div>

            <div class="editor-sb-divider"></div>

            <!-- Метрики -->
            <div class="editor-sb-section">
                <label class="editor-sb-label">Метрики текста</label>
                <div class="editor-sb-metrics">
                    <div class="editor-sb-metric">
                        <span class="editor-sb-metric-label">Слов</span>
                        <span class="editor-sb-metric-value" id="editor-stat-words">0</span>
                    </div>
                    <div class="editor-sb-metric">
                        <span class="editor-sb-metric-label">Символов</span>
                        <span class="editor-sb-metric-value" id="editor-stat-chars">0</span>
                    </div>
                    <div class="editor-sb-metric">
                        <span class="editor-sb-metric-label">Чтение</span>
                        <span class="editor-sb-metric-value" id="editor-stat-reading">~0 мин</span>
                    </div>
                    <div class="editor-sb-metric">
                        <span class="editor-sb-metric-label">Абзацев</span>
                        <span class="editor-sb-metric-value" id="editor-stat-paragraphs">0</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- ВКЛАДКА: SEO -->
        <div class="editor-sidebar-panel hidden" id="editor-tab-seo">
            <!-- SERP Preview -->
            <div class="editor-sb-section">
                <label class="editor-sb-label">Результат поиска Google</label>
                <div class="editor-serp-preview">
                    <div class="editor-serp-url">hexacms.ru › blog › <span id="editor-serp-slug"><?= TemplateEngine::e($post['slug'] ?? 'url-post') ?></span></div>
                    <div class="editor-serp-title" id="editor-serp-title"><?= TemplateEngine::e($post['title'] ?? 'Заголовок поста') ?></div>
                    <div class="editor-serp-desc" id="editor-serp-desc"><?= TemplateEngine::e($post['excerpt'] ?? 'Описание поста в результатах поиска...') ?></div>
                </div>
            </div>

            <div class="editor-sb-divider"></div>

            <!-- Meta Title -->
            <div class="editor-sb-section">
                <div class="editor-sb-label-row">
                    <label class="editor-sb-label">SEO Заголовок (Title)</label>
                    <span class="editor-sb-counter" id="editor-meta-title-counter">0 / 70</span>
                </div>
                <input type="text" id="editor-meta-title" class="form-control"
                    value="<?= TemplateEngine::e($post['title'] ?? '') ?>"
                    oninput="onMetaTitleChange(this.value)"
                    placeholder="SEO-заголовок (до 70 символов)">
            </div>

            <!-- Meta Description -->
            <div class="editor-sb-section">
                <div class="editor-sb-label-row">
                    <label class="editor-sb-label">Meta Description</label>
                    <span class="editor-sb-counter" id="editor-meta-desc-counter">0 / 160</span>
                </div>
                <textarea id="editor-meta-desc" class="form-control" rows="3"
                    oninput="onMetaDescChange(this.value)"
                    placeholder="Краткое описание (до 160 символов)"><?= TemplateEngine::e($post['excerpt'] ?? '') ?></textarea>
            </div>

            <div class="editor-sb-divider"></div>

            <!-- Canonical URL -->
            <div class="editor-sb-section">
                <label class="editor-sb-label">Канонический URL</label>
                <input type="text" id="editor-canonical" class="form-control" placeholder="(совпадает с URL поста)">
            </div>

            <div class="editor-sb-divider"></div>

            <!-- OpenGraph -->
            <div class="editor-sb-section">
                <label class="editor-sb-label">Open Graph</label>
                <div class="editor-og-status">
                    <?= icon('check-circle-2') ?>
                    <span>OG:Image, OG:Title сформированы автоматически</span>
                </div>
            </div>
        </div>
    </aside>
</div>

<!-- ================= МОДАЛКА ПРЕДПРОСМОТРА ================= -->
<div id="editor-preview-modal" class="modal-overlay hidden">
    <div class="modal editor-preview-modal">
        <div class="modal-header">
            <div class="modal-header-left">
                <span class="modal-title"><?= icon('eye') ?> Предпросмотр поста</span>
                <div class="editor-preview-devices">
                    <button type="button" class="btn btn-ghost btn-xs active" id="preview-btn-desktop" onclick="setPreviewDevice('desktop')">ПК</button>
                    <button type="button" class="btn btn-ghost btn-xs" id="preview-btn-mobile" onclick="setPreviewDevice('mobile')">Смартфон</button>
                </div>
            </div>
            <button type="button" class="btn-icon" onclick="closePreviewModal()"><?= icon('x') ?></button>
        </div>
        <div class="modal-body editor-preview-body">
            <article id="preview-article" class="editor-preview-article">
                <div class="editor-preview-category" id="preview-category-badge"><?= TemplateEngine::e($cats[0]['name'] ?? 'Без категории') ?></div>
                <h1 class="editor-preview-h1" id="preview-title"></h1>
                <div class="editor-preview-meta">
                    <span>Автор: Редакция</span>
                    <span>•</span>
                    <span id="preview-date">Сегодня</span>
                    <span>•</span>
                    <span id="preview-reading-time">~1 мин чтения</span>
                </div>
                <div id="preview-cover-box" class="editor-preview-cover-box hidden">
                    <img id="preview-cover-img" src="" alt="Обложка">
                </div>
                <p class="editor-preview-lead" id="preview-lead"></p>
                <div class="editor-preview-content" id="preview-content"></div>
            </article>
        </div>
    </div>
</div>

<!-- ================= МОДАЛКА ПУБЛИКАЦИИ ================= -->
<div id="editor-publish-modal" class="modal-overlay hidden">
    <div class="modal editor-publish-modal">
        <div class="editor-publish-icon"><?= icon('send') ?></div>
        <h3 class="editor-publish-title">Опубликовать пост?</h3>
        <p class="editor-publish-desc">Пост появится в открытом доступе на сайте</p>
        <div class="editor-publish-info">
            <div class="editor-publish-info-row">
                <span class="editor-publish-info-label">URL:</span>
                <span class="editor-publish-info-value" id="publish-modal-url">/blog/<?= $post['slug'] ?? 'url-post' ?></span>
            </div>
            <div class="editor-publish-info-row">
                <span class="editor-publish-info-label">Рубрика:</span>
                <span class="editor-publish-info-value" id="publish-modal-cat"><?= $cats[0]['name'] ?? 'Без категории' ?></span>
            </div>
            <div class="editor-publish-info-row">
                <span class="editor-publish-info-label">Режим:</span>
                <span class="editor-publish-info-value editor-publish-mode">Мгновенная публикация</span>
            </div>
        </div>
        <div class="editor-publish-actions">
            <button type="button" class="btn btn-secondary" onclick="closePublishModal()">Отмена</button>
            <button type="button" class="btn btn-primary" onclick="confirmPublish()"><?= icon('check') ?> Опубликовать сейчас</button>
        </div>
    </div>
</div>

<!-- ================= AI DRAWER ================= -->
<div id="editor-ai-drawer" class="editor-drawer hidden">
    <div class="editor-drawer-header">
        <div class="editor-drawer-title">
            <?= icon('sparkles') ?>
            <div>
                <span class="editor-drawer-title-text">AI Ассистент</span>
                <span class="editor-drawer-subtitle">Копирайтинг и редактура</span>
            </div>
        </div>
        <button type="button" class="btn-icon" onclick="toggleAiDrawer()"><?= icon('x') ?></button>
    </div>
    <div class="editor-drawer-body">
        <div class="editor-ai-section">
            <label class="editor-ai-label">Быстрые сценарии:</label>
            <button type="button" class="btn btn-ghost btn-sm btn-block" onclick="runAiScenario('improve')">
                <?= icon('wand-2') ?> Улучшить читаемость
            </button>
            <button type="button" class="btn btn-ghost btn-sm btn-block" onclick="runAiScenario('summarize')">
                <?= icon('file-text') ?> Сделать краткий вывод
            </button>
            <button type="button" class="btn btn-ghost btn-sm btn-block" onclick="runAiScenario('catchy-title')">
                <?= icon('sparkle') ?> Предложить заголовки
            </button>
        </div>

        <div class="editor-ai-section">
            <label class="editor-ai-label">Произвольная задача:</label>
            <textarea id="editor-ai-prompt" class="form-control" rows="3"
                placeholder="Например: добавь сравнительную таблицу..."></textarea>
        </div>

        <button type="button" class="btn btn-primary btn-block" id="editor-ai-generate" onclick="executeAiGeneration()">
            <?= icon('sparkles') ?> Запустить генерацию
        </button>

        <div id="editor-ai-result" class="editor-ai-result hidden">
            <div class="editor-ai-result-header">
                <span class="editor-ai-result-label">Рекомендация AI:</span>
                <button type="button" class="btn btn-ghost btn-xs" onclick="applyAiTextToArticle()">Вставить</button>
            </div>
            <div id="editor-ai-result-text" class="editor-ai-result-text"></div>
        </div>
    </div>
</div>

<!-- ================= TOAST ================= -->
<div id="editor-toast" class="editor-toast hidden">
    <?= icon('check-circle-2') ?>
    <span id="editor-toast-msg">Сохранено</span>
</div>

<script src="<?= SITE_URL ?>/admin/js/editor.js?v=<?= filemtime(ADMIN_PATH . '/js/editor.js') ?>"></script>