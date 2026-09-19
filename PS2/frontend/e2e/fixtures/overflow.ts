// Overflow measurement. A bare `scrollWidth > clientWidth` assertion tells you a page reflows
// but not what did it, so this also names the offending element, its box, its computed inline
// size and the nearest ancestor that establishes its width. That is the evidence the design
// plan asks for before anything is patched.
import type { Page } from '@playwright/test'

export type OverflowOffender = {
  selector: string
  text: string
  right: number
  left: number
  width: number
  computedWidth: string
  computedMinWidth: string
  ancestor: string
  ancestorDisplay: string
}

export type OverflowReport = {
  scrollWidth: number
  clientWidth: number
  overflowBy: number
  offenders: OverflowOffender[]
  offscreenControls: { selector: string; text: string; left: number; right: number }[]
}

export async function measureOverflow(page: Page): Promise<OverflowReport> {
  return page.evaluate(() => {
    const doc = document.documentElement
    const clientWidth = doc.clientWidth

    function describe(element: Element): string {
      const tag = element.tagName.toLowerCase()
      const id = element.id ? `#${element.id}` : ''
      const cls = typeof element.className === 'string' && element.className.trim()
        ? `.${element.className.trim().split(/\s+/).join('.')}`
        : ''
      return `${tag}${id}${cls}`
    }

    // An element that sticks out inside a clipping ancestor cannot scroll the document, so it is
    // not what we are hunting. Walk up and see whether anything actually clips it.
    function isClipped(element: Element): boolean {
      let node = element.parentElement
      while (node && node !== doc) {
        const style = getComputedStyle(node)
        if (style.overflowX !== 'visible') return true
        node = node.parentElement
      }
      return false
    }

    function layoutAncestor(element: Element): Element | null {
      let node = element.parentElement
      while (node && node !== doc) {
        const style = getComputedStyle(node)
        if (/grid|flex/.test(style.display) || style.position === 'absolute' || style.position === 'fixed') return node
        node = node.parentElement
      }
      return element.parentElement
    }

    const offenders: OverflowOffender[] = []
    for (const element of Array.from(document.body.querySelectorAll('*'))) {
      const style = getComputedStyle(element)
      if (style.display === 'none' || style.visibility === 'hidden' || style.position === 'fixed') continue
      const rect = element.getBoundingClientRect()
      if (rect.width === 0 && rect.height === 0) continue
      const overshootsRight = rect.right > clientWidth + 1
      const overshootsLeft = rect.left < -1
      if (!overshootsRight && !overshootsLeft) continue
      if (isClipped(element)) continue
      const ancestor = layoutAncestor(element)
      offenders.push({
        selector: describe(element),
        text: (element.textContent ?? '').trim().slice(0, 80),
        right: Math.round(rect.right * 100) / 100,
        left: Math.round(rect.left * 100) / 100,
        width: Math.round(rect.width * 100) / 100,
        computedWidth: style.width,
        computedMinWidth: style.minWidth,
        ancestor: ancestor ? describe(ancestor) : '(none)',
        ancestorDisplay: ancestor ? getComputedStyle(ancestor).display : '(none)',
      })
    }

    // Deepest-first is noisiest; report the outermost offenders, which are the ones to fix.
    offenders.sort((a, b) => b.width - a.width)

    const controls = Array.from(document.querySelectorAll('a, button, input, select, summary, [role="button"]'))
    const offscreenControls: OverflowReport['offscreenControls'] = []
    for (const control of controls) {
      const style = getComputedStyle(control)
      if (style.display === 'none' || style.visibility === 'hidden') continue
      const rect = control.getBoundingClientRect()
      if (rect.width === 0 && rect.height === 0) continue
      if (rect.right <= clientWidth + 1 && rect.left >= -1) continue
      offscreenControls.push({
        selector: describe(control),
        text: (control.textContent ?? control.getAttribute('aria-label') ?? '').trim().slice(0, 60),
        left: Math.round(rect.left * 100) / 100,
        right: Math.round(rect.right * 100) / 100,
      })
    }

    return {
      scrollWidth: doc.scrollWidth,
      clientWidth,
      overflowBy: doc.scrollWidth - clientWidth,
      offenders: offenders.slice(0, 12),
      offscreenControls,
    }
  })
}

export function formatReport(label: string, report: OverflowReport): string {
  const lines = [
    `${label}: scrollWidth ${report.scrollWidth} vs clientWidth ${report.clientWidth} (over by ${report.overflowBy}px)`,
  ]
  for (const offender of report.offenders) {
    lines.push(
      `  ${offender.selector} box ${offender.left}→${offender.right} (${offender.width}px wide), ` +
        `computed width ${offender.computedWidth}, min-width ${offender.computedMinWidth}, ` +
        `inside ${offender.ancestor} [display: ${offender.ancestorDisplay}]` +
        (offender.text ? ` — "${offender.text}"` : ''),
    )
  }
  for (const control of report.offscreenControls) {
    lines.push(`  control out of view: ${control.selector} "${control.text}" at ${control.left}→${control.right}`)
  }
  return lines.join('\n')
}
