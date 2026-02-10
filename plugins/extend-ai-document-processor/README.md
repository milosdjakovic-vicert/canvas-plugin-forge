# Canvas Extend AI Document Processor

Canvas plugin for AI-powered document categorization and template prefilling via Extend AI.

## What It Does

When a document is uploaded to Canvas, this plugin automatically:

- Categorizes the document type (Lab Report, Imaging Report, etc.)
- Matches and links to the correct patient
- Assigns an appropriate reviewer
- Prefills report templates with extracted data (test results, codes, values)

## Configuration

Add these secrets to your plugin configuration:

| Secret | Description |
|--------|-------------|
| `EXTEND_AI_API_KEY` | Your Extend AI API key |
| `EXTEND_AI_PROCESSOR_ID` | Processor ID from Extend Studio (e.g., `processor_1234`) |

### Getting your Processor ID

1. Create a processor in Extend Studio for document extraction
2. Copy the processor ID from the processor details page
3. Add it to your plugin secrets

## Requirements

- Extend AI account
- Report templates configured in Canvas (for prefilling to work)
