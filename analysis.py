from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# Define the project folders and the source dataset path.
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "supply_chain_data.csv"
OUTPUT_DIR = BASE_DIR / "output"


# Store the exact CSV column names discovered in the dataset.
PRODUCT_TYPE_COL = "Product type"
SKU_COL = "SKU"
STOCK_LEVELS_COL = "Stock levels"
UNITS_SOLD_COL = "Number of products sold"
ORDER_QUANTITIES_COL = "Order quantities"
SUPPLIER_COL = "Supplier name"
LEAD_TIMES_COL = "Lead times"
MANUFACTURING_COSTS_COL = "Manufacturing costs"
DEFECT_RATES_COL = "Defect rates"


# Validate that the required columns exist before the analysis starts.
def require_columns(frame: pd.DataFrame, required_columns: list[str]) -> None:
    missing_columns = [column for column in required_columns if column not in frame.columns]
    if missing_columns:
        raise KeyError(f"Missing required columns: {missing_columns}")


# Fill missing values so the charts and summary are built from a clean dataset.
def fill_missing_values(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned_frame = frame.copy()
    for column in cleaned_frame.columns:
        if pd.api.types.is_numeric_dtype(cleaned_frame[column]):
            median_value = cleaned_frame[column].median()
            if pd.isna(median_value):
                median_value = 0
            cleaned_frame[column] = cleaned_frame[column].fillna(median_value)
        else:
            mode_values = cleaned_frame[column].mode(dropna=True)
            fallback_value = mode_values.iloc[0] if not mode_values.empty else "Unknown"
            cleaned_frame[column] = cleaned_frame[column].fillna(fallback_value)
    return cleaned_frame


# Safely divide two numeric series without creating infinite values.
def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    ratio = numerator.where(denominator.ne(0)) / denominator.where(denominator.ne(0))
    return ratio.replace([float("inf"), float("-inf")], pd.NA)


# Build the derived metrics requested by the analysis brief.
def add_calculated_columns(frame: pd.DataFrame) -> pd.DataFrame:
    calculated_frame = frame.copy()
    calculated_frame["Inventory Turnover"] = safe_divide(
        calculated_frame[UNITS_SOLD_COL], calculated_frame[STOCK_LEVELS_COL]
    )
    calculated_frame["Procurement Cost per Unit"] = safe_divide(
        calculated_frame[MANUFACTURING_COSTS_COL], calculated_frame[ORDER_QUANTITIES_COL]
    )

    defect_rate_series = pd.to_numeric(calculated_frame[DEFECT_RATES_COL], errors="coerce")
    finite_defect_rates = defect_rate_series.dropna()
    if not finite_defect_rates.empty and finite_defect_rates.max() <= 1:
        calculated_frame["Defect Rate %"] = defect_rate_series * 100
    else:
        calculated_frame["Defect Rate %"] = defect_rate_series

    return calculated_frame


# Save a bar chart to the output folder using a consistent image format.
def save_bar_chart(fig: plt.Figure, filename: str) -> None:
    fig.savefig(OUTPUT_DIR / filename, dpi=300, bbox_inches="tight")
    plt.close(fig)


# Create the stock levels by product type chart.
def create_stock_levels_chart(frame: pd.DataFrame) -> None:
    chart_frame = (
        frame.groupby(PRODUCT_TYPE_COL, dropna=False)[STOCK_LEVELS_COL]
        .sum()
        .sort_values(ascending=True)
    )
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(chart_frame.index.astype(str), chart_frame.values, color="#2a6f97")
    ax.set_title("Stock Levels by Product Type")
    ax.set_xlabel("Total Stock Levels")
    ax.set_ylabel("Product Type")
    fig.tight_layout()
    save_bar_chart(fig, "01_stock_levels_by_product_type.png")


# Create the supplier performance chart using average lead times and defect rates.
def create_supplier_performance_chart(frame: pd.DataFrame) -> None:
    chart_frame = (
        frame.groupby(SUPPLIER_COL, dropna=False)
        .agg({LEAD_TIMES_COL: "mean", "Defect Rate %": "mean"})
        .sort_index()
    )
    x_positions = range(len(chart_frame.index))
    bar_width = 0.4

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(
        [position - bar_width / 2 for position in x_positions],
        chart_frame[LEAD_TIMES_COL].values,
        width=bar_width,
        label="Lead Times",
        color="#457b9d",
    )
    ax.bar(
        [position + bar_width / 2 for position in x_positions],
        chart_frame["Defect Rate %"].values,
        width=bar_width,
        label="Defect Rate %",
        color="#e76f51",
    )
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(chart_frame.index.astype(str), rotation=0)
    ax.set_title("Supplier Performance")
    ax.set_ylabel("Average Value")
    ax.legend()
    fig.tight_layout()
    save_bar_chart(fig, "02_supplier_performance.png")


# Create the inventory turnover chart for the top 15 products.
def create_inventory_turnover_chart(frame: pd.DataFrame) -> None:
    chart_frame = (
        frame[[SKU_COL, "Inventory Turnover"]]
        .dropna(subset=["Inventory Turnover"])
        .sort_values(by="Inventory Turnover", ascending=False)
        .head(15)
        .sort_values(by="Inventory Turnover", ascending=True)
    )
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(chart_frame[SKU_COL].astype(str), chart_frame["Inventory Turnover"], color="#1d3557")
    ax.set_title("Inventory Turnover by Product")
    ax.set_xlabel("Inventory Turnover")
    ax.set_ylabel("SKU")
    fig.tight_layout()
    save_bar_chart(fig, "03_inventory_turnover_by_product.png")


# Create the procurement cost analysis chart by supplier.
def create_procurement_cost_chart(frame: pd.DataFrame) -> None:
    grouped_frame = frame.groupby(SUPPLIER_COL, dropna=False)[[MANUFACTURING_COSTS_COL, ORDER_QUANTITIES_COL]].sum()
    chart_frame = (grouped_frame[MANUFACTURING_COSTS_COL] / grouped_frame[ORDER_QUANTITIES_COL]).sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(chart_frame.index.astype(str), chart_frame.values, color="#6c757d")
    ax.set_title("Procurement Cost Analysis")
    ax.set_xlabel("Manufacturing Cost per Unit")
    ax.set_ylabel("Supplier")
    fig.tight_layout()
    save_bar_chart(fig, "04_procurement_cost_analysis.png")


# Create the order quantity trends chart by product type.
def create_order_quantity_chart(frame: pd.DataFrame) -> None:
    chart_frame = frame.groupby(PRODUCT_TYPE_COL, dropna=False)[ORDER_QUANTITIES_COL].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(chart_frame.index.astype(str), chart_frame.values, color="#8d99ae")
    ax.set_title("Order Quantity Trends by Product Type")
    ax.set_xlabel("Product Type")
    ax.set_ylabel("Total Order Quantities")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    save_bar_chart(fig, "05_order_quantity_trends_by_product_type.png")


# Create the slow moving inventory chart and highlight below-average products in red.
def create_slow_moving_inventory_chart(frame: pd.DataFrame) -> None:
    turnover_mean = frame["Inventory Turnover"].mean(skipna=True)
    slow_moving_frame = (
        frame[[SKU_COL, "Inventory Turnover"]]
        .dropna(subset=["Inventory Turnover"])
        .loc[lambda data: data["Inventory Turnover"] < turnover_mean]
        .sort_values(by="Inventory Turnover", ascending=True)
    )
    fig, ax = plt.subplots(figsize=(10, max(6, 0.35 * len(slow_moving_frame) + 2)))
    ax.barh(slow_moving_frame[SKU_COL].astype(str), slow_moving_frame["Inventory Turnover"], color="#c1121f")
    ax.set_title("Slow Moving Inventory")
    ax.set_xlabel("Inventory Turnover")
    ax.set_ylabel("SKU")
    fig.tight_layout()
    save_bar_chart(fig, "06_slow_moving_inventory.png")


# Print the summary metrics requested at the end of the analysis.
def print_summary(frame: pd.DataFrame) -> None:
    total_stock_units = frame[STOCK_LEVELS_COL].sum()
    total_products = frame[SKU_COL].nunique()
    average_lead_time = frame[LEAD_TIMES_COL].mean(skipna=True)
    average_defect_rate = frame["Defect Rate %"].mean(skipna=True)
    average_inventory_turnover = frame["Inventory Turnover"].mean(skipna=True)
    slow_moving_count = frame["Inventory Turnover"].lt(average_inventory_turnover).sum()

    print("Analysis Summary")
    print(f"Total Stock Units: {total_stock_units:,.2f}")
    print(f"Total Products: {int(total_products):,}")
    print(f"Average Lead Time (days): {average_lead_time:,.2f}")
    print(f"Average Defect Rate %: {average_defect_rate:,.2f}")
    print(f"Average Inventory Turnover: {average_inventory_turnover:,.2f}")
    print(f"Number of Slow Moving Products (below average turnover): {int(slow_moving_count):,}")


# Run the complete analysis workflow from loading data through chart creation.
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATH)
    print("Detected columns:")
    print(list(df.columns))

    require_columns(
        df,
        [
            PRODUCT_TYPE_COL,
            SKU_COL,
            STOCK_LEVELS_COL,
            UNITS_SOLD_COL,
            ORDER_QUANTITIES_COL,
            SUPPLIER_COL,
            LEAD_TIMES_COL,
            MANUFACTURING_COSTS_COL,
            DEFECT_RATES_COL,
        ],
    )

    df = fill_missing_values(df)
    df = add_calculated_columns(df)

    create_stock_levels_chart(df)
    create_supplier_performance_chart(df)
    create_inventory_turnover_chart(df)
    create_procurement_cost_chart(df)
    create_order_quantity_chart(df)
    create_slow_moving_inventory_chart(df)

    print_summary(df)


if __name__ == "__main__":
    main()