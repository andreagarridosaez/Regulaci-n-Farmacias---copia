import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


# ---------------------------------------------------
# 1. Paths
# ---------------------------------------------------

data = Path("datos")
graphs = Path("graficos")
graphs.mkdir(exist_ok=True)


def save_graph(filename):
    plt.tight_layout()
    plt.savefig(graphs / filename, dpi=300, bbox_inches="tight")
    plt.show()


# ---------------------------------------------------
# 2. Historical population of Navarra
# ---------------------------------------------------

years = [1996, 1998, 1999] + list(range(2000, 2011))
Navarra_population = []

for year in years:
    extension = ".xlsx" if year == 1996 else ".xls"
    file = data / "municipios_ine" / "pobmun" / f"pobmun{str(year)[-2:]}{extension}"

    # 1998 has a different format
    if year == 1998:
        year_data = pd.read_excel(file)
        year_data.columns = ["CPRO", "CMUN", "NOMBRE", "TOTAL", "VARONES", "MUJERES"]

    else:
        for header in range(8):
            year_data = pd.read_excel(file, header=header)
            year_data.columns = year_data.columns.astype(str).str.strip()

            if "CPRO" in year_data.columns:
                break

    year_data["CPRO"] = pd.to_numeric(
        year_data["CPRO"],
        errors="coerce"
    )

    Navarra = year_data[
        year_data["CPRO"] == 31
    ]

    population_column = next(
        column for column in Navarra.columns
        if (
            str(column).startswith("POB")
            or str(column).upper() == "TOTAL"
            or "AMBOS" in str(column).upper()
        )
    )

    Navarra_population.append({
        "year": year,
        "population": Navarra[population_column].sum()
    })


population_series = pd.DataFrame(Navarra_population)

print("\nPopulation of Navarra:")
print(population_series)


# ---------------------------------------------------
# 3. Historical pharmacies
# ---------------------------------------------------

historical_pharmacies = {
    1999: 308,
    2000: 309,
    2001: 392,
    2002: 501,
    2003: 527,
    2004: 538,
    2005: 547
}

analysis_data = population_series.copy()

analysis_data["pharmacies"] = (
    analysis_data["year"]
    .map(historical_pharmacies)
)

analysis_data["pharmacies_per_10000"] = (
    analysis_data["pharmacies"]
    / analysis_data["population"]
    * 10000
).round(2)

print("\nHistorical analysis:")
print(analysis_data)


# ---------------------------------------------------
# 4. Graph 1: Pharmacy supply
# ---------------------------------------------------

graph_data = analysis_data.dropna(
    subset=["pharmacies"]
)

plt.figure(figsize=(9, 5))

plt.plot(
    graph_data["year"],
    graph_data["pharmacies_per_10000"],
    marker="o"
)

plt.axvline(
    2000,
    linestyle="--",
    label="Ley Foral 12/2000"
)

for year, value in zip(
    graph_data["year"],
    graph_data["pharmacies_per_10000"]
):
    plt.text(
        year,
        value + 0.12,
        f"{value:.2f}",
        ha="center"
    )

plt.xlabel("Year")
plt.ylabel("Pharmacies per 10,000 inhabitants")
plt.title("Pharmacy supply before and after the 2000 reform")

plt.legend()
plt.grid(alpha=0.3)

save_graph("farmacias_por_10000.png")


# ---------------------------------------------------
# 5. Population and pharmacy growth, 2000-2005
# ---------------------------------------------------

data_by_year = analysis_data.set_index("year")

start = data_by_year.loc[2000]
end = data_by_year.loc[2005]

population_growth = (
    end["population"] / start["population"] - 1
) * 100

pharmacy_growth = (
    end["pharmacies"] / start["pharmacies"] - 1
) * 100

print("\nGrowth between 2000 and 2005:")
print(f"Population growth: {population_growth:.2f}%")
print(f"Pharmacy growth: {pharmacy_growth:.2f}%")




# ---------------------------------------------------
# 7. Historical growth by municipality size
# ---------------------------------------------------

municipality_groups = [
    "< 500",
    "500 - 1,000",
    "1,000 - 5,000",
    "5,000 - 10,000",
    "10,000 - 15,000"
]

before_reform = [
    1.2,
    0.0,
    0.0,
    0.0,
    0.0
]

after_reform = [
    -4.2,
    3.0,
    30.4,
    39.6,
    28.6
]

municipality_growth = pd.DataFrame({
    "Municipality size": municipality_groups,
    "1998-2000": before_reform,
    "2000-2003": after_reform
})

print("\nPharmacy growth by municipality size:")
print(municipality_growth)


# ---------------------------------------------------
# 8. Graph 3: Entry by municipality size
# ---------------------------------------------------

x = np.arange(len(municipality_groups))
width = 0.35

plt.figure(figsize=(10, 6))

before_bars = plt.bar(
    x - width / 2,
    before_reform,
    width,
    label="Before reform (1998-2000)"
)

after_bars = plt.bar(
    x + width / 2,
    after_reform,
    width,
    label="After reform (2000-2003)"
)

plt.bar_label(
    before_bars,
    fmt="%.1f%%",
    padding=3
)

plt.bar_label(
    after_bars,
    fmt="%.1f%%",
    padding=3
)

plt.axhline(
    0,
    linewidth=1
)

plt.xticks(
    x,
    municipality_groups
)

plt.xlabel("Municipality population")
plt.ylabel("Annual pharmacy growth (%)")
plt.title("Did pharmacy entry reach smaller municipalities?")

plt.legend()
plt.grid(axis="y", alpha=0.3)

save_graph("crecimiento_farmacias_municipios.png")


# ---------------------------------------------------
# Current municipal coverage
# ---------------------------------------------------

import geopandas as gpd
import zipfile
import unicodedata
import re


pharmacies = pd.read_csv(data / "farmacias.csv")

with zipfile.ZipFile(data / "DOTACI_Sym_Farmacias.zip") as zip_file:
    zip_file.extractall(data / "farmacias_map")

pharmacy_map = gpd.read_file(
    data / "farmacias_map" / "DOTACI_Sym_Farmacias.shp"
)


def clean_name(name):
    name = unicodedata.normalize("NFKD", str(name))
    name = name.encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"\s+", " ", name.replace("<>", "/").replace(" / ", "/"))


pharmacies["key"] = pharmacies["Localidad"].apply(clean_name)
pharmacy_map["key"] = pharmacy_map["POBLACION"].apply(clean_name)

municipality_codes = (
    pharmacy_map[["key", "CMUNICIPIO"]]
    .drop_duplicates("key")
)

pharmacies = pharmacies.merge(
    municipality_codes,
    on="key",
    how="left"
)


# Localities whose current spelling differs from the geographic file
manual_codes = {
    "Estella/Lizarra": 97,
    "Uharte-Arakil": 123,
    "Etxarri-Aranatz": 84,
    "Larrainzar": 236,
    "Barañain": 901,
    "Noáin": 88,
    "Abárzuza": 2,
    "Ancín": 14,
    "Erice": 40,
    "Artica": 902,
    "Berriosuso": 902
}

pharmacies["CMUNICIPIO"] = pharmacies["CMUNICIPIO"].fillna(
    pharmacies["Localidad"].map(manual_codes)
)

print("\nPharmacies without municipality:")
print(pharmacies["CMUNICIPIO"].isna().sum())


# ---------------------------------------------------
# Population and pharmacies by municipality
# ---------------------------------------------------

population_2025 = pd.read_excel(
    data / "municipios_ine" / "pobmun" / "pobmun25.xlsx",
    header=1
)

Navarra_2025 = population_2025[
    population_2025["CPRO"] == 31
][["CMUN", "NOMBRE", "POB25"]].copy()

pharmacies_by_municipality = (
    pharmacies.groupby("CMUNICIPIO")
    .size()
    .reset_index(name="pharmacies")
)

pharmacies_by_municipality["CMUNICIPIO"] = (
    pharmacies_by_municipality["CMUNICIPIO"].astype(int)
)

municipal_data = Navarra_2025.merge(
    pharmacies_by_municipality,
    left_on="CMUN",
    right_on="CMUNICIPIO",
    how="left"
)

municipal_data["pharmacies"] = (
    municipal_data["pharmacies"].fillna(0).astype(int)
)


# ---------------------------------------------------
# Municipalities without a pharmacy
# ---------------------------------------------------

municipal_data["without_pharmacy"] = (
    municipal_data["pharmacies"] == 0
)

population_without = municipal_data.loc[
    municipal_data["without_pharmacy"],
    "POB25"
].sum()

share_without = (
    population_without
    / municipal_data["POB25"].sum()
    * 100
)

print("\nCurrent pharmacy coverage:")
print(f"Municipalities: {len(municipal_data)}")
print(f"Without pharmacy: {municipal_data['without_pharmacy'].sum()}")
print(f"Population without pharmacy: {population_without}")
print(f"Share of population without pharmacy: {share_without:.2f}%")


# ---------------------------------------------------
# 9. Current coverage by municipality size
# ---------------------------------------------------

size_labels = [
    "< 500",
    "500 - 1,000",
    "1,000 - 5,000",
    "5,000 - 10,000",
    "10,000 - 15,000",
    "> 15,000"
]

municipal_data["size_group"] = pd.cut(
    municipal_data["POB25"],
    bins=[0, 500, 1000, 5000, 10000, 15000, np.inf],
    labels=size_labels,
    right=False
)

coverage_by_size = (
    municipal_data.groupby("size_group", observed=False)
    .agg(
        municipalities=("NOMBRE", "count"),
        without_pharmacy=("without_pharmacy", "sum")
    )
    .reset_index()
)

coverage_by_size["without_pharmacy_share"] = (
    coverage_by_size["without_pharmacy"]
    / coverage_by_size["municipalities"]
    * 100
)

print("\nCurrent coverage by municipality size:")
print(coverage_by_size.round(1))


# ---------------------------------------------------
# 10. Graph: municipalities without a pharmacy
# ---------------------------------------------------

plt.figure(figsize=(10, 6))

bars = plt.bar(
    coverage_by_size["size_group"],
    coverage_by_size["without_pharmacy_share"]
)

plt.bar_label(
    bars,
    fmt="%.1f%%",
    padding=3
)

plt.xlabel("Municipality population")
plt.ylabel("Municipalities without a pharmacy (%)")
plt.title("Where is lack of pharmacy coverage concentrated in Navarra?")

plt.ylim(0, 95)
plt.grid(axis="y", alpha=0.3)

save_graph("cobertura_actual_por_municipio.png")