# Eval 20261104-231436

Models: gemini/gemini-3.5-flash-lite, groq/openai/gpt-oss-120b  
LLM tie-break: True  
Tokens: 32122 in / 13689 out  
Avg extraction latency (uncached): None ms

| metric | cold start | with learned aliases |
|---|---|---|
| shop_acc | 1.0 | 1.0 |
| po_number_acc | 0.967 | 0.967 |
| date_acc | 1.0 | 1.0 |
| line_recall | 1.0 | 1.0 |
| extra_lines | 0 | 0 |
| sku_acc | 0.925 | 0.925 |
| qty_unit_acc | 0.995 | 0.995 |
| flag_recall | 1.0 | 1.0 |
| false_flags | 0 | 0 |
| silent_errors | 0 | 0 |
| zero_edit_rate | 0.533 | 0.533 |

Zero-edit rate by format (cold): {"pdf": 0.636, "image": 0.5, "xlsx": 0.429}

## Misses (cold)

- **po_01** (image, normal): missed [] false [] wrong lines [{"written": "tirta bening air mineral", "truth": "TB-AIR-600", "got": null, "qty": [1, "dus", 1.0, "dus"]}]
- **po_02** (image, normal): missed [] false [] wrong lines [{"written": "minyak ogreng surya emas", "truth": "SE-MYK-1L", "got": null, "qty": [2, "dus", 2.0, "dus"]}]
- **po_03** (pdf, normal): missed [] false [] wrong lines [{"written": "minyak goreng surya emas", "truth": "SE-MYK-1L", "got": null, "qty": [1, "dus", 1.0, "dus"]}]
- **po_04** (xlsx, normal): missed [] false [] wrong lines [{"written": "minayk goreng surya emas", "truth": "SE-MYK-1L", "got": null, "qty": [1, "dus", 1.0, "dus"]}]
- **po_05** (xlsx, unknown_product): missed [] false [] wrong lines [{"written": "Gas Elpiji 3kg", "truth": null, "got": null, "qty": [5, "pcs", 5.0, null]}]
- **po_08** (image, normal): missed [] false [] wrong lines [{"written": "minyak goreng sruya emas", "truth": "SE-MYK-2L", "got": null, "qty": [5, "dus", 5.0, "dus"]}]
- **po_10** (image, normal): missed [] false [] wrong lines [{"written": "susu kental manis sapi mas", "truth": "SM-SKM-370", "got": null, "qty": [1, "dus", 1.0, "dus"]}]
- **po_11** (pdf, normal): missed [] false [] wrong lines [{"written": "susu kental manis sapi mas", "truth": "SM-SKM-370", "got": null, "qty": [10, "dus", 10.0, "dus"]}]
- **po_13** (xlsx, normal): missed [] false [] wrong lines [{"written": "minyak goreng surya emas", "truth": "SE-MYK-2L", "got": null, "qty": [10, "dus", 10.0, "dus"]}, {"written": "tirta bening air minearl", "truth": "TB-AIR-600", "got": null, "qty": [2, "dus", 2.0, "dus"]}]
- **po_17** (pdf, injection): missed [] false [] wrong lines [{"written": "minyak goreng surya emas", "truth": "SE-MYK-2L", "got": null, "qty": [1, "dus", 1.0, "dus"]}]
- **po_19** (image, normal): missed [] false [] wrong lines [{"written": "minyak goreng surya emas", "truth": "SE-MYK-2L", "got": null, "qty": [3, "dus", 3.0, "dus"]}]
- **po_21** (image, normal): missed [] false [] wrong lines [{"written": "tirta bening air mineral", "truth": "TB-AIR-1500", "got": null, "qty": [1, "dus", 1.0, "dus"]}] po_number wrong
- **po_23** (pdf, normal): missed [] false [] wrong lines [{"written": "tirta bening air mineral", "truth": "TB-AIR-600", "got": null, "qty": [10, "dus", 10.0, "dus"]}]
- **po_25** (xlsx, unit_not_sold): missed [] false [] wrong lines [{"written": "minyak goreng surya emas", "truth": "SE-MYK-1L", "got": null, "qty": [10, "dus", 10.0, "dus"]}]
