"""
台灣衛福部食品藥物管理署（FDA）食品成分資料庫匯入邏輯。

官方資料來源：https://consumer.fda.gov.tw/Food/TFND.aspx
CSV 格式：每 100g 的營養成分，欄位名稱為繁體中文。

預期的 CSV 欄位對應（可透過 COLUMN_MAP 調整）：
    樣品名稱      → food_name
    熱量          → calories  (kcal/100g)
    粗蛋白        → protein   (g/100g)
    粗脂肪        → fat       (g/100g)
    飽和脂肪      → saturated_fat
    反式脂肪      → trans_fat
    總碳水化合物  → carbohydrates
    糖質總量      → sugar
    鈉            → sodium    (mg/100g)
"""
import csv
import io
import logging
import urllib.request
from decimal import Decimal, InvalidOperation
from typing import IO

logger = logging.getLogger(__name__)

# 衛福部 CSV 欄位 → model 欄位對應（可視實際 CSV 調整）
DEFAULT_COLUMN_MAP: dict[str, str] = {
    '樣品名稱':     'food_name',
    '熱量':         'calories',
    '粗蛋白':       'protein',
    '粗脂肪':       'fat',
    '飽和脂肪':     'saturated_fat',
    '反式脂肪':     'trans_fat',
    '總碳水化合物': 'carbohydrates',
    '糖質總量':     'sugar',
    '鈉':           'sodium',
}


def _to_decimal(value: str) -> Decimal:
    """將 CSV 字串轉為 Decimal，空值或非數字回傳 0。"""
    try:
        cleaned = value.strip().replace(',', '')
        return Decimal(cleaned) if cleaned else Decimal('0')
    except InvalidOperation:
        return Decimal('0')


class TaiwanFDAImporter:
    """
    讀取 FDA CSV，批次寫入 FoodNutritionCache。
    import_from_file(f)  ← 接受 file-like object
    import_from_url(url) ← 下載後呼叫上面的方法
    """

    def __init__(self, column_map: dict[str, str] | None = None):
        self.column_map = column_map or DEFAULT_COLUMN_MAP

    # ── 公開方法 ────────────────────────────────────────────────────────────────

    def import_from_file(self, file_obj: IO, encoding: str = 'utf-8-sig') -> dict:
        """從 file-like object 匯入，回傳 {created, updated, skipped} 統計。"""
        text = io.TextIOWrapper(file_obj, encoding=encoding, newline='')
        return self._process(text)

    def import_from_path(self, path: str, encoding: str = 'utf-8-sig') -> dict:
        """從本機路徑匯入。"""
        with open(path, 'rb') as f:
            return self.import_from_file(f, encoding=encoding)

    def import_from_url(self, url: str) -> dict:
        """下載 CSV 後匯入。"""
        logger.info(f"下載 FDA CSV：{url}")
        with urllib.request.urlopen(url, timeout=30) as response:
            return self.import_from_file(response)

    # ── 內部邏輯 ────────────────────────────────────────────────────────────────

    def _process(self, text_io) -> dict:
        from nutrition.models import FoodNutritionCache

        reader = csv.DictReader(text_io)
        created = updated = skipped = 0
        batch: list[FoodNutritionCache] = []

        for row in reader:
            record = self._map_row(row)
            if not record:
                skipped += 1
                continue

            obj, is_created = FoodNutritionCache.objects.update_or_create(
                food_name=record['food_name'],
                defaults={**record, 'data_source': 'taiwan_fda'},
            )
            if is_created:
                created += 1
            else:
                updated += 1

        logger.info(f"FDA 匯入完成：新增 {created}，更新 {updated}，略過 {skipped}")
        return {'created': created, 'updated': updated, 'skipped': skipped}

    def _map_row(self, row: dict) -> dict | None:
        """將 CSV row 對應到 model 欄位；無法對應或食物名稱空白則回傳 None。"""
        result: dict = {}
        for csv_col, model_field in self.column_map.items():
            value = row.get(csv_col, '').strip()
            if model_field == 'food_name':
                if not value:
                    return None
                result['food_name'] = value.lower()
            else:
                result[model_field] = _to_decimal(value)

        if 'food_name' not in result:
            return None
        return result
