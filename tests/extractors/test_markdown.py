from knowledge_ingestor.extractors.markdown import (
    extract_headings,
    extract_images,
    extract_links,
    html_to_markdown,
)


def test_html_to_markdown_converts_basic_structure():
    html = "<h1>Title</h1><p>Hello <b>world</b></p>"

    markdown = html_to_markdown(html)

    assert markdown.startswith("# Title")
    assert "**world**" in markdown


def test_extract_headings():
    markdown = "# Title\n\nsome text\n\n## Subheading\n"

    assert extract_headings(markdown) == ["Title", "Subheading"]


def test_extract_images_and_links():
    markdown = (
        "See [docs](https://example.com/docs) and ![alt](https://example.com/img.png)."
    )

    assert extract_links(markdown) == ["https://example.com/docs"]
    assert extract_images(markdown) == ["https://example.com/img.png"]
