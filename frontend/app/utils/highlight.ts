/**
 * A deliberately tiny syntax highlighter for the API reference.
 *
 * Pulling in a real highlighter would add a few hundred kilobytes to a page
 * that shows three languages and a couple of dozen snippets. Every pattern
 * below runs as a single alternation pass over already-escaped text, so a match
 * can never land inside a span this function itself inserted.
 *
 * Input is escaped first and unconditionally. The snippets are authored in
 * apiReference.ts rather than supplied by anyone, but escaping is what makes
 * the v-html at the call site safe regardless of where the string came from.
 */

export type CodeLanguage = 'bash' | 'json' | 'http'

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

const span = (token: string, text: string) => `<span class="tok-${token}">${text}</span>`

/** JSON, plus the small amount of JS used in the browser example. */
function highlightJson(source: string): string {
  return source.replace(
    // A string (optionally followed by a colon, which makes it a key), a
    // template literal, a keyword, a number, or a line comment.
    /(&quot;(?:\\.|[^&\\]|&(?!quot;))*?&quot;)(\s*:)?|(`(?:\\.|[^`\\])*`)|\b(true|false|null|const|for|of|if|new)\b|\b(-?\d+(?:\.\d+)?)\b|(\/\/[^\n]*)/g,
    (match, str, colon, template, keyword, num, comment) => {
      if (comment) return span('comment', comment)
      if (template) return span('string', template)
      if (str) return colon ? span('key', str) + colon : span('string', str)
      if (keyword) return span('keyword', keyword)
      if (num) return span('number', num)
      return match
    },
  )
}

function highlightBash(source: string): string {
  return source.replace(
    // Comment, quoted string, long/short flag, or a known command at the start
    // of a line.
    /(#[^\n]*)|(&quot;(?:\\.|[^&\\]|&(?!quot;))*?&quot;|'(?:\\.|[^'\\])*')|(^|\s)(-{1,2}[A-Za-z][\w-]*)|(^|\|\s*)(curl|jq)\b/gm,
    (match, comment, str, flagLead, flag, cmdLead, cmd) => {
      if (comment) return span('comment', comment)
      if (str) return span('string', str)
      if (flag) return flagLead + span('flag', flag)
      if (cmd) return cmdLead + span('keyword', cmd)
      return match
    },
  )
}

/** Raw SSE frames: the field names carry the meaning, the payload is JSON. */
function highlightHttp(source: string): string {
  return highlightJson(source).replace(
    /^(event|data|id|retry)(:)|^(:\s*keep-alive)$/gm,
    (match, field, colon, comment) => {
      if (comment) return span('comment', comment)
      if (field) return span('keyword', field) + colon
      return match
    },
  )
}

export function highlight(source: string, language: CodeLanguage): string {
  const escaped = escapeHtml(source)
  if (language === 'bash') return highlightBash(escaped)
  if (language === 'http') return highlightHttp(escaped)
  return highlightJson(escaped)
}
