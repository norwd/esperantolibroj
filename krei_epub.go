// krei_epub.go — Konvertas ĉiujn Markdown-dosierojn al EPUB
// Uzo: go run krei_epub.go [dosieroj...]
package main

import (
	"archive/zip"
	"bytes"
	"fmt"
	htmlpkg "html"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
	"unicode"

	"github.com/yuin/goldmark"
	"github.com/yuin/goldmark/extension"
	"github.com/yuin/goldmark/parser"
	goldhtml "github.com/yuin/goldmark/renderer/html"
)

var md = goldmark.New(
	goldmark.WithExtensions(extension.GFM),
	goldmark.WithParserOptions(parser.WithAutoHeadingID()),
	goldmark.WithRendererOptions(goldhtml.WithUnsafe()),
)

func main() {
	if err := os.MkdirAll("epub", 0755); err != nil {
		fmt.Fprintln(os.Stderr, "Cannot create epub dir:", err)
		os.Exit(1)
	}

	var files []string
	if len(os.Args) > 1 {
		files = os.Args[1:]
	} else {
		entries, err := os.ReadDir(".")
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		for _, e := range entries {
			if !e.IsDir() && strings.HasSuffix(e.Name(), ".md") && e.Name() != "README.md" {
				files = append(files, e.Name())
			}
		}
	}

	start := time.Now()
	ok, fail := 0, 0
	for _, f := range files {
		if err := convertFile(f); err != nil {
			fmt.Fprintf(os.Stderr, "ERARO %s: %v\n", f, err)
			fail++
		} else {
			ok++
		}
	}
	fmt.Printf("Farita: %d ĉefikoj, %d eraroj en %s\n", ok, fail, time.Since(start).Round(time.Millisecond))
}

// titleAuthorFromFilename splits "Title - Author.md" into (title, author).
func titleAuthorFromFilename(name string) (title, author string) {
	base := strings.TrimSuffix(name, ".md")
	if i := strings.LastIndex(base, " - "); i >= 0 {
		return strings.TrimSpace(base[:i]), strings.TrimSpace(base[i+3:])
	}
	return base, ""
}

func convertFile(src string) error {
	data, err := os.ReadFile(src)
	if err != nil {
		return err
	}

	title, author := titleAuthorFromFilename(src)

	// Convert Markdown → HTML
	var buf bytes.Buffer
	if err := md.Convert(data, &buf); err != nil {
		return fmt.Errorf("markdown: %w", err)
	}
	bodyHTML := buf.String()

	// Extract headings for navigation
	navItems := extractHeadings(bodyHTML)

	// Build XHTML content page
	xhtml := buildContentXHTML(title, author, bodyHTML)

	// Build navigation XHTML
	navXHTML := buildNavXHTML(title, navItems)

	// Build OPF
	opf := buildOPF(title, author)

	// Write EPUB ZIP
	outName := strings.TrimSuffix(src, ".md") + ".epub"
	outPath := filepath.Join("epub", outName)
	if err := writeEPUB(outPath, xhtml, navXHTML, opf); err != nil {
		return err
	}
	fmt.Println("Faris:", src)
	return nil
}

// extractHeadings returns (id, text) pairs for h1–h3 elements.
func extractHeadings(body string) [][2]string {
	re := regexp.MustCompile(`(?i)<h[1-3][^>]*id="([^"]*)"[^>]*>(.*?)</h[1-3]>`)
	var items [][2]string
	for _, m := range re.FindAllStringSubmatch(body, -1) {
		text := stripTags(m[2])
		if text != "" {
			items = append(items, [2]string{m[1], text})
		}
	}
	return items
}

func stripTags(s string) string {
	re := regexp.MustCompile(`<[^>]+>`)
	return htmlpkg.UnescapeString(re.ReplaceAllString(s, ""))
}

// slugify makes a safe XML/HTML id from arbitrary text.
func slugify(s string) string {
	var b strings.Builder
	for _, r := range strings.ToLower(s) {
		if unicode.IsLetter(r) || unicode.IsDigit(r) || r == '-' {
			b.WriteRune(r)
		} else if r == ' ' || r == '_' {
			b.WriteByte('-')
		}
	}
	return b.String()
}

const xhtmlHeader = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="eo" lang="eo">
<head>
  <meta charset="UTF-8"/>
  <title>%s</title>
  <style>
    body { font-family: Georgia, serif; line-height: 1.6; margin: 1em 2em; }
    h1, h2, h3 { font-family: sans-serif; }
    p { margin: 0.4em 0; text-indent: 1.2em; }
    p:first-of-type, h1+p, h2+p, h3+p { text-indent: 0; }
    blockquote { margin-left: 2em; font-style: italic; }
  </style>
</head>
<body>
`

func buildContentXHTML(title, author, bodyHTML string) string {
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf(xhtmlHeader, htmlpkg.EscapeString(title)))
	if author != "" {
		sb.WriteString(fmt.Sprintf("<p class=\"author\"><em>%s</em></p>\n", htmlpkg.EscapeString(author)))
	}
	// Make HTML well-formed for XHTML: self-close void elements
	body := fixVoidElements(bodyHTML)
	sb.WriteString(body)
	sb.WriteString("</body>\n</html>\n")
	return sb.String()
}

var voidRe = regexp.MustCompile(`(?i)<(br|hr|img|input|meta|link)([^/]*)>`)

func fixVoidElements(s string) string {
	return voidRe.ReplaceAllString(s, "<$1$2/>")
}

func buildNavXHTML(title string, items [][2]string) string {
	var sb strings.Builder
	sb.WriteString(`<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="eo">
<head><meta charset="UTF-8"/><title>` + htmlpkg.EscapeString(title) + `</title></head>
<body>
<nav epub:type="toc" id="toc">
<h1>Enhavo</h1>
<ol>
`)
	if len(items) == 0 {
		sb.WriteString(fmt.Sprintf("<li><a href=\"content.xhtml\">%s</a></li>\n", htmlpkg.EscapeString(title)))
	} else {
		for _, item := range items {
			sb.WriteString(fmt.Sprintf("<li><a href=\"content.xhtml#%s\">%s</a></li>\n",
				htmlpkg.EscapeString(item[0]), htmlpkg.EscapeString(item[1])))
		}
	}
	sb.WriteString("</ol>\n</nav>\n</body>\n</html>\n")
	return sb.String()
}

func buildOPF(title, author string) string {
	uid := "urn:uuid:" + slugify(title)
	authorElem := ""
	if author != "" {
		authorElem = fmt.Sprintf("\n    <dc:creator>%s</dc:creator>", htmlpkg.EscapeString(author))
	}
	return fmt.Sprintf(`<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">%s</dc:identifier>
    <dc:title>%s</dc:title>%s
    <dc:language>eo</dc:language>
    <meta property="dcterms:modified">%s</meta>
  </metadata>
  <manifest>
    <item id="content" href="content.xhtml" media-type="application/xhtml+xml"/>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
  </manifest>
  <spine>
    <itemref idref="content"/>
  </spine>
</package>
`, uid, htmlpkg.EscapeString(title), authorElem, time.Now().UTC().Format("2006-01-02T15:04:05Z"))
}

func writeEPUB(path, xhtml, navXHTML, opf string) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	w := zip.NewWriter(f)
	defer w.Close()

	// 1. mimetype — MUST be first and uncompressed
	mh := &zip.FileHeader{Name: "mimetype", Method: zip.Store}
	mh.Modified = time.Now()
	mw, err := w.CreateHeader(mh)
	if err != nil {
		return err
	}
	mw.Write([]byte("application/epub+zip"))

	// 2. META-INF/container.xml
	cw, _ := w.Create("META-INF/container.xml")
	cw.Write([]byte(`<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>`))

	// 3. Content
	xw, _ := w.Create("OEBPS/content.xhtml")
	xw.Write([]byte(xhtml))

	// 4. Navigation
	nw, _ := w.Create("OEBPS/nav.xhtml")
	nw.Write([]byte(navXHTML))

	// 5. OPF manifest
	ow, _ := w.Create("OEBPS/content.opf")
	ow.Write([]byte(opf))

	return nil
}
