"""
python manage.py import_taiwan_fda --file /path/to/tfnd.csv
python manage.py import_taiwan_fda --url https://...
python manage.py import_taiwan_fda --file data.csv --encoding big5
"""
from django.core.management.base import BaseCommand, CommandError
from nutrition.fda_importer import TaiwanFDAImporter


class Command(BaseCommand):
    help = "從台灣衛福部 FDA 食品成分資料庫 CSV 匯入營養資料到 FoodNutritionCache"

    def add_arguments(self, parser):
        source = parser.add_mutually_exclusive_group(required=True)
        source.add_argument('--file', metavar='PATH', help='本機 CSV 檔案路徑')
        source.add_argument('--url',  metavar='URL',  help='遠端 CSV 下載網址')
        parser.add_argument(
            '--encoding', default='utf-8-sig',
            help='CSV 編碼（預設 utf-8-sig；Big5 用 big5）'
        )

    def handle(self, *args, **options):
        importer = TaiwanFDAImporter()

        try:
            if options['file']:
                self.stdout.write(f"從檔案匯入：{options['file']}")
                result = importer.import_from_path(options['file'], encoding=options['encoding'])
            else:
                self.stdout.write(f"從 URL 下載匯入：{options['url']}")
                result = importer.import_from_url(options['url'])
        except FileNotFoundError as e:
            raise CommandError(f"找不到檔案：{e}")
        except Exception as e:
            raise CommandError(f"匯入失敗：{e}")

        self.stdout.write(self.style.SUCCESS(
            f"完成！新增 {result['created']} 筆，"
            f"更新 {result['updated']} 筆，"
            f"略過 {result['skipped']} 筆"
        ))
