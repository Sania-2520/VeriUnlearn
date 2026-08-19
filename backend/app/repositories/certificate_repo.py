from __future__ import annotations

from app.db.models import Certificate
from app.repositories.base import BaseRepository


class CertificateRepository(BaseRepository[Certificate]):
    model = Certificate

    async def create(self, certificate: Certificate) -> Certificate:
        return await self.add(certificate)
