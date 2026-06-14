from datetime import date
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.image import imread


# Define the project folders, source dataset, and generated chart image names.
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "supply_chain_data.csv"
OUTPUT_DIR = BASE_DIR / "output"
PDF_PATH = OUTPUT_DIR / "Inventory_Report.pdf"

CHART_FILES = [
    OUTPUT_DIR / "01_stock_levels_by_product_type.png",
    OUTPUT_DIR / "02_supplier_performance.png",
    OUTPUT_DIR / "03_inventory_turnover_by_product.png",
    OUTPUT_DIR / "04_procurement_cost_analysis.png",
    OUTPUT_DIR / "05_order_quantity_trends_by_product_type.png",
    OUTPUT_DIR / "06_slow_moving_inventory.png",
]


# Load the dataset and build a compact summary used on the title page.
def load_summary() -> dict[str, object]:
    frame = pd.read_csv(DATA_PATH)
    summary = {
        "rows": len(frame),
        "unique_products": frame["SKU"].nunique() if "SKU" in frame.columns else len(frame),
        "unique_suppliers": frame["Supplier name"].nunique() if "Supplier name" in frame.columns else 0,
        "total_stock_units": frame["Stock levels"].sum() if "Stock levels" in frame.columns else 0,
        "average_lead_time": frame["Lead times"].mean(skipna=True) if "Lead times" in frame.columns else 0,
        "average_defect_rate": frame["Defect rates"].mean(skipna=True) if "Defect rates" in frame.columns else 0,
    }
    return summary


# Render the title page with the report name, date, and dataset summary statistics.
def create_title_page(pdf: PdfPages, summary: dict[str, object]) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111)
    fig.patch.set_facecolor("white")
    fig.text(0.5, 0.88, "Inventory & Procurement Analytics Report", ha="center", va="center", fontsize=24, fontweight="bold")
    fig.text(0.5, 0.82, date.today().strftime("%B %d, %Y"), ha="center", va="center", fontsize=14)

    summary_text = (
        f"Rows analysed: {summary['rows']:,}\n"
        f"Total products: {summary['unique_products']:,}\n"
        f"Unique suppliers: {summary['unique_suppliers']:,}\n"
        f"Total stock units: {summary['total_stock_units']:,.2f}\n"
        f"Average lead time (days): {summary['average_lead_time']:,.2f}\n"
        f"Average defect rate %: {summary['average_defect_rate']:,.2f}"
    )
    fig.text(
        0.5,
        0.5,
        summary_text,
        ha="center",
        va="center",
        fontsize=13,
        bbox={"boxstyle": "round,pad=0.8", "facecolor": "#f1f5f9", "edgecolor": "#94a3b8"},
        linespacing=1.8,
    )
    fig.text(0.5, 0.14, "Generated from data/supply_chain_data.csv", ha="center", va="center", fontsize=11, color="#475569")
    ax.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


# Render a full-page chart image inside the PDF.
def create_image_page(pdf: PdfPages, chart_path: Path, page_title: str) -> None:
    if not chart_path.exists():
        raise FileNotFoundError(f"Missing chart image: {chart_path}")

    image = imread(chart_path)
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.imshow(image)
    ax.set_title(page_title, pad=12)
    ax.axis("off")
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


# Build the key insights page from the dataset and the saved chart metrics.
def create_insights_page(pdf: PdfPages) -> None:
    frame = pd.read_csv(DATA_PATH)
    frame["Inventory Turnover"] = frame["Number of products sold"] / frame["Stock levels"].where(frame["Stock levels"].ne(0))
    frame["Procurement Cost per Unit"] = frame["Manufacturing costs"] / frame["Order quantities"].where(frame["Order quantities"].ne(0))

    average_turnover = frame["Inventory Turnover"].mean(skipna=True)
    slow_moving_count = frame["Inventory Turnover"].lt(average_turnover).sum()
    highest_turnover_sku = frame.sort_values("Inventory Turnover", ascending=False)["SKU"].iloc[0]
    highest_defect_supplier = frame.groupby("Supplier name")["Defect rates"].mean().sort_values(ascending=False).index[0]
    procurement_by_supplier = frame.groupby("Supplier name").agg({"Manufacturing costs": "sum", "Order quantities": "sum"})
    highest_procurement_supplier = (
        procurement_by_supplier["Manufacturing costs"] / procurement_by_supplier["Order quantities"]
    ).sort_values(ascending=False).index[0]

    insights = [
        f"• Average inventory turnover: {average_turnover:,.2f}",
        f"• Slow-moving products below average turnover: {int(slow_moving_count):,}",
        f"• Highest-turnover product: {highest_turnover_sku}",
        f"• Supplier with the highest average defect rate: {highest_defect_supplier}",
        f"• Supplier with the highest procurement cost per unit: {highest_procurement_supplier}",
        "• Review the slow-moving SKUs first when planning replenishment or markdown actions.",
    ]

    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111)
    fig.text(0.5, 0.9, "Key Insights", ha="center", va="center", fontsize=22, fontweight="bold")
    fig.text(
        0.08,
        0.8,
        "\n".join(insights),
        ha="left",
        va="top",
        fontsize=14,
        bbox={"boxstyle": "round,pad=0.75", "facecolor": "#f8fafc", "edgecolor": "#cbd5e1"},
        linespacing=1.8,
    )
    ax.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


# Assemble the PDF report from the title page, the chart pages, and the insights page.
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = load_summary()

    with PdfPages(PDF_PATH) as pdf:
        create_title_page(pdf, summary)

        chart_titles = [
            "Stock Levels by Product Type",
            "Supplier Performance",
            "Inventory Turnover by Product",
            "Procurement Cost Analysis",
            "Order Quantity Trends by Product Type",
            "Slow Moving Inventory",
        ]
        for chart_path, chart_title in zip(CHART_FILES, chart_titles, strict=True):
            create_image_page(pdf, chart_path, chart_title)

        create_insights_page(pdf)

    print(f"Saved PDF report to {PDF_PATH}")


if __name__ == "__main__":
    main()