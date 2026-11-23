import csv
from pathlib import Path
from fpdf import FPDF

SAMPLE_DIR = Path("data/sample")


def create_sample_csv(csv_path: Path) -> None:
    rows = [
        ["reporting_year", "facility", "scope", "category", "activity_mwh", "emissions_tco2e", "verification_status"],
        [2024, "Rotterdam Logistics Hub", "Scope 1", "Stationary & Fleet Fuel", 4200, 1040.0, "Limited Assurance"],
        [2024, "Utrecht Packaging Plant", "Scope 1", "Natural Gas Heating", 2100, 390.0, "Limited Assurance"],
        [2024, "Rotterdam Logistics Hub", "Scope 2", "Purchased Electricity (Market)", 5100, 610.0, "Limited Assurance"],
        [2024, "Utrecht Packaging Plant", "Scope 2", "Purchased Electricity (Market)", 3400, 410.0, "Limited Assurance"],
        [2025, "Rotterdam Logistics Hub", "Scope 1", "Stationary & Fleet Fuel", 3900, 960.0, "Internal Unaudited"],
        [2025, "Utrecht Packaging Plant", "Scope 1", "Natural Gas Heating", 1950, 360.0, "Internal Unaudited"],
        [2025, "Rotterdam Logistics Hub", "Scope 2", "Purchased Electricity (Market)", 5250, 420.0, "Internal Unaudited"],
        [2025, "Utrecht Packaging Plant", "Scope 2", "Purchased Electricity (Market)", 3300, 290.0, "Internal Unaudited"],
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def create_sample_pdf(pdf_path: Path) -> None:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)

    pages = [
        {
            "title": "1. Governance, Strategy & Brand Commitments",
            "body": (
                "GreenLeaf Foods B.V. (820 employees, Netherlands) oversees sustainability impacts "
                "through its Supervisory Board Audit & Risk Committee, which reviews double materiality "
                "priorities semi-annually.\n\n"
                "Our flagship retail line now features 100% carbon neutral packaging across all Dutch "
                "supermarkets, making our products completely eco-friendly for conscious consumers.\n\n"
                "Consolidation boundary: Operational control across our Rotterdam Logistics Hub and "
                "Utrecht Packaging Plant."
            ),
        },
        {
            "title": "2. Climate Transition Plan & GHG Performance (ESRS E1)",
            "body": (
                "GreenLeaf Foods targets a 42% absolute reduction in Scope 1 and Scope 2 greenhouse gas "
                "emissions by 2030 against a 2024 baseline, aligned with a 1.5 degrees Celsius pathway.\n\n"
                "In 2025, operational efficiency upgrades delivered a 22% reduction in Scope 1 emissions "
                "compared to 2024. Total gross Scope 1 emissions stood at 1,320 tCO2e and market-based "
                "Scope 2 emissions totaled 710 tCO2e. Location-based Scope 2 figures and material Scope 3 "
                "Category 1 agricultural supply chain emissions are currently under supplier data collection "
                "and are excluded from this disclosure."
            ),
        },
        {
            "title": "3. Value Chain Workers & Business Conduct (ESRS S2 & G1)",
            "body": (
                "All Tier-1 agricultural and packaging suppliers must sign our Supplier Code of Conduct "
                "prohibiting forced labor and enforcing living-wage audits. Workers can submit anonymous "
                "complaints via an independent third-party hotline available in Dutch, English, and Polish.\n\n"
                "During the 2025 reporting period, zero confirmed incidents of corruption or bribery were "
                "recorded across company operations, and 98% of staff completed annual anti-bribery training."
            ),
        },
    ]

    for idx, page in enumerate(pages, start=1):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"GreenLeaf Foods B.V. - 2025 Sustainability Report (Page {idx})", ln=True)
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, page["title"], ln=True)
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, page["body"])

    pdf.output(str(pdf_path))


def main() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = SAMPLE_DIR / "sample_emissions.csv"
    pdf_path = SAMPLE_DIR / "sample_sustainability_report.pdf"

    create_sample_csv(csv_path)
    create_sample_pdf(pdf_path)
    print(f"Created synthetic test fixtures:\n  - {csv_path}\n  - {pdf_path}")


if __name__ == "__main__":
    main()