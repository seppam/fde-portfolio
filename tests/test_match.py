import pytest

from po_agent.catalog import normalize_unit, products
from po_agent.match import (
    MemoryAliases,
    fuzzy_candidates,
    match_product,
    match_shop,
    match_unit,
    norm,
)


@pytest.mark.parametrize("raw,unit", [("dus", "dus"), ("KTN", "dus"), ("karton", "dus"), ("dos.", "dus"),
                                      ("bks", "pcs"), ("rcg", "renceng"), ("renteng", "renceng"),
                                      ("karung", "sak"), ("tabung", None), (None, None)])
def test_unit_synonyms(raw, unit):
    assert normalize_unit(raw) == unit


def test_norm_joins_size_and_drops_punctuation():
    assert norm("Mie Raja Goreng 85 g!!") == "mie raja goreng 85g"


@pytest.mark.parametrize("raw,sku", [
    ("Mie Raja Goreng 85g", "MR-GRG-85"),
    ("mie raja goreng", "MR-GRG-85"),
    ("MR GRG 85", "MR-GRG-85"),
    ("kopi senja mocca", "KS-MOC-30"),
    ("minayk goreng surya emas 1L", "SE-MYK-1L"),
])
def test_fuzzy_top_candidate(raw, sku):
    assert fuzzy_candidates(raw)[0][0] == sku


def test_size_disagreement_is_penalised():
    # '70' should not prefer the 85g pack
    cands = dict(fuzzy_candidates("mie raja goreng 70"))
    assert cands.get("MR-GRG-85", 0) < 88


def test_alias_wins_over_fuzzy():
    al = MemoryAliases()
    al.put("C001", "indomi grg", "MR-GRG-85")
    sku, conf, method, *_ = match_product("Indomi GRG", "C001", al, use_llm=False)
    assert (sku, conf, method) == ("MR-GRG-85", 1.0, "alias")


def test_shop_specific_alias_does_not_leak_to_other_shop():
    al = MemoryAliases()
    al.put("C001", "barang biasa", "MR-GRG-85")
    sku, *_ = match_product("barang biasa", "C002", al, use_llm=False)
    assert sku is None  # C002 falls back to fuzzy, which finds nothing; never the C001 alias
    assert al.get("C002", "barang biasa") is None


def test_unknown_product_is_not_forced():
    sku, _conf, method, *_ = match_product("Gas Elpiji 3kg", None, MemoryAliases(), use_llm=False)
    assert sku is None and method == "none"


def test_ambiguous_without_llm_stays_unmatched():
    # 'goreng' fits two noodle SKUs; without an LLM the agent must not guess
    sku, _, method, cands, _ = match_product("goreng", None, MemoryAliases(), use_llm=False)
    assert sku is None and method == "ambiguous" and len(cands) >= 2


def test_missing_size_is_ambiguous_not_unknown():
    sku, _, method, cands, _ = match_product("minyak goreng surya emas", None, MemoryAliases(), use_llm=False)
    assert sku is None and method == "ambiguous"
    assert {"SE-MYK-1L", "SE-MYK-2L"} <= {c[0] for c in cands}


def test_shop_history_picks_the_size_it_always_buys():
    sku, conf, method, *_ = match_product("minyak goreng surya emas", "C001", MemoryAliases(),
                                          use_llm=False, history={"SE-MYK-2L", "MR-GRG-85"})
    assert (sku, method) == ("SE-MYK-2L", "history") and conf < 0.9


def test_word_order_and_city_pick_the_right_shop():
    # 'Toko Bintang Abadi' and 'Toko Abadi Bintang' both exist
    shop, _ = match_shop("Toko Abadi Bintang - Cikampek")
    assert shop.name == "Toko Abadi Bintang"


def test_missing_unit_defaults_to_first_pack():
    assert match_unit(None, products()["MR-GRG-85"]) == "dus"
    assert match_unit("tabung", products()["MR-GRG-85"]) is None


def test_shop_by_email_beats_name():
    shop, conf = match_shop("nama apa saja", "order.c012@toko-contoh.test")
    assert shop.shop_id == "C012" and conf == 1.0


def test_shop_by_partial_name():
    shop, conf = match_shop("Makmur Sumber")
    assert shop.shop_id == "C012" and conf >= 0.85


def test_shop_unknown():
    shop, _ = match_shop("PT Tidak Ada Hubungannya Sama Sekali")
    assert shop is None
