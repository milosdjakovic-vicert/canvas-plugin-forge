"""Core PDF generation using FPDF2."""

from pathlib import Path

from fpdf import FPDF

from demo_pdf_generator.models import PdfConfig


def generate_pdf(config: PdfConfig, output_path: Path) -> Path:
    """Generate a PDF from config using the appropriate generator."""
    if config.report.type == "lab_report":
        _generate_lab_report(config, output_path)
    elif config.report.type == "imaging_report":
        _generate_imaging_report(config, output_path)
    elif config.report.type == "specialty_report":
        _generate_specialty_report(config, output_path)
    else:
        raise ValueError(f"Unknown report type: {config.report.type}")
    return output_path


class ReportPDF(FPDF):
    """Base PDF class with common styling."""

    def __init__(self, facility: str, title: str, color: tuple):
        super().__init__()
        self.facility = facility
        self.title = title
        self.color = color
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        # Facility name
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*self.color)
        self.cell(0, 8, self.facility, new_x="LMARGIN", new_y="NEXT")
        # Report title
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 6, self.title, new_x="LMARGIN", new_y="NEXT")
        # Line
        self.set_draw_color(*self.color)
        self.set_line_width(0.5)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def add_info_section(self, config: PdfConfig):
        """Add patient/provider info section."""
        self.set_fill_color(245, 245, 245)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(0, 0, 0)

        info = [
            ("Patient Name:", f"{config.patient.first_name} {config.patient.last_name}",
             "Date of Birth:", config.patient.date_of_birth),
            ("MRN:", config.patient.mrn or "N/A",
             "Report Date:", config.report.date),
            ("Provider:", f"{config.reviewer.first_name} {config.reviewer.last_name}",
             "Facility:", config.report.facility),
        ]

        for row in info:
            self.set_font("Helvetica", "B", 9)
            self.cell(28, 6, row[0], fill=True)
            self.set_font("Helvetica", "", 9)
            self.cell(62, 6, row[1], fill=True)
            self.set_font("Helvetica", "B", 9)
            self.cell(28, 6, row[2], fill=True)
            self.set_font("Helvetica", "", 9)
            self.cell(62, 6, row[3], fill=True, new_x="LMARGIN", new_y="NEXT")

        self.ln(5)

    def add_section_title(self, title: str):
        """Add a section title."""
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*self.color)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 7, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)


def _generate_lab_report(config: PdfConfig, output_path: Path):
    """Generate lab report PDF matching exact DB templates.

    Templates matched:
    - CBC: id=5009 "Complete Blood Count (Cbc) With Differential"
    - CMP: id=322000 "Metabolic Panel (14), Comprehensive" (if pages=2)
    """
    pdf = ReportPDF(config.report.facility, "Laboratory Report", (44, 90, 160))
    pdf.add_page()
    pdf.add_info_section(config)

    # CBC Panel - matches template id=5009
    cbc_tests = _get_cbc_tests()
    pdf.add_section_title("Complete Blood Count (Cbc) With Differential")
    _add_lab_table(pdf, cbc_tests)

    if config.pages == 2:
        # CMP Panel - matches template id=322000
        pdf.add_page()
        cmp_tests = _get_cmp_tests()
        pdf.add_section_title("Metabolic Panel (14), Comprehensive")
        _add_lab_table(pdf, cmp_tests)

    # Footer signature
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 5, f"Reviewed by: {config.reviewer.first_name} {config.reviewer.last_name}, MD", new_x="LMARGIN", new_y="NEXT")

    pdf.output(output_path)


def _add_lab_table(pdf: ReportPDF, tests: list[dict]):
    """Add a lab results table to the PDF."""
    # Table header
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(44, 90, 160)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(48, 6, "Test Name", border=1, fill=True)
    pdf.cell(20, 6, "LOINC", border=1, fill=True)
    pdf.cell(22, 6, "Result", border=1, fill=True)
    pdf.cell(30, 6, "Units", border=1, fill=True)
    pdf.cell(35, 6, "Reference Range", border=1, fill=True)
    pdf.cell(15, 6, "Flag", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    # Table rows
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(0, 0, 0)

    for i, test in enumerate(tests):
        fill = i % 2 == 0
        pdf.set_fill_color(249, 249, 249) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(48, 5, test["name"][:25], border=1, fill=fill)  # Truncate long names
        pdf.cell(20, 5, test["loinc"], border=1, fill=fill)
        pdf.cell(22, 5, test["value"], border=1, fill=fill)
        pdf.cell(30, 5, test["unit"][:15], border=1, fill=fill)  # Truncate long units
        pdf.cell(35, 5, test["range"], border=1, fill=fill)
        pdf.cell(15, 5, test["flag"], border=1, fill=fill, new_x="LMARGIN", new_y="NEXT")


def _generate_imaging_report(config: PdfConfig, output_path: Path):
    """Generate imaging report PDF."""
    pdf = ReportPDF(config.report.facility, "Diagnostic Imaging Report", (21, 101, 192))
    pdf.add_page()
    pdf.add_info_section(config)

    content = _get_imaging_content()

    pdf.add_section_title("EXAMINATION")
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, content["study_name"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Modality: {content['modality']}  |  Body Part: {content['body_part']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.add_section_title("CLINICAL INDICATION")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, content["indication"])
    pdf.ln(3)

    pdf.add_section_title("TECHNIQUE")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, content["technique"])
    pdf.ln(3)

    pdf.add_section_title("FINDINGS")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, content["findings"])
    pdf.ln(3)

    # Impression box
    pdf.set_fill_color(227, 242, 253)
    pdf.set_draw_color(21, 101, 192)
    pdf.set_line_width(0.8)
    pdf.rect(10, pdf.get_y(), 190, 25, style="DF")
    pdf.set_xy(12, pdf.get_y() + 2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(21, 101, 192)
    pdf.cell(0, 5, "IMPRESSION", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(12)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(186, 5, content["impression"])

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"CPT Code: {content['cpt_code']} | SNOMED: {content['snomed_comment']}, {content['snomed_interpretation']}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 5, f"{config.reviewer.first_name} {config.reviewer.last_name}, MD - Radiologist", new_x="LMARGIN", new_y="NEXT")

    pdf.output(output_path)


def _generate_specialty_report(config: PdfConfig, output_path: Path):
    """Generate specialty report PDF."""
    pdf = ReportPDF(config.report.facility, "Sleep Study Consultation", (123, 31, 162))
    pdf.add_page()

    # Specialty badge
    pdf.set_fill_color(123, 31, 162)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(30, 5, "Sleep Medicine", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    pdf.add_info_section(config)

    content = _get_specialty_content()

    pdf.add_section_title("REASON FOR REFERRAL")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, content["reason_for_referral"])
    pdf.ln(3)

    pdf.add_section_title("HISTORY AND EXAMINATION")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, content["history"])
    pdf.ln(3)

    # Assessment box
    pdf.set_fill_color(243, 229, 245)
    pdf.set_draw_color(123, 31, 162)
    pdf.set_line_width(0.8)
    y_start = pdf.get_y()
    pdf.rect(10, y_start, 190, 22, style="DF")
    pdf.set_xy(12, y_start + 2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(123, 31, 162)
    pdf.cell(0, 5, "ASSESSMENT", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(12)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(186, 5, content["assessment"])

    pdf.set_y(y_start + 27)

    # Recommendations box
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(123, 31, 162)
    pdf.set_line_width(1)
    y_start = pdf.get_y()
    pdf.rect(10, y_start, 190, 35, style="D")
    pdf.set_xy(12, y_start + 2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(123, 31, 162)
    pdf.cell(0, 5, "RECOMMENDATIONS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(12)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(186, 5, content["recommendations"])

    pdf.ln(20)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"SNOMED Code: {content['snomed_code']}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 5, f"{config.reviewer.first_name} {config.reviewer.last_name}, MD - Sleep Medicine Specialist", new_x="LMARGIN", new_y="NEXT")

    pdf.output(output_path)


def _get_cbc_tests() -> list[dict]:
    """Get CBC test data - exact match to template id=5009 (Complete Blood Count With Differential)."""
    return [
        {"name": "WBC", "loinc": "6690-2", "value": "7.2", "unit": "x10^9/L", "range": "4.5-11.0", "flag": ""},
        {"name": "RBC", "loinc": "789-8", "value": "4.8", "unit": "x10^12/L", "range": "4.5-5.5", "flag": ""},
        {"name": "Hemoglobin", "loinc": "718-7", "value": "14.2", "unit": "g/dL", "range": "13.5-17.5", "flag": ""},
        {"name": "Hematocrit", "loinc": "4544-3", "value": "42.1", "unit": "%", "range": "38.0-50.0", "flag": ""},
        {"name": "MCV", "loinc": "787-2", "value": "88", "unit": "fL", "range": "80-100", "flag": ""},
        {"name": "MCH", "loinc": "785-6", "value": "29.6", "unit": "pg", "range": "27-33", "flag": ""},
        {"name": "MCHC", "loinc": "786-4", "value": "33.7", "unit": "g/dL", "range": "32-36", "flag": ""},
        {"name": "RDW", "loinc": "788-0", "value": "13.2", "unit": "%", "range": "11.5-14.5", "flag": ""},
        {"name": "Platelets", "loinc": "777-3", "value": "245", "unit": "x10^9/L", "range": "150-400", "flag": ""},
        {"name": "Neutrophils", "loinc": "770-8", "value": "55", "unit": "%", "range": "40-70", "flag": ""},
        {"name": "Lymphs", "loinc": "736-9", "value": "35", "unit": "%", "range": "20-40", "flag": ""},
        {"name": "Monocytes", "loinc": "5905-5", "value": "6", "unit": "%", "range": "2-8", "flag": ""},
        {"name": "Eos", "loinc": "713-8", "value": "3", "unit": "%", "range": "1-4", "flag": ""},
        {"name": "Basos", "loinc": "706-2", "value": "1", "unit": "%", "range": "0-2", "flag": ""},
        {"name": "Neutrophils (Absolute)", "loinc": "751-8", "value": "3.96", "unit": "x10^9/L", "range": "1.8-7.7", "flag": ""},
        {"name": "Lymphs (Absolute)", "loinc": "731-0", "value": "2.52", "unit": "x10^9/L", "range": "1.0-4.8", "flag": ""},
        {"name": "Monocytes(Absolute)", "loinc": "742-7", "value": "0.43", "unit": "x10^9/L", "range": "0.0-0.8", "flag": ""},
        {"name": "Eos (Absolute)", "loinc": "711-2", "value": "0.22", "unit": "x10^9/L", "range": "0.0-0.4", "flag": ""},
        {"name": "Baso (Absolute)", "loinc": "704-7", "value": "0.07", "unit": "x10^9/L", "range": "0.0-0.2", "flag": ""},
        {"name": "Immature Granulocytes", "loinc": "38518-7", "value": "0", "unit": "%", "range": "0-2", "flag": ""},
        {"name": "Immature Grans (Abs)", "loinc": "51584-1", "value": "0.00", "unit": "x10^9/L", "range": "0.0-0.1", "flag": ""},
        {"name": "NRBC", "loinc": "58413-6", "value": "0", "unit": "/100 WBC", "range": "0", "flag": ""},
    ]


def _get_cmp_tests() -> list[dict]:
    """Get CMP test data - exact match to template id=322000 (Metabolic Panel 14, Comprehensive)."""
    return [
        {"name": "Glucose", "loinc": "2345-7", "value": "95", "unit": "mg/dL", "range": "70-100", "flag": ""},
        {"name": "BUN", "loinc": "3094-0", "value": "15", "unit": "mg/dL", "range": "7-20", "flag": ""},
        {"name": "Creatinine", "loinc": "2160-0", "value": "1.0", "unit": "mg/dL", "range": "0.7-1.3", "flag": ""},
        {"name": "eGFR If NonAfricn Am", "loinc": "48642-3", "value": ">60", "unit": "mL/min/1.73m2", "range": ">60", "flag": ""},
        {"name": "eGFR If Africn Am", "loinc": "62238-1", "value": ">60", "unit": "mL/min/1.73m2", "range": ">60", "flag": ""},
        {"name": "BUN/Creatinine Ratio", "loinc": "3097-3", "value": "15", "unit": "", "range": "10-20", "flag": ""},
        {"name": "Sodium", "loinc": "2951-2", "value": "140", "unit": "mEq/L", "range": "136-145", "flag": ""},
        {"name": "Potassium", "loinc": "2823-3", "value": "4.2", "unit": "mEq/L", "range": "3.5-5.0", "flag": ""},
        {"name": "Chloride", "loinc": "2075-0", "value": "102", "unit": "mEq/L", "range": "98-106", "flag": ""},
        {"name": "Carbon Dioxide, Total", "loinc": "2028-9", "value": "24", "unit": "mEq/L", "range": "23-29", "flag": ""},
        {"name": "Calcium", "loinc": "17861-6", "value": "9.5", "unit": "mg/dL", "range": "8.5-10.5", "flag": ""},
        {"name": "Protein, Total", "loinc": "2885-2", "value": "7.0", "unit": "g/dL", "range": "6.0-8.3", "flag": ""},
        {"name": "Albumin", "loinc": "1751-7", "value": "4.2", "unit": "g/dL", "range": "3.5-5.0", "flag": ""},
        {"name": "Globulin, Total", "loinc": "10834-0", "value": "2.8", "unit": "g/dL", "range": "2.0-3.5", "flag": ""},
        {"name": "A/G Ratio", "loinc": "1759-0", "value": "1.5", "unit": "", "range": "1.0-2.5", "flag": ""},
        {"name": "Bilirubin, Total", "loinc": "1975-2", "value": "0.8", "unit": "mg/dL", "range": "0.1-1.2", "flag": ""},
        {"name": "Alkaline Phosphatase", "loinc": "6768-6", "value": "65", "unit": "U/L", "range": "44-147", "flag": ""},
        {"name": "AST (SGOT)", "loinc": "1920-8", "value": "25", "unit": "U/L", "range": "10-40", "flag": ""},
        {"name": "ALT (SGPT)", "loinc": "1742-6", "value": "28", "unit": "U/L", "range": "7-56", "flag": ""},
    ]


def _get_imaging_content() -> dict:
    """Get imaging report content - matches template id=620.

    Template: "Radiologic Exam Chest 2 Views Frontal&Lateral"
    CPT Code: 71020
    Fields:
    - Comment (SNOMED 281296001)
    - Interpretation (SNOMED 282290005)
    """
    return {
        "study_name": "Radiologic Exam Chest 2 Views Frontal&Lateral",
        "cpt_code": "71020",  # Template code
        "snomed_comment": "281296001",  # Field code for Comment
        "snomed_interpretation": "282290005",  # Field code for Interpretation
        "modality": "X-Ray",
        "body_part": "Chest",
        "indication": "Annual screening, history of smoking",
        "technique": "PA and lateral views of the chest obtained.",
        "findings": (
            "LUNGS: Clear bilaterally. No focal consolidation, pleural effusion, or pneumothorax.\n\n"
            "HEART: Normal cardiac silhouette. No cardiomegaly.\n\n"
            "MEDIASTINUM: Normal mediastinal contours. No widening.\n\n"
            "BONES: No acute osseous abnormality. Degenerative changes of the thoracic spine.\n\n"
            "SOFT TISSUES: Unremarkable."
        ),
        "impression": (
            "1. No acute cardiopulmonary abnormality.\n"
            "2. Mild degenerative changes of the thoracic spine."
        ),
    }


def _get_specialty_content() -> dict:
    """Get specialty report content."""
    return {
        "study_name": "Sleep Study Consultation",
        "snomed_code": "440290008",
        "specialty": "Sleep Medicine",
        "reason_for_referral": "Excessive daytime sleepiness, reported snoring",
        "history": (
            "Patient reports difficulty staying awake during the day, particularly in the afternoon. "
            "Partner reports loud snoring with witnessed apneic episodes. Patient denies morning headaches. "
            "BMI: 28.5. Mallampati score: III. Neck circumference: 42 cm."
        ),
        "assessment": (
            "Clinical presentation consistent with obstructive sleep apnea syndrome. "
            "Recommend in-laboratory polysomnography for definitive diagnosis."
        ),
        "recommendations": (
            "1. Schedule in-laboratory polysomnography\n"
            "2. Sleep hygiene counseling provided\n"
            "3. Weight loss encouraged\n"
            "4. Follow-up after sleep study completion"
        ),
    }
