/**
 * Editor V2 — новый редактор постов
 * Полноэкранный редактор с правым сайдбаром (Параметры/SEO)
 * Работает параллельно со старым редактором
 */

(function() {
    'use strict';

    // ─── Состояние редактора ───────────────────────
    const state = {
        isDirty: false,
        isPublished: false,
        coverUrl: '',
        tags: [],
        slugUserEdited: false,
        currentStatus: document.getElementById('editor-status-hidden')?.value || 'draft',
    };

    // ─── DOM references ────────────────────────────
    const $ = id => document.getElementById(id);
    const titleEl = $('editor-title');
    const slugInput = $('editor-slug-input');
    const slugHidden = $('editor-slug-hidden');
    const leadEl = $('editor-lead');
    const contentField = $('content');
    const statusHidden = $('editor-status-hidden');
    const categorySelect = $('editor-category-select');
    const categoryHidden = $('editor-category-hidden');
    const tagsContainer = $('editor-tags-container');
    const tagInput = $('editor-tag-input');
    const tagsHidden = $('editor-tags-hidden');
    const publishDateInput = $('editor-publish-date-input');
    const publishDateHidden = $('editor-publish-date-hidden');
    const confirmBtn = document.querySelector('.btn-primary[onclick*="confirmPublish"]');
    const form = $('editor-form');

    // ─── Адаптер для доступа к контенту ────────────
    // Сейчас TinyMCE. При замене редактора меняем только эти 2 функции
    function getEditorContent() {
        if (typeof tinymce !== 'undefined' && tinymce.get('content')) {
            return tinymce.get('content').getContent();
        }
        return contentField ? contentField.value : '';
    }

    function setEditorContent(html) {
        if (typeof tinymce !== 'undefined' && tinymce.get('content')) {
            tinymce.get('content').setContent(html);
        } else if (contentField) {
            contentField.value = html;
        }
    }

    function getEditorText() {
        if (typeof tinymce !== 'undefined' && tinymce.get('content')) {
            return tinymce.get('content').getContent({ format: 'text' });
        }
        const el = contentField;
        return el ? el.value.replace(/<[^>]*>/g, '') : '';
    }

    // ─── Инициализация ─────────────────────────────
    function init() {
        // Устанавливаем дату по умолчанию
        setDefaultPublishDate();

        // Загружаем теги (из скрытых или из DOM)
        loadTagsFromDOM();

        // Метрики
        recalculateStats();

        // Подписываемся на TinyMCE init
        if (typeof tinymce !== 'undefined') {
            tinymce.on('AddedEditor', function(e) {
                const editor = e.editor;
                if (editor.id === 'content') {
                    editor.on('change', function() {
                        triggerContentChange();
                    });
                    editor.on('keyup', function() {
                        recalculateStats();
                    });
                }
            });
        }

        // Если TinyMCE уже инициализирован
        setTimeout(function() {
            if (typeof tinymce !== 'undefined' && tinymce.get('content')) {
                const editor = tinymce.get('content');
                editor.on('change', triggerContentChange);
                editor.on('keyup', recalculateStats);
            }
            // Принудительный пересчёт метрик через 1с
            setTimeout(recalculateStats, 1000);
        }, 500);
    }

    // ─── Установка даты ────────────────────────────
    function setDefaultPublishDate() {
        const existing = publishDateInput?.dataset?.existing;
        if (existing) {
            publishDateInput.value = existing;
        } else {
            const now = new Date();
            now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
            publishDateInput.value = now.toISOString().slice(0, 16);
        }
    }

    // ─── Авто-высота textarea ──────────────────────
    window.autoResizeTextarea = function(el) {
        el.style.height = 'auto';
        el.style.height = el.scrollHeight + 'px';
    };

    // ─── Изменение заголовка ───────────────────────
    window.onTitleChange = function(val) {
        const topbar = $('editor-topbar-title');
        if (topbar) topbar.textContent = val.trim() || 'Новый пост';

        // SERP preview
        $('editor-serp-title').textContent = val.trim() || 'Заголовок поста';
        $('editor-meta-title').value = val.trim();
        updateMetaTitleCounter(val);

        // Авто-slug (только если не редактировался вручную)
        if (!state.slugUserEdited) {
            const slug = transliterate(val.trim().toLowerCase());
            if (slugInput) slugInput.value = slug;
            if (slugHidden) slugHidden.value = slug;
            $('editor-serp-slug').textContent = slug || 'url-post';
        }

        triggerContentChange();
    };

    // ─── Slug ──────────────────────────────────────
    window.onSlugChange = function(val) {
        state.slugUserEdited = true;
        if (slugHidden) slugHidden.value = val;
        $('editor-serp-slug').textContent = val || 'url-post';
        triggerContentChange();
    };

    // ─── Категория ─────────────────────────────────
    window.onCategoryChange = function(val) {
        if (categoryHidden) categoryHidden.value = val;
        triggerContentChange();
    };

    // ─── SEO ───────────────────────────────────────
    window.onMetaTitleChange = function(val) {
        $('editor-serp-title').textContent = val || 'Заголовок поста';
        updateMetaTitleCounter(val);
        triggerContentChange();
    };

    window.onMetaDescChange = function(val) {
        $('editor-serp-desc').textContent = val || 'Описание поста...';
        const counter = $('editor-meta-desc-counter');
        if (counter) counter.textContent = val.length + ' / 160';
        triggerContentChange();
    };

    function updateMetaTitleCounter(val) {
        const counter = $('editor-meta-title-counter');
        if (counter) counter.textContent = val.length + ' / 70';
    }

    // ─── Контент изменился ─────────────────────────
    window.triggerContentChange = function() {
        state.isDirty = true;
        updateSaveStatus('dirty', 'Есть несохранённые правки');
        recalculateStats();
    };

    function updateSaveStatus(mode, text) {
        const dot = $('editor-save-dot');
        const txt = $('editor-save-text');
        if (!dot || !txt) return;
        dot.className = 'editor-save-dot editor-save-dot--' + mode;
        txt.textContent = text;
    }

    function markSaved() {
        state.isDirty = false;
        const now = new Date();
        const time = now.getHours().toString().padStart(2, '0') + ':' +
                     now.getMinutes().toString().padStart(2, '0');
        updateSaveStatus('saved', 'Сохранено в ' + time);
    }

    // ─── Мануальное сохранение ─────────────────────
    window.manualSaveDraft = function() {
        syncHiddenFields();
        state.currentStatus = 'draft';
        if (statusHidden) statusHidden.value = 'draft';
        form.submit();
        markSaved();
        showToast('Черновик сохранён');
    };

    // ─── Синхронизация скрытых полей ───────────────
    function syncHiddenFields() {
        // Sync tags
        if (tagsHidden) {
            tagsHidden.value = JSON.stringify(state.tags);
        }

        // Sync slug
        if (slugHidden && slugInput) {
            slugHidden.value = slugInput.value;
        }

        // Sync date
        if (publishDateHidden && publishDateInput) {
            publishDateHidden.value = publishDateInput.value;
        }

        // Sync category
        if (categoryHidden && categorySelect) {
            categoryHidden.value = categorySelect.value;
        }

        // Sync status
        if (statusHidden) {
            statusHidden.value = state.currentStatus;
        }

        // Sync SEO
        const seoTitle = $('editor-meta-title');
        const seoDesc = $('editor-meta-desc');
        const seoTitleHidden = $('editor-seo-title-hidden');
        const seoDescHidden = $('editor-seo-description-hidden');
        if (seoTitleHidden && seoTitle) seoTitleHidden.value = seoTitle.value;
        if (seoDescHidden && seoDesc) seoDescHidden.value = seoDesc.value;
    }

    // ─── Статус ────────────────────────────────────
    window.setPostStatus = function(status) {
        state.currentStatus = status;
        if (statusHidden) statusHidden.value = status;
        const badge = $('editor-status-badge');
        if (badge) {
            badge.className = 'badge badge-' + status;
            const labels = { draft: 'Черновик', published: 'Опубликован', archived: 'Архив' };
            badge.textContent = labels[status] || status;
        }
    };

    // ─── Публикация ────────────────────────────────
    window.openPublishModal = function() {
        const catSelect = categorySelect;
        const catText = catSelect ? catSelect.options[catSelect.selectedIndex]?.text : 'Без категории';
        $('publish-modal-cat').textContent = catText;

        const slug = slugInput ? slugInput.value : 'url-post';
        $('publish-modal-url').textContent = '/blog/' + slug;

        $('editor-publish-modal').classList.remove('hidden');
    };

    window.closePublishModal = function() {
        $('editor-publish-modal').classList.add('hidden');
    };

    window.confirmPublish = function() {
        state.currentStatus = 'published';
        if (statusHidden) statusHidden.value = 'published';
        closePublishModal();
        setPostStatus('published');
        syncHiddenFields();
        form.submit();
        showToast('Пост опубликован!');
    };

    // ─── Теги ──────────────────────────────────────
    window.handleTagKeydown = function(e) {
        if (e.key !== 'Enter') return;
        e.preventDefault();
        const input = tagInput;
        let tag = input.value.trim();
        if (!tag) return;
        if (!tag.startsWith('#')) tag = '#' + tag;

        state.tags.push(tag);
        renderTags();
        input.value = '';
        triggerContentChange();
    };

    window.removeTag = function(btn) {
        const span = btn.parentElement;
        const tagText = span.textContent.replace('×', '').trim();
        state.tags = state.tags.filter(function(t) { return t !== tagText; });
        span.remove();
        triggerContentChange();
    };

    function renderTags() {
        if (!tagsContainer) return;
        tagsContainer.innerHTML = '';
        state.tags.forEach(function(tag) {
            const span = document.createElement('span');
            span.className = 'editor-tag';
            span.innerHTML = tag + ' <button type="button" class="editor-tag-remove" onclick="removeTag(this)">&times;</button>';
            tagsContainer.appendChild(span);
        });
    }

    function loadTagsFromDOM() {
        const existingTags = tagsContainer ? tagsContainer.querySelectorAll('.editor-tag') : [];
        state.tags = [];
        existingTags.forEach(function(el) {
            const text = el.textContent.replace('×', '').trim();
            if (text) state.tags.push(text);
        });
    }

    // ─── Статистика ────────────────────────────────
    function recalculateStats() {
        const titleText = titleEl ? titleEl.value : '';
        const bodyText = getEditorText();
        const fullText = titleText + ' ' + bodyText;

        const words = fullText.trim().split(/\s+/).filter(Boolean).length;
        const chars = fullText.length;

        // Считаем абзацы в html
        let paragraphs = 0;
        const html = getEditorContent();
        if (html) {
            const matches = html.match(/<p[^>]*>/g);
            paragraphs = matches ? matches.length : 0;
        }

        const readMin = Math.max(1, Math.ceil(words / 170));

        const setStat = function(id, val) {
            const el = $(id);
            if (el) el.textContent = val;
        };

        setStat('editor-stat-words', words);
        setStat('editor-stat-chars', chars);
        setStat('editor-stat-reading', '~' + readMin + ' мин');
        setStat('editor-stat-paragraphs', paragraphs);
    }

    // ─── Сайдбар ───────────────────────────────────
    window.toggleSidebar = function() {
        const sb = $('editor-sidebar');
        if (sb) sb.classList.toggle('hidden');
    };

    window.switchSidebarTab = function(tab) {
        const tabGeneral = $('editor-tab-general');
        const tabSeo = $('editor-tab-seo');
        const btnGeneral = $('editor-tab-btn-general');
        const btnSeo = $('editor-tab-btn-seo');

        if (tab === 'general') {
            tabGeneral.classList.remove('hidden');
            tabSeo.classList.add('hidden');
            btnGeneral.className = 'editor-sidebar-tab active';
            btnSeo.className = 'editor-sidebar-tab';
        } else {
            tabSeo.classList.remove('hidden');
            tabGeneral.classList.add('hidden');
            btnSeo.className = 'editor-sidebar-tab active';
            btnGeneral.className = 'editor-sidebar-tab';
        }
    };

    // ─── Предпросмотр ──────────────────────────────
    window.openPreviewModal = function() {
        const catSelect = categorySelect;
        const catText = catSelect ? catSelect.options[catSelect.selectedIndex]?.text : '';

        $('preview-category-badge').textContent = catText;
        $('preview-title').textContent = titleEl ? titleEl.value : '';
        $('preview-lead').textContent = leadEl ? leadEl.value : '';
        $('preview-content').innerHTML = getEditorContent();

        const coverBox = $('preview-cover-box');
        if (state.coverUrl) {
            $('preview-cover-img').src = state.coverUrl;
            coverBox.classList.remove('hidden');
        } else {
            coverBox.classList.add('hidden');
        }

        // Reading time
        const words = (titleEl ? titleEl.value : '').split(/\s+/).filter(Boolean).length +
                      (leadEl ? leadEl.value : '').split(/\s+/).filter(Boolean).length;
        const readMin = Math.max(1, Math.ceil(words / 170));
        $('preview-reading-time').textContent = '~' + readMin + ' мин чтения';

        $('editor-preview-modal').classList.remove('hidden');
    };

    window.closePreviewModal = function() {
        $('editor-preview-modal').classList.add('hidden');
    };

    window.setPreviewDevice = function(dev) {
        const article = $('preview-article');
        const btnDesk = $('preview-btn-desktop');
        const btnMob = $('preview-btn-mobile');

        if (dev === 'mobile') {
            article.className = 'editor-preview-article max-w-sm';
            btnMob.className = 'btn btn-ghost btn-xs active';
            btnDesk.className = 'btn btn-ghost btn-xs';
        } else {
            article.className = 'editor-preview-article';
            btnDesk.className = 'btn btn-ghost btn-xs active';
            btnMob.className = 'btn btn-ghost btn-xs';
        }
    };

    // ─── AI Ассистент ──────────────────────────────
    window.toggleAiDrawer = function() {
        const drawer = $('editor-ai-drawer');
        if (drawer) drawer.classList.toggle('hidden');
    };

    window.runAiScenario = function(type) {
        const promptInput = $('editor-ai-prompt');
        var prompts = {
            improve: 'Улучши читаемость статьи, сделай формулировки точнее и динамичнее',
            summarize: 'Сделай краткое резюме ключевых выводов статьи (3-4 тезиса)',
            'catchy-title': 'Предложи 5 привлекательных вариантов заголовка для блога'
        };
        if (promptInput && prompts[type]) {
            promptInput.value = prompts[type];
        }
        executeAiGeneration();
    };

    window.executeAiGeneration = function() {
        var prompt = ($('editor-ai-prompt') ? $('editor-ai-prompt').value : '') || 'Улучши читаемость статьи';
        var btn = $('editor-ai-generate');
        var resultBox = $('editor-ai-result');
        var resultText = $('editor-ai-result-text');

        btn.disabled = true;
        btn.innerHTML = '✦ Обработка...';

        var articleText = getEditorText().slice(0, 1200);
        var payload = {
            prompt: prompt,
            article: articleText
        };

        // Симуляция AI (заглушка)
        setTimeout(function() {
            var fallbacks = [
                'Добавьте больше практических примеров конфигурации для наглядности.',
                'Рекомендуется разбить длинные абзацы на более короткие для улучшения читаемости.',
                'Хорошая структура! Можно добавить сравнительную таблицу в разделе с цифрами.',
                'Попробуйте начать раздел с вопроса к читателю — это повышает вовлечённость.'
            ];
            var reply = fallbacks[Math.floor(Math.random() * fallbacks.length)];

            if (resultBox) resultBox.classList.remove('hidden');
            if (resultText) resultText.textContent = reply;

            btn.disabled = false;
            btn.innerHTML = '✦ Запустить генерацию';
        }, 800);
    };

    window.applyAiTextToArticle = function() {
        var text = $('editor-ai-result-text');
        if (!text) return;
        var html = '<p>' + text.textContent + '</p>';
        var current = getEditorContent();
        setEditorContent(current + html);
        toggleAiDrawer();
        triggerContentChange();
        showToast('Текст добавлен в пост');
    };

    // ─── Обложка ───────────────────────────────────
    window.handleCoverUpload = function(e) {
        var file = e.target.files[0];
        if (!file) return;

        var reader = new FileReader();
        reader.onload = function(event) {
            state.coverUrl = event.target.result;
            var preview = $('editor-cover-preview');
            var container = $('editor-cover-container');
            var placeholder = $('editor-cover-placeholder');
            if (preview) preview.src = state.coverUrl;
            if (container) container.classList.remove('hidden');
            if (placeholder) placeholder.classList.add('hidden');
            triggerContentChange();
            showToast('Обложка загружена');
        };
        reader.readAsDataURL(file);
    };

    window.removeCoverImage = function() {
        state.coverUrl = '';
        var container = $('editor-cover-container');
        var placeholder = $('editor-cover-placeholder');
        if (container) container.classList.add('hidden');
        if (placeholder) placeholder.classList.remove('hidden');
        triggerContentChange();
        showToast('Обложка удалена');
    };

    // ─── Типограф ──────────────────────────────────
    window.runTypographer = function() {
        var html = getEditorContent();

        // Кавычки «елочки» — упрощённая версия
        html = html.replace(/(^|[\s(])"([^\s"][^"]*)"/g, '$1«$2»');
        // Тире
        html = html.replace(/(\s)-(\s)/g, '$1—$2');
        html = html.replace(/--/g, '—');

        setEditorContent(html);
        triggerContentChange();
        showToast('Типографика: кавычки, тире');
    };

    // ─── Транслитерация ────────────────────────────
    function transliterate(word) {
        var map = {
            'а':'a','б':'b','в':'v','г':'g','д':'d',
            'е':'e','ё':'yo','ж':'zh','з':'z','и':'i',
            'й':'y','к':'k','л':'l','м':'m','н':'n',
            'о':'o','п':'p','р':'r','с':'s','т':'t',
            'у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch',
            'ш':'sh','щ':'shch','ъ':'','ы':'y','ь':'',
            'э':'e','ю':'yu','я':'ya'
        };
        return word.split('').map(function(c) {
            return map[c] || (c.match(/[a-z0-9-]/i) ? c.toLowerCase() : '-');
        }).join('').replace(/-+/g, '-').replace(/^-|-$/g, '');
    }

    // ─── Toast ──────────────────────────────────────
    function showToast(msg) {
        var toast = $('editor-toast');
        var toastMsg = $('editor-toast-msg');
        if (!toast || !toastMsg) return;
        toastMsg.textContent = msg;
        toast.classList.remove('hidden');
        setTimeout(function() {
            toast.classList.add('hidden');
        }, 3000);
    }

    // ─── Запуск при загрузке страницы ──────────────
    if (document.readyState === 'complete') {
        init();
    } else {
        window.addEventListener('load', init);
    }

})();