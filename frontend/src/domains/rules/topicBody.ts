/**
 * Topic body for the rules viewer: the dump's topic files open with their own `# Title` and a
 * source blockquote (`> Źródło: … — © Fantasy Flight Games …`). The viewer already shows the
 * title above the content and the credit under the index, so both are dropped from the body.
 * The files themselves stay unchanged (they are also read as docs).
 */
export function topicBody(markdown: string): string {
  const lines = markdown.split(/\r?\n/);
  let i = 0;
  const skipBlank = () => {
    while (i < lines.length && lines[i].trim() === "") i++;
  };
  skipBlank();
  if (i < lines.length && /^#\s/.test(lines[i])) i++;
  skipBlank();
  if (i < lines.length && /^>\s*(Źródło|Source)\b/i.test(lines[i])) {
    while (i < lines.length && lines[i].startsWith(">")) i++;
  }
  skipBlank();
  return lines.slice(i).join("\n");
}
