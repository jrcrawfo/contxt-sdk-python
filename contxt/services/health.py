from ..auth import Auth
from ..models.health import Health
from .api import ApiEnvironment, ConfiguredLegacyApi
from ..utils.config import ContxtEnvironmentConfig


class HealthService(ConfiguredLegacyApi):
    """Health API client"""

    def __init__(self, auth: Auth, env_config: ContxtEnvironmentConfig, **kwargs) -> None:
        super().__init__(env_config=env_config, auth=auth, **kwargs)

    def create_health_status(self, org_id: str, asset_id: str, health: Health) -> Health:
        resp = self.post(f"{org_id}/assets/{asset_id}", data=health.post())
        return Health.from_api(resp)
