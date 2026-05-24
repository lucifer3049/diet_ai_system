from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken


class EncryptedCharField(models.TextField):
    """
    Fernet 對稱加密的文字欄位。
    寫入時加密，讀出時解密，DB 中永遠是密文。
    需要在 settings 設定 FIELD_ENCRYPTION_KEY（32-byte URL-safe base64）。

    生成 key：
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """

    def _fernet(self) -> Fernet:
        key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
        if not key:
            raise ValueError("settings.FIELD_ENCRYPTION_KEY 未設定，無法加解密欄位")
        return Fernet(key.encode() if isinstance(key, str) else key)

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return self._fernet().decrypt(value.encode()).decode()
        except (InvalidToken, Exception):
            return value  # 相容舊的未加密資料

    def get_prep_value(self, value):
        if not value:
            return value
        return self._fernet().encrypt(value.encode()).decode()
