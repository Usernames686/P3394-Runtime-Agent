const COMMAND_TOOL_NAMES = new Set([
  'shell',
  'powershell',
  'execute_command',
  'execute_sudo_command',
  'terminal',
  'command',
])

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

function firstString(source, keys) {
  if (!source || typeof source !== 'object') return ''
  for (const key of keys) {
    const value = source[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return ''
}

function normalizeText(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value.trimEnd()
  return JSON.stringify(value, null, 2)
}

function parseExitCode(value) {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function splitMarkedShellOutput(text) {
  const output = String(text || '').trimEnd()
  const markerPattern = /\[(stdout|stderr)\]\r?\n/gi
  const markers = [...output.matchAll(markerPattern)]
  const exitMatch = output.match(/exit code\s+(-?\d+)/i)
  const exitCode = exitMatch ? Number.parseInt(exitMatch[1], 10) : null

  if (!markers.length) {
    if (/^\[ERROR\]/i.test(output)) {
      return {
        stdout: '',
        stderr: output.replace(/^\[ERROR\]\s*/i, '').trim(),
        exitCode,
      }
    }
    return {
      stdout: output === '(no output)' ? '' : output,
      stderr: '',
      exitCode,
    }
  }

  const parts = { stdout: '', stderr: '' }
  markers.forEach((marker, index) => {
    const key = marker[1].toLowerCase()
    const start = marker.index + marker[0].length
    const end = index + 1 < markers.length ? markers[index + 1].index : output.length
    const section = output.slice(start, end).trimEnd()
    parts[key] = parts[key] ? `${parts[key]}\n${section}` : section
  })

  const prefix = output.slice(0, markers[0].index).trim()
  if (prefix && /^\[ERROR\]/i.test(prefix) && !parts.stderr) {
    parts.stderr = prefix.replace(/^\[ERROR\]\s*/i, '')
  }

  return { ...parts, exitCode }
}

export function isCommandTool(tool) {
  if (!tool) return false
  const toolName = String(tool.name || 'command')
  const lowerToolName = toolName.toLowerCase()
  const args = parseJsonLike(tool.arguments)
  const command = firstString(args, ['command', 'cmd', 'script'])

  return COMMAND_TOOL_NAMES.has(lowerToolName)
    || lowerToolName.includes('shell')
    || lowerToolName.includes('powershell')
    || lowerToolName.includes('terminal')
    || lowerToolName.includes('command')
    || !!command
}

export function normalizeCommandResult(tool) {
  if (!tool || !isCommandTool(tool)) return null

  const toolName = String(tool.name || 'command')
  const args = parseJsonLike(tool.arguments)
  const result = parseJsonLike(tool.result)
  const command = firstString(args, ['command', 'cmd', 'script'])
  const cwd = firstString(args, ['cwd', 'working_dir', 'workdir', 'workingDirectory'])

  let stdout = ''
  let stderr = ''
  let exitCode = null
  let success = null

  if (result && typeof result === 'object' && !Array.isArray(result)) {
    stdout = normalizeText(result.stdout ?? result.output ?? result.result ?? '')
    stderr = normalizeText(result.stderr ?? result.error ?? '')
    exitCode = parseExitCode(result.exit_code ?? result.exitCode ?? result.returncode ?? result.return_code ?? result.code)
    if (typeof result.success === 'boolean') success = result.success
  } else {
    const split = splitMarkedShellOutput(result || tool.result || '')
    stdout = split.stdout
    stderr = split.stderr
    exitCode = split.exitCode
  }

  const status = String(tool.status || '').toLowerCase()
  const running = ['running', 'pending', 'started'].includes(status)
  const failed = success === false
    || (exitCode !== null && exitCode !== 0)
    || ['failed', 'error', 'cancelled', 'canceled', 'timeout'].includes(status)
    || (/^\[ERROR\]/i.test(String(tool.result || '')) && !stdout)

  return {
    command: command || toolName,
    cwd,
    exitCode,
    failed,
    running,
    stdout,
    stderr,
    toolName,
  }
}

export function commandStatusText(command) {
  if (!command) return ''
  if (command.exitCode !== null && command.exitCode !== undefined) return `Exit ${command.exitCode}`
  if (command.running) return 'Running'
  return command.failed ? 'Failed' : 'Done'
}

export function formatCommandDuration(tool) {
  if (tool?.duration_ms !== undefined && tool?.duration_ms !== null) {
    return `${Number(tool.duration_ms).toFixed(0)}ms`
  }
  return tool?.elapsed || ''
}
