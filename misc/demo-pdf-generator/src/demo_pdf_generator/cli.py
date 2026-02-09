"""CLI for PDF generation."""

from pathlib import Path

import click
import yaml

from demo_pdf_generator.generator import generate_pdf as create_pdf
from demo_pdf_generator.models import PdfConfig

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


@click.command()
@click.argument("config_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_OUTPUT_DIR,
    help="Output directory for generated PDF",
)
def generate_pdf(config_file: Path, output_dir: Path):
    """Generate a single PDF from a YAML config file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(config_file) as f:
        config_data = yaml.safe_load(f)

    config = PdfConfig(**config_data)
    output_name = f"{config.report.type}_{config.patient.last_name.lower()}.pdf"
    output_path = output_dir / output_name

    create_pdf(config, output_path)
    click.echo(f"Generated: {output_path}")


@click.command()
@click.option(
    "-o", "--output-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_OUTPUT_DIR,
    help="Output directory for generated PDFs",
)
def generate_all(output_dir: Path):
    """Generate all demo PDFs from config files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    config_files = list(CONFIG_DIR.glob("*.yaml"))
    if not config_files:
        click.echo(f"No config files found in {CONFIG_DIR}")
        return

    for config_file in sorted(config_files):
        click.echo(f"Processing: {config_file.name}")
        with open(config_file) as f:
            config_data = yaml.safe_load(f)

        config = PdfConfig(**config_data)
        output_name = f"{config.report.type}_{config.patient.last_name.lower()}.pdf"
        output_path = output_dir / output_name

        create_pdf(config, output_path)
        click.echo(f"  -> {output_path}")

    click.echo(f"\nGenerated {len(config_files)} PDFs in {output_dir}")


if __name__ == "__main__":
    generate_all()
