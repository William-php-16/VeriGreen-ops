"""Generate synthetic benchmark corpus for VeriGreen-ops in data/sample/.

Creates:
  - data/sample/sample_emissions.csv
  - data/sample/sample_sustainability_report.pdf

Planted audit test cases:
  (a) Valid Scope 1 & 2 governance and transition policy disclosures.
  (b) Intentional numerical discrepancy: PDF claims a 24.0% Scope 1+2 reduction
      (to 7,600 tCO2e in FY 2025), whereas CSV logs sum to 9,200.0 tCO2e
      (an 8.0% reduction from the 10,000.0 tCO2e FY 2024 baseline).
  (c) Missing Scope 3 baseline gap (explicitly unmeasured / no baseline year).
  (d) Unsubstantiated "100% carbon neutral packaging" marketing claim.
"""

from __future__ import annotations

import csv
from pathlib import Path
from fpdf import FPDF


REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO_ROOT / "data" / "sample"


EMISSIONS_ROWS = [
    # FY 2024 Baseline (Scope 1 = 6,000.0 | Scope 2 = 4,000.0 | Total = 10,000.0 tCO2e)
    ["2024", "NL-UTR-01", "Utrecht Processing Plant", "Scope 1", "Natural Gas Boilers", "12800", "MWh", "2600.0", "Market-based"],
    ["2024", "NL-UTR-01", "Utrecht Processing Plant", "Scope 2", "Purchased Grid Electricity", "5200", "MWh", "1400.0", "Market-based"],
    ["2024", "NL-EIN-02", "Eindhoven Packaging Hub", "Scope 1", "Process Heat & LPG", "6900", "MWh", "1400.0", "Market-based"],
    ["2024", "NL-EIN-02", "Eindhoven Packaging Hub", "Scope 2", "Purchased Grid Electricity", "4100", "MWh", "1100.0", "Market-based"],
    ["2024", "BE-ANT-03", "Antwerp Cold Logistics Center", "Scope 1", "Backup Diesel & Refrigerants", "4500", "MWh", "1100.0", "Market-based"],
    ["2024", "BE-ANT-03", "Antwerp Cold Logistics Center", "Scope 2", "Purchased Grid Electricity", "3600", "MWh", "900.0", "Market-based"],
    ["2024", "DE-DOR-04", "Dortmund Distribution Depot", "Scope 1", "Regional Delivery Fleet", "3800", "MWh", "900.0", "Market-based"],
    ["2024", "DE-DOR-04", "Dortmund Distribution Depot", "Scope 2", "Purchased Grid Electricity", "2400", "MWh", "600.0", "Market-based"],
    # FY 2025 Actuals (Scope 1 = 5,700.0 | Scope 2 = 3,500.0 | Total = 9,200.0 tCO2e -> 8.0% reduction)
    ["2025", "NL-UTR-01", "Utrecht Processing Plant", "Scope 1", "Natural Gas Boilers", "12300", "MWh", "2500.0", "Market-based"],
    ["2025", "NL-UTR-01", "Utrecht Processing Plant", "Scope 2", "Purchased Grid Electricity", "5100", "MWh", "1200.0", "Market-based"],
    ["2025", "NL-EIN-02", "Eindhoven Packaging Hub", "Scope 1", "Process Heat & LPG", "6650", "MWh", "1350.0", "Market-based"],
    ["2025", "NL-EIN-02", "Eindhoven Packaging Hub", "Scope 2", "Purchased Grid Electricity", "4000", "MWh", "950.0", "Market-based"],
    ["2025", "BE-ANT-03", "Antwerp Cold Logistics Center", "Scope 1", "Backup Diesel & Refrigerants", "4100", "MWh", "1000.0", "Market-based"],
    ["2025", "BE-ANT-03", "Antwerp Cold Logistics Center", "Scope 2", "Purchased Grid Electricity", "3500", "MWh", "800.0", "Market-based"],
    ["2025", "DE-DOR-04", "Dortmund Distribution Depot", "Scope 1", "Regional Delivery Fleet", "3600", "MWh", "850.0", "Market-based"],
    ["2025", "DE-DOR-04", "Dortmund Distribution Depot", "Scope 2", "Purchased Grid Electricity", "2350", "MWh", "550.0", "Market-based"],
]


class SustainabilityReportPDF(FPDF):
    """Simple, clean A4 PDF renderer with predictable text extraction."""

    def header(self) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(90, 100, 110)
        self.cell(
            0,
            8,
            "VerdaPack Foods B.V. - FY 2025 Draft Sustainability Report (CSRD Readiness Corpus)",
            align="L",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_draw_color(200, 210, 220)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def add_section(self, heading: str, paragraphs: list[str]) -> None:
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(20, 60, 45)
        self.multi_cell(0, 7, heading)
        self.ln(2)
        self.set_font("Helvetica", "", 10.5)
        self.set_text_color(30, 30, 30)
        for para in paragraphs:
            self.multi_cell(0, 5.8, para)
            self.ln(3)
        self.ln(2)


def write_sample_csv(csv_path: Path) -> None:
    headers = [
        "reporting_year",
        "facility_id",
        "facility_name",
        "emission_scope",
        "activity_source",
        "energy_consumption",
        "energy_unit",
        "emissions_tco2e",
        "methodology",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(EMISSIONS_ROWS)


def write_sample_pdf(pdf_path: Path) -> None:
    pdf = SustainabilityReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(20, 18, 20)

    # Page 1: Title + Valid Scope 1 & 2 Policy Disclosures
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 50, 35)
    pdf.multi_cell(0, 9, "VerdaPack Foods B.V.\nFY 2025 Sustainability & CSRD Readiness Draft")
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 90, 95)
    pdf.multi_cell(
        0,
        5.5,
        "Prepared for internal pre-assurance review | Reporting Entity: 1,250 FTE | Turnover: EUR 480M | Boundary: Utrecht, Eindhoven, Antwerp, and Dortmund facilities.",
    )
    pdf.ln(6)

    pdf.add_section(
        "1. Climate Transition Plan & Scope 1 and 2 Policy (ESRS E1-1)",
        [
            (
                "In March 2025, the Board of Directors of VerdaPack Foods B.V. formally approved our Corporate Climate and Energy Transition Policy, establishing executive oversight under the Sustainability and Audit Committee. Our operational decarbonization roadmap aligns with a 1.5C Paris Agreement trajectory across all four European manufacturing and logistics facilities."
            ),
            (
                "Under this policy, VerdaPack Foods maintains ISO 50001 energy management certification at Utrecht Processing Plant and Eindhoven Packaging Hub. Key Scope 1 and Scope 2 levers include heat-recovery retrofits on natural gas boilers, phased electrification of regional delivery vans in Dortmund, and multi-year Power Purchase Agreements backed by Guarantees of Origin targeting 100% renewable grid electricity by 2030."
            ),
            (
                "For internal baseline tracking, FY 2024 serves as our reference year for operational emissions, with consolidated Scope 1 and Scope 2 market-based emissions of 10,000 tCO2e across our four European sites."
            ),
        ],
    )

    # Page 2: Quantitative GHG Disclosures (Intentional Discrepancy) + Scope 3 Baseline Gap
    pdf.add_page()
    pdf.add_section(
        "2. Scope 1 & 2 GHG Emissions Performance (ESRS E1-4, E1-6, VS-B3)",
        [
            (
                "VerdaPack Foods targets a 42% absolute reduction in Scope 1 and Scope 2 greenhouse gas emissions by FY 2030 compared to our FY 2024 baseline of 10,000 tCO2e. Emissions are consolidated under operational control following the GHG Protocol Corporate Standard."
            ),
            (
                "In FY 2025, operational efficiency and partial renewable power procurement delivered a 24.0% reduction in combined Scope 1 and Scope 2 GHG emissions compared to the FY 2024 baseline of 10,000 tCO2e, lowering total operational emissions to 7,600 tCO2e across our four European facilities."
            ),
            (
                "Total operational energy consumption across boilers, process heat, fleet fuel, and grid electricity is logged monthly at facility level in our internal energy ledger (41,600 MWh in FY 2025 versus 43,300 MWh in FY 2024), equating to an operational emissions intensity of 19.17 tCO2e per million EUR turnover based on facility utility data."
            ),
        ],
    )

    pdf.add_section(
        "3. Scope 3 Value Chain Emissions Status (ESRS E1-4, E1-6)",
        [
            (
                "Scope 3 indirect value chain emissions (including purchased agricultural ingredients, packaging substrates, and downstream cold-chain distribution) are currently excluded from our FY 2025 GHG inventory. VerdaPack Foods has not yet established a Scope 3 baseline year, screening methodology, or quantitative Scope 3 reduction target, and plans to initiate supplier data collection in FY 2027."
            ),
        ],
    )

    # Page 3: Packaging Greenwashing Claim + E4, S2, G1 Disclosures
    pdf.add_page()
    pdf.add_section(
        "4. Packaging Circularity & Product Claims (ESRS E5-5)",
        [
            (
                "Total outbound packaging placed on the European market in FY 2025 totaled 14,200 metric tonnes, of which 62% by weight is classified as technically recyclable cardboard and mono-material polymer trays. Recycled post-consumer content averaged 34% across rigid trays."
            ),
            (
                "All VerdaPack retail product lines now feature 100% carbon neutral packaging, delivering zero-impact food protection across our European retail channels."
            ),
        ],
    )

    pdf.add_section(
        "5. Value Chain Workers, Business Conduct & Biodiversity (ESRS S2, G1, E4)",
        [
            (
                "Value Chain Workers (ESRS S2-1): Our Supplier Code of Conduct prohibits forced labor, child labor, and unsafe working conditions, and has been signed by 78% of Tier-1 suppliers by spend. However, independent third-party living-wage audits and a dedicated non-employee worker grievance portal have not yet been implemented."
            ),
            (
                "Business Conduct (ESRS G1-1): VerdaPack Foods enforces a zero-tolerance Anti-Bribery and Anti-Corruption Policy signed annually by all corporate staff, supported by an encrypted third-party SpeakUp whistleblower hotline with zero confirmed corruption incidents in FY 2025."
            ),
            (
                "Biodiversity (ESRS E4-1): VerdaPack Foods recognizes potential land-use dependencies in agricultural sourcing, but has not yet conducted site-level biodiversity proximity assessments or adopted a formal nature transition plan."
            ),
        ],
    )

    pdf.output(str(pdf_path))


def main() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = SAMPLE_DIR / "sample_emissions.csv"
    pdf_path = SAMPLE_DIR / "sample_sustainability_report.pdf"

    write_sample_csv(csv_path)
    write_sample_pdf(pdf_path)

    print(f"Generated CSV: {csv_path}")
    print(f"Generated PDF: {pdf_path}")


if __name__ == "__main__":
    main()
