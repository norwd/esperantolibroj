#!/usr/bin/env python3
"""
fix_ebooks.py - Fix common PDF-conversion artifacts in Esperanto ebook Markdown files.

Fixes applied:
1. Remove repeated page headers (short lines appearing 4+ times in body text)
2. Remove page numbers from end of text lines (e.g. "...boao, 4")
3. Remove page numbers embedded in hyphenated words (e.g. "komen-8\n\nci" -> "komenci")
4. Fix incorrect Esperanto capitalization (e.g. "cAPITRO" -> "CAPITRO" with hat chars)
5. Join hyphenated words split across lines (PDF line-wrap artifact)
6. Remove @omnibus.se / @tyreso.nu and similar publisher boilerplate lines
7. Remove "### 1" style section markers from PDF conversion
8. Remove standalone bullet dot lines (publisher boilerplate)
9. Makes a .bak backup before modifying each file

Usage:
  python3 fix_ebooks.py                           # process all .md files
  python3 fix_ebooks.py "filename.md"             # process specific file(s)
"""

import re
import os
import sys
import shutil
from collections import Counter

# Lowercase Esperanto hat letters mapped to their uppercase equivalents
HAT_LOWER_TO_UPPER = {
    'ĉ': 'Ĉ',
    'ĝ': 'Ĝ',
    'ĥ': 'Ĥ',
    'ĵ': 'Ĵ',
    'ŝ': 'Ŝ',
    'ŭ': 'Ŭ',
}

# The set of hat lowercase characters as a string, for use in regex character classes
HAT_LOWER_CHARS = ''.join(HAT_LOWER_TO_UPPER.keys())


def fix_hat_capitalization(text):
    """
    Fix incorrect Esperanto hat capitalization where the PDF converter used
    a lowercase hat letter before uppercase ASCII letters.
    E.g. "cAPITRO" -> "CAPITRO" (with proper hat chars), "cU LI?" -> "CU LI?"
    Pattern: a lowercase hat letter immediately followed by an uppercase ASCII letter.
    """
    def replace_hat(m):
        hat_lower = m.group(1)
        rest = m.group(2)
        return HAT_LOWER_TO_UPPER.get(hat_lower, hat_lower) + rest

    # Match a lowercase hat letter followed by one or more uppercase ASCII letters
    pattern = '(' + '|'.join(re.escape(c) for c in HAT_LOWER_TO_UPPER.keys()) + ')([A-Z])'
    return re.sub(pattern, replace_hat, text)


def find_repeated_headers(lines, min_occurrences=4, max_header_length=80):
    """
    Find lines that appear many times throughout the document - these are
    page headers repeated from the printed book.

    Returns a set of stripped line strings that should be removed from the body.

    Strategy: count all short line occurrences across the ENTIRE document.
    Lines appearing >= min_occurrences times that look like titles/headers
    (low proportion of lowercase ASCII) are considered page headers.
    """
    candidate_counts = Counter()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) > max_header_length:
            continue
        # Must look like a header: low proportion of lowercase ASCII letters
        lowercase_ascii = sum(1 for c in stripped if c.islower() and c.isascii())
        total_alpha = sum(1 for c in stripped if c.isalpha())
        if total_alpha == 0:
            continue
        lowercase_ratio = lowercase_ascii / total_alpha
        # Consider it a header candidate if less than 15% lowercase ASCII letters
        if lowercase_ratio < 0.15:
            candidate_counts[stripped] += 1

    headers = set()
    for line_text, count in candidate_counts.items():
        if count >= min_occurrences:
            headers.add(line_text)

    return headers


def remove_page_numbers_from_line(line):
    """
    Remove page numbers from the end of text lines.
    Matches patterns like:
      - "...word, 4"       (word/punct followed by space and number)
      - "...word 14"       (word followed by space and number)
    But NOT:
      - Lines that are ONLY a number (standalone numbers = chapter numbers etc.)
      - Lines ending with hyphen-number (handled by join_hyphenated)
      - 4-digit numbers (years like 1984, 2003 - not page numbers)
      - Numbers larger than 999 (books rarely exceed 999 pages)
    """
    stripped = line.rstrip()
    # Don't modify lines that are only a number or only whitespace
    if re.match(r'^\s*\d+\s*$', stripped):
        return line  # leave standalone number lines alone

    # Remove a trailing page number: space + 1-3 digits at end of line
    # The number must be preceded by a non-digit, non-hyphen character
    # We limit to 1-3 digits to avoid removing years (4 digits) or other numbers
    new = re.sub(r'(?<=[^\d\-\s])\s+(\d{1,3})\s*$', '', stripped)
    if new != stripped:
        # Restore trailing newline if original had one
        if line.endswith('\n'):
            return new + '\n'
        return new
    return line


def join_hyphenated(text, headers):
    """
    Join hyphenated words split across lines (PDF line-wrap artifact).

    Handles two patterns:
    A) Line ends with "word-DIGITS" (hyphen with embedded page number):
       "komen-8\n\nLA ETA PRINCO\n\nci la malmuntadon"
       -> "komenci la malmuntadon"

    B) Line ends with "word-" (plain hyphen at end of line):
       "deseg-\n\nnon. Mian desegnon"
       -> "desegnon. Mian desegnon"

    The continuation fragment is identified by starting with a lowercase letter
    (regular or Esperanto hat lowercase).
    """
    lines_list = text.split('\n')
    result = []
    i = 0
    while i < len(lines_list):
        line = lines_list[i]
        stripped = line.rstrip()

        # Pattern A: line ends with "word-DIGITS" (embedded page number)
        m_pagenum = re.match(
            r'^(.*[a-zA-Z' + HAT_LOWER_CHARS + r'])-(\d+)\s*$', stripped
        )
        # Pattern B: line ends with "word-" (plain hyphen at end of line)
        m_plain = re.match(
            r'^(.*[a-zA-Z' + HAT_LOWER_CHARS + r'])-\s*$', stripped
        )

        if m_pagenum or m_plain:
            prefix = m_pagenum.group(1) if m_pagenum else m_plain.group(1)

            # Look ahead: skip blank lines and repeated headers to find continuation
            j = i + 1
            while j < len(lines_list):
                next_stripped = lines_list[j].strip()
                if next_stripped == '':
                    j += 1
                elif next_stripped in headers:
                    j += 1
                else:
                    break

            # The continuation must start with a lowercase letter
            # (it's the second half of a split word)
            if j < len(lines_list):
                cont_line = lines_list[j]
                cont_stripped = cont_line.strip()
                if cont_stripped and (
                    cont_stripped[0].islower() or
                    cont_stripped[0] in HAT_LOWER_CHARS
                ):
                    # Join: prefix + continuation (removing the hyphen)
                    joined = prefix + cont_stripped
                    result.append(joined)
                    # Skip all intermediate lines we consumed
                    i = j + 1
                    continue

        result.append(line)
        i += 1

    return '\n'.join(result)


def remove_repeated_headers(text, headers):
    """
    Remove repeated page headers from the body of the text.
    Keep only the FIRST occurrence of each header (which is in the front matter).
    All subsequent occurrences throughout the body are removed.
    """
    if not headers:
        return text

    lines_list = text.split('\n')
    new_lines = []
    header_seen = Counter()

    for line in lines_list:
        stripped = line.strip()
        if stripped in headers:
            header_seen[stripped] += 1
            if header_seen[stripped] <= 1:
                # Keep first occurrence (front matter / title area)
                new_lines.append(line)
            # else: skip this repeated header line
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)


def process_file(filepath):
    """
    Process a single Markdown file, applying all fixes.
    Returns (original_text, fixed_text).
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        original_text = f.read()

    text = original_text

    # ----------------------------------------------------------------
    # Step 1: Fix hat capitalization FIRST (so header detection finds
    # the correct uppercase forms, e.g. "CU LI?" not "cU LI?")
    # ----------------------------------------------------------------
    text = fix_hat_capitalization(text)

    # ----------------------------------------------------------------
    # Step 2: Remove publisher boilerplate lines
    # ----------------------------------------------------------------
    # @omnibus.se, @tyreso.nu, etc.
    text = re.sub(r'^@\S+\s*$', '', text, flags=re.MULTILINE)

    # "### 1" style conversion artifacts
    text = re.sub(r'^###\s+\d+\s*$', '', text, flags=re.MULTILINE)

    # Standalone middle dot / bullet lines (publisher boilerplate)
    text = re.sub(r'^[·•]\s*$', '', text, flags=re.MULTILINE)

    # Standalone "X" lines surrounded by blank lines (front matter boilerplate)
    # Use a pattern that matches \nX\n between blank lines
    text = re.sub(r'\n\nX\n\n', '\n\n', text)

    # ----------------------------------------------------------------
    # Step 3: Find repeated page headers (on the hat-fixed text)
    # ----------------------------------------------------------------
    fixed_lines = text.split('\n')
    headers_to_remove = find_repeated_headers(fixed_lines)

    if headers_to_remove:
        print(f"  Found {len(headers_to_remove)} repeated header(s) to remove:")
        for h in sorted(headers_to_remove):
            print(f"    '{h}'")

    # ----------------------------------------------------------------
    # Step 4: Join hyphenated words split across lines/pages
    # (must happen BEFORE removing headers, because headers are used
    # as "skip" markers when looking for word continuations)
    # ----------------------------------------------------------------
    text = join_hyphenated(text, headers_to_remove)

    # ----------------------------------------------------------------
    # Step 5: Remove repeated page headers from body
    # ----------------------------------------------------------------
    text = remove_repeated_headers(text, headers_to_remove)

    # ----------------------------------------------------------------
    # Step 6: Remove page numbers from end of text lines
    # ----------------------------------------------------------------
    lines_list = text.split('\n')
    new_lines = [remove_page_numbers_from_line(line) for line in lines_list]
    text = '\n'.join(new_lines)

    # ----------------------------------------------------------------
    # Step 7: Clean up excessive blank lines
    # Replace 3+ consecutive blank lines with 2 blank lines
    # ----------------------------------------------------------------
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    # Remove leading blank lines at start of file
    text = text.lstrip('\n')

    return original_text, text


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Determine which files to process
    if len(sys.argv) > 1:
        targets = []
        for arg in sys.argv[1:]:
            if os.path.isabs(arg):
                targets.append(arg)
            else:
                targets.append(os.path.join(script_dir, arg))
    else:
        # Process all .md files except README.md
        targets = []
        for fname in sorted(os.listdir(script_dir)):
            if fname.endswith('.md') and fname != 'README.md':
                targets.append(os.path.join(script_dir, fname))

    if not targets:
        print("No files to process.")
        return

    print(f"Processing {len(targets)} file(s)...\n")

    for filepath in targets:
        if not os.path.isfile(filepath):
            print(f"SKIP: {filepath} (not found)")
            continue

        fname = os.path.basename(filepath)
        print(f"Processing: {fname}")

        # Make backup (only if it doesn't exist yet)
        backup_path = filepath + '.bak'
        if not os.path.exists(backup_path):
            shutil.copy2(filepath, backup_path)
            print(f"  Backup: {backup_path}")
        else:
            print(f"  Backup already exists, restoring from it first...")
            shutil.copy2(backup_path, filepath)

        try:
            original_text, fixed_text = process_file(filepath)
        except Exception as e:
            print(f"  ERROR processing {fname}: {e}")
            import traceback
            traceback.print_exc()
            continue

        if original_text == fixed_text:
            print(f"  No changes needed.\n")
        else:
            orig_line_count = original_text.count('\n')
            new_line_count = fixed_text.count('\n')
            diff = new_line_count - orig_line_count
            print(f"  Lines: {orig_line_count} -> {new_line_count} ({diff:+d})")

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_text)
            print(f"  Saved.\n")


if __name__ == '__main__':
    main()
