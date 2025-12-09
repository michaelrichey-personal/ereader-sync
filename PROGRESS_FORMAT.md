# Progress Output Format Specification

This document defines the standardized format for progress reporting across all scripts in the e-reader system. This format enables real-time progress updates in both GUI and TUI.

## Format

All scripts that process multiple items should output progress information to stdout in the following format:

```
PROGRESS|<successful>|<failures>|<processed>|<total>|<current_item>
```

### Fields

1. **PROGRESS**: Fixed prefix for easy parsing
2. **successful**: Number of items successfully processed (integer)
3. **failures**: Number of items that failed (integer)
4. **processed**: Total number of items processed so far (successful + failures) (integer)
5. **total**: Total number of items to process (integer)
6. **current_item**: Description of the current item being processed (string)

### Examples

```
PROGRESS|0|0|0|20|Starting to scrape Hacker News stories
PROGRESS|1|0|1|20|Scraped: How to Build a Compiler
PROGRESS|2|0|2|20|Scraped: Understanding Async/Await
PROGRESS|2|1|3|20|Failed: Network timeout for article
PROGRESS|20|0|20|20|Complete
```

### Parsing

GUI/TUI implementations should:
1. Read stdout line-by-line in real-time (streaming, not buffered)
2. Check if each line starts with `PROGRESS|`
3. Split on `|` delimiter to extract fields
4. Update progress bars: `progress = processed / total`
5. Update status labels with `current_item` text
6. Display success/failure counts

### Implementation Guidelines

**For Scripts:**
- Flush stdout after each progress line: `print(..., flush=True)`
- Output progress before processing each item
- Output final progress when complete
- Use descriptive `current_item` text

**For GUI/TUI:**
- Use non-blocking subprocess execution with stdout streaming
- Read stdout line-by-line in real-time
- Parse PROGRESS lines and update UI
- Display other output lines in detail/log view

## Script-Specific Formats

### Scrapers (HCR, HN)
- **Total**: Number of posts/stories to scrape
- **Current item**: "Scraping: <title>" or "Checking: <title>"
- **Final**: "Complete" or "Scraping complete"

### Converter (EPUB to XTC)
- **Total**: Number of EPUB files to convert
- **Current item**: "Converting: <filename>" with substeps
- **Substeps**: "Loading converter", "Uploading EPUB", "Applying settings", "Starting conversion", "Waiting for download"
- **Final**: "Conversion complete"

### Upload
- **Total**: Number of files to upload
- **Current item**: "Uploading: <filename>"
- **Final**: "Upload complete"

## Backward Compatibility

Scripts should output both:
1. **Machine-readable**: PROGRESS lines for GUI/TUI parsing
2. **Human-readable**: Regular print statements for direct terminal use

This ensures scripts work well when run directly from command line while also providing structured data for UI parsing.
