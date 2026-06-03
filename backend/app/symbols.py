"""Yahoo Finance symbol mapping — mirrors the frontend src/constants/symbols.ts.

`id` matches the ids used in the frontend's static data so live values can be
merged into the existing cards.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolDef:
    id: str
    yahoo: str
    name: str
    unit: str
    currency: str
    category: str


CORE: list[SymbolDef] = [
    SymbolDef("brent", "BZ=F", "Brent Crude", "bbl", "USD", "crude"),
    SymbolDef("wti", "CL=F", "WTI Crude", "bbl", "USD", "crude"),
    SymbolDef("vix", "^VIX", "VIX", "idx", "", "macro"),
    SymbolDef("dxy", "DX-Y.NYB", "DXY", "idx", "", "macro"),
]

MACRO: list[SymbolDef] = [
    SymbolDef("sp500", "^GSPC", "S&P 500", "idx", "", "macro"),
    SymbolDef("ust10y", "^TNX", "US 10Y Yield", "%", "", "macro"),
    SymbolDef("gold", "GC=F", "Gold", "oz", "USD", "macro"),
    SymbolDef("copper", "HG=F", "Copper", "lb", "USD", "macro"),
]

PRODUCTS: list[SymbolDef] = [
    SymbolDef("rbob", "RB=F", "RBOB Gasoline", "gal", "USD", "products"),
    SymbolDef("heatoil", "HO=F", "Heating Oil", "gal", "USD", "products"),
]

ALL: list[SymbolDef] = [*CORE, *MACRO, *PRODUCTS]

BY_ID: dict[str, SymbolDef] = {s.id: s for s in ALL}

# Named groups the API can serve directly.
GROUPS: dict[str, list[SymbolDef]] = {
    "core": CORE,
    "macro": MACRO,
    "products": PRODUCTS,
    "all": ALL,
}
