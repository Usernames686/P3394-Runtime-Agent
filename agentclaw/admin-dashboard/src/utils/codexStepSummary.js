import { normalizeCommandResult } from './commandResult'

const READ_KEYS = new Set([
  'file',
  'files',
  'filename',
  'file_name',
  'file_path',
  'path',
  'paths',
  'source',
  'sources',
  'document',
  'documents',
  'context_file',
  'context_files',
])

const WRITE_KEYS = new Set([
  'artifact',
  'artifacts',
  'artifact_path',
  'artifact_paths',
  'created_file',
  'created_files',
  'directory',
  'file_path',
  'folder',
  'output_file',
  'output_path',
  'path',
  'saved_path',
  'target',
  'write_path',
])

const VERIFY_COMMAND_PATTERN = /\b(pytest|vitest|jest|npm\s+(?:run\s+)?(?:test|build|lint)|pnpm\s+(?:run\s+)?(?:test|build|lint)|yarn\s+(?:test|build|lint)|ruff|mypy|tsc|eslint|playwright|uv\s+run\s+pytest)\b/i
const VERIFY_OUTPUT_PATTERN = /\b(\d+\s+(?:passed|failed|skipped|errors?)|all\s+tests\s+passed|build\s+(?:succeeded|success|completed)|exit\s+code\s+0)\b/i
const FILE_LIKE_PATTERN = /(?:^|[\\/])[^\\/]+\.[a-z0-9]{1,12}$/i

function parseJsonLike(value) {
  if (!value) return {}
  if (typeof value === 'object') return value
  const text = String(value).trim()
  if (!text) return {}
  if (!text.startsWith('{') && !text.startsWith('[')) return text
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

function compactText(value, max = 150) {
  const text = String(value ?? '').replace(/\s+/g, ' ').trim()
  if (!text) return ''
  return text.length > max ? `${text.slice(0, max - 1)}...` : text
}

function addUnique(list, value, max = 150) {
  const text = compactText(value, max)
  if (text && !list.includes(text)) list.push(text)
}

function looksLikePath(value) {
  const text = String(value || '').trim()
  if (!text || text.length > 240) return false
  return text.includes('/') || text.includes('\\') || FILE_LIKE_PATTERN.test(text)
}

function collectValuesByKeys(value, keys, results = [], depth = 0) {
  if (!value || depth > 4) return results
  if (typeof value === 'string') {
    if (looksLikePath(value)) addUnique(results, value)
    return results
  }
  if (Array.isArray(value)) {
    value.forEach(item => collectValuesByKeys(item, keys, results, depth + 1))
    return results
  }
  if (typeof value !== 'object') return results

  Object.entries(value).forEach(([key, item]) => {
    const normalizedKey = String(key || '').toLowerCase()
    if (keys.has(normalizedKey)) {
      if (typeof item === 'string') addUnique(results, item)
      else collectAnyPathValues(item, results, depth + 1)
      return
    }
    collectValuesByKeys(item, keys, results, depth + 1)
  })
  return results
}

function collectAnyPathValues(value, results = [], depth = 0) {
  if (!value || depth > 4) return results
  if (typeof value === 'string') {
    if (looksLikePath(value)) addUnique(results, value)
    return results
  }
  if (Array.isArray(value)) {
    value.forEach(item => collectAnyPathValues(item, results, depth + 1))
    return results
  }
  if (typeof value !== 'object') return results
  Object.values(value).forEach(item => collectAnyPathValues(item, results, depth + 1))
  return results
}

function collectTools(stepOrTools) {
  if (Array.isArray(stepOrTools)) return stepOrTools
  const tools = []
  ;(stepOrTools?.toolCalls || []).forEach(tool => tools.push(tool))
  ;(stepOrTools?.segments || []).forEach(seg => {
    if (seg?.type === 'tool') tools.push(seg)
    if (seg?.type === 'tool-group') (seg.tools || []).forEach(tool => tools.push(tool))
  })
  return tools
}

function firstNonEmpty(...values) {
  for (const value of values) {
    const text = compactText(value)
    if (text) return text
  }
  return ''
}

function commandSummary(commandResult) {
  if (!commandResult) return ''
  const status = commandResult.exitCode !== null && commandResult.exitCode !== undefined
    ? `exit ${commandResult.exitCode}`
    : commandResult.running
      ? 'running'
      : commandResult.failed
        ? 'failed'
        : 'done'
  return `${commandResult.command} (${status})`
}

function verifySummary(commandResult) {
  if (!commandResult) return ''
  const evidence = firstNonEmpty(commandResult.stdout, commandResult.stderr, commandResult.command)
  if (!evidence) return commandSummary(commandResult)
  return evidence
}

function maybeToolPathSummary(tool, args, readTargets, writeTargets) {
  const name = String(tool?.name || '').toLowerCase()
  if (name.includes('read') || name.includes('search') || name.includes('list') || name.includes('open')) {
    collectValuesByKeys(args, READ_KEYS, readTargets)
  }
  if (name.includes('write') || name.includes('edit') || name.includes('create') || name.includes('save') || name.includes('patch')) {
    collectValuesByKeys(args, WRITE_KEYS, writeTargets)
  }
}

function buildItem(kind, values) {
  if (!values.length) return null
  return {
    kind,
    detail: values.slice(0, 3).join(' · '),
    extraCount: Math.max(0, values.length - 3),
  }
}

export function buildCodexStepItems(stepOrTools) {
  const step = Array.isArray(stepOrTools) ? { toolCalls: stepOrTools } : (stepOrTools || {})
  const readTargets = []
  const runTargets = []
  const writeTargets = []
  const verifyTargets = []

  collectValuesByKeys(step.inputs, READ_KEYS, readTargets)
  collectValuesByKeys(step.outputs, WRITE_KEYS, writeTargets)

  const tools = collectTools(stepOrTools)
  tools.forEach(tool => {
    const args = parseJsonLike(tool?.arguments)
    const result = parseJsonLike(tool?.result)
    const commandResult = normalizeCommandResult(tool)

    if (commandResult) {
      addUnique(runTargets, commandSummary(commandResult), 180)
      if (VERIFY_COMMAND_PATTERN.test(commandResult.command) || VERIFY_OUTPUT_PATTERN.test(firstNonEmpty(commandResult.stdout, commandResult.stderr))) {
        addUnique(verifyTargets, verifySummary(commandResult), 180)
      }
      return
    }

    maybeToolPathSummary(tool, args, readTargets, writeTargets)
    collectValuesByKeys(result, WRITE_KEYS, writeTargets)
  })

  const outputEvidence = firstNonEmpty(step.outputs?.result, step.outputs?.summary, step.outputs?.stdout, step.outputs?.message)
  if (VERIFY_OUTPUT_PATTERN.test(outputEvidence)) addUnique(verifyTargets, outputEvidence, 180)
  if (step.error) addUnique(verifyTargets, step.error, 180)

  return [
    buildItem('read', readTargets),
    buildItem('run', runTargets),
    buildItem('write', writeTargets),
    buildItem('verify', verifyTargets),
  ].filter(Boolean)
}
