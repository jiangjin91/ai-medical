<script setup>
import { reactive, ref } from 'vue'
import { searchKnowledge } from '../api/medical'

const ENTRY_TYPES = [
  { value: '', label: '全部类型' },
  { value: 'drug_label', label: '药品说明书' },
  { value: 'guideline', label: '临床指南' },
  { value: 'interaction', label: '相互作用' },
  { value: 'contraindication', label: '禁忌' },
  { value: 'local_rule', label: '机构规则' },
]

const filters = reactive({ q: '', entryType: '', medicationId: '' })
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const error = ref('')
const result = ref(null) // KnowledgeSearchData
const expandedId = ref(null)

async function search(targetPage = 1) {
  if (!filters.q.trim() && !filters.medicationId.trim()) {
    error.value = '请输入关键词或药品 ID。'
    return
  }
  page.value = targetPage
  loading.value = true
  error.value = ''
  try {
    result.value = await searchKnowledge({
      q: filters.q.trim(),
      entryType: filters.entryType || undefined,
      medicationId: filters.medicationId.trim() || undefined,
      page: targetPage,
      pageSize,
    })
  } catch (err) {
    result.value = null
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function totalPages() {
  return Math.max(1, Math.ceil((result.value?.pagination?.total ?? 0) / pageSize))
}
</script>

<template>
  <section class="panel-card">
    <header class="panel-header">
      <h2 class="panel-title">药学知识库</h2>
      <p class="panel-subtitle">仅检索已发布、生效期内的权威知识（带版本可追溯）</p>
    </header>

    <div class="search-area">
      <input v-model="filters.q" type="text" class="app-input" placeholder="关键词，如：华法林 相互作用" @keyup.enter="search(1)" />
      <div class="filter-row">
        <select v-model="filters.entryType" class="app-select" style="flex:1">
          <option v-for="item in ENTRY_TYPES" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <input v-model="filters.medicationId" type="text" class="app-input med-id" placeholder="药品ID" @keyup.enter="search(1)" />
        <button type="button" class="app-button primary" :disabled="loading" @click="search(1)">
          {{ loading ? '检索中…' : '检索' }}
        </button>
      </div>
    </div>

    <p v-if="error" class="error-line" style="margin: 0 14px 10px">{{ error }}</p>

    <div v-if="result" class="panel-body result-body">
      <p class="muted-line total-line">共 {{ result.pagination.total }} 条 · 第 {{ result.pagination.page }}/{{ totalPages() }} 页</p>

      <article
        v-for="entry in result.items"
        :key="entry.entry_id"
        class="panel-section knowledge-item"
      >
        <div class="item-head">
          <span class="status-badge status-info">{{ entry.entry_type }}</span>
          <strong class="item-title" :title="entry.title">{{ entry.title }}</strong>
        </div>
        <small class="meta-line">{{ entry.entry_code }} · 版本 v{{ entry.source_version }}<template v-if="entry.published_at"> · 发布于 {{ String(entry.published_at).slice(0, 10) }}</template></small>
        <p class="content-snippet" :class="{ expanded: expandedId === entry.entry_id }">{{ entry.content }}</p>
        <button type="button" class="app-button ghost-small" @click="expandedId = expandedId === entry.entry_id ? null : entry.entry_id">
          {{ expandedId === entry.entry_id ? '收起' : '展开全文' }}
        </button>
      </article>

      <div v-if="totalPages() > 1" class="pager">
        <button type="button" class="app-button" :disabled="page <= 1 || loading" @click="search(page - 1)">上一页</button>
        <button type="button" class="app-button" :disabled="page >= totalPages() || loading" @click="search(page + 1)">下一页</button>
      </div>
    </div>

    <div v-else-if="!error" class="empty-state">
      <span class="empty-icon">📚</span>
      <p>输入药品名或专业问题检索说明书、指南、禁忌与机构规则。</p>
    </div>
  </section>
</template>

<style scoped>
.search-area {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.filter-row {
  display: flex;
  gap: 8px;
}
.filter-row .med-id {
  width: 90px;
  flex-shrink: 0;
}
.panel-card {
  height: 100%;
}
.result-body {
  padding-top: 0;
}
.total-line {
  font-size: 12px;
}
.knowledge-item .item-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.item-title {
  font-size: 13px;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.meta-line {
  display: block;
  margin-top: 4px;
  color: var(--color-text-muted);
  font-size: 11px;
}
.content-snippet {
  margin: 8px 0;
  font-size: 12px;
  line-height: 1.65;
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: pre-wrap;
  word-break: break-word;
}
.content-snippet.expanded {
  display: block;
  -webkit-line-clamp: unset;
}
.ghost-small {
  min-height: 28px;
  padding: 3px 10px;
  font-size: 12px;
  color: var(--color-accent);
  border-color: rgba(45, 212, 191, 0.2);
}
.pager {
  display: flex;
  justify-content: center;
  gap: 10px;
  padding-top: 4px;
}
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 30px 20px;
  text-align: center;
}
.empty-icon {
  font-size: 34px;
  opacity: 0.5;
}
.empty-state p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.7;
}
</style>
