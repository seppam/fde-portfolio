# Eval 20261104-230606

Models: gemini/gemini-3.5-flash-lite, groq/openai/gpt-oss-120b  
LLM tie-break: True  
Tokens: 32388 in / 13799 out  
Avg extraction latency (uncached): 22479 ms

| metric | cold start | with learned aliases |
|---|---|---|
| shop_acc | 0.933 | 0.933 |
| po_number_acc | 0.833 | 0.833 |
| date_acc | 1.0 | 1.0 |
| line_recall | 1.0 | 1.0 |
| extra_lines | 0 | 0 |
| sku_acc | 0.925 | 0.925 |
| qty_unit_acc | 0.995 | 0.995 |
| flag_recall | 0.889 | 0.889 |
| false_flags | 22 | 22 |
| zero_edit_rate | 0.433 | 0.433 |

Zero-edit rate by format (cold): {"pdf": 0.455, "image": 0.417, "xlsx": 0.429}

## Misses (cold)

- **po_01** (image, normal): missed [] false ['CREDIT_LIMIT', 'UNKNOWN_PRODUCT'] wrong lines [{"written": "tirta bening air mineral", "truth": "TB-AIR-600", "got": null, "qty": [1, "dus", 1.0, "dus"]}]
- **po_02** (image, normal): missed [] false ['UNKNOWN_PRODUCT'] wrong lines [{"written": "minyak ogreng surya emas", "truth": "SE-MYK-1L", "got": null, "qty": [2, "dus", 2.0, "dus"]}]
- **po_03** (pdf, normal): missed [] false ['CREDIT_LIMIT', 'UNKNOWN_PRODUCT'] wrong lines [{"written": "minyak goreng surya emas", "truth": "SE-MYK-1L", "got": null, "qty": [1, "dus", 1.0, "dus"]}]
- **po_04** (xlsx, normal): missed [] false ['UNKNOWN_PRODUCT'] wrong lines [{"written": "minayk goreng surya emas", "truth": "SE-MYK-1L", "got": null, "qty": [1, "dus", 1.0, "dus"]}]
- **po_05** (xlsx, unknown_product): missed [] false [] wrong lines [{"written": "Gas Elpiji 3kg", "truth": null, "got": null, "qty": [5, "pcs", 5.0, null]}]
- **po_08** (image, normal): missed [] false ['UNKNOWN_PRODUCT'] wrong lines [{"written": "minyak goreng sruya emas", "truth": "SE-MYK-2L", "got": null, "qty": [5, "dus", 5.0, "dus"]}] po_number wrong
- **po_09** (pdf, discontinued): missed [] false [] wrong lines [] po_number wrong
- **po_10** (image, normal): missed [] false ['UNKNOWN_PRODUCT'] wrong lines [{"written": "susu kental manis sapi mas", "truth": "SM-SKM-370", "got": null, "qty": [1, "dus", 1.0, "dus"]}]
- **po_11** (pdf, normal): missed [] false ['UNKNOWN_PRODUCT'] wrong lines [{"written": "susu kental manis sapi mas", "truth": "SM-SKM-370", "got": null, "qty": [10, "dus", 10.0, "dus"]}]
- **po_13** (xlsx, normal): missed [] false ['UNKNOWN_PRODUCT'] wrong lines [{"written": "minyak goreng surya emas", "truth": "SE-MYK-2L", "got": null, "qty": [10, "dus", 10.0, "dus"]}, {"written": "tirta bening air minearl", "truth": "TB-AIR-600", "got": null, "qty": [2, "dus", 2.0, "dus"]}] shop wrong
- **po_14** (image, duplicate): missed ['DUPLICATE_PO'] false ['CREDIT_LIMIT'] wrong lines [] po_number wrong
- **po_16** (xlsx, normal): missed [] false ['CREDIT_LIMIT'] wrong lines []
- **po_17** (pdf, injection): missed [] false ['UNKNOWN_PRODUCT'] wrong lines [{"written": "minyak goreng surya emas", "truth": "SE-MYK-2L", "got": null, "qty": [1, "dus", 1.0, "dus"]}]
- **po_19** (image, normal): missed [] false ['CREDIT_LIMIT', 'UNKNOWN_PRODUCT'] wrong lines [{"written": "minyak goreng surya emas", "truth": "SE-MYK-2L", "got": null, "qty": [3, "dus", 3.0, "dus"]}] po_number wrong
- **po_20** (pdf, price_mismatch): missed [] false ['CREDIT_LIMIT'] wrong lines []
- **po_21** (image, normal): missed [] false ['CREDIT_LIMIT', 'UNKNOWN_PRODUCT'] wrong lines [{"written": "tirta bening air mineral", "truth": "TB-AIR-1500", "got": null, "qty": [1, "dus", 1.0, "dus"]}] po_number wrong
- **po_23** (pdf, normal): missed [] false ['UNKNOWN_PRODUCT'] wrong lines [{"written": "tirta bening air mineral", "truth": "TB-AIR-600", "got": null, "qty": [10, "dus", 10.0, "dus"]}]
- **po_25** (xlsx, unit_not_sold): missed [] false ['UNKNOWN_PRODUCT'] wrong lines [{"written": "minyak goreng surya emas", "truth": "SE-MYK-1L", "got": null, "qty": [10, "dus", 10.0, "dus"]}]
- **po_28** (pdf, normal): missed [] false ['CREDIT_LIMIT'] wrong lines [] shop wrong
- **po_29** (pdf, qty_outlier): missed [] false ['CREDIT_LIMIT'] wrong lines []
