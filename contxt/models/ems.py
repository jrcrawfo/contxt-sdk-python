from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from contxt.models import ApiField, ApiObject, Parsers
from contxt.models.events import Event
from contxt.models.iot import Field


class ResourceType(Enum):
    COMBINED = "combined"
    ELECTRIC = "electric"
    GAS = "gas"
    WATER = "water"


class MainService(ApiObject):
    _api_fields = (
        ApiField("id", data_type=int),
        ApiField("facility_id", data_type=int),
        ApiField("name"),
        ApiField("type", attr_key="resource_type", data_type=ResourceType),
        ApiField("demand_field_id", data_type=int),
        ApiField("usage_field_id", data_type=int),
        ApiField("demand_field", data_type=Field),
        ApiField("usage_field", data_type=Field),
        ApiField("created_at", data_type=Parsers.datetime),
        ApiField("updated_at", data_type=Parsers.datetime),
    )

    def __init__(
        self,
        id: int,
        facility_id: int,
        name: str,
        resource_type: ResourceType,
        demand_field_id: int,
        usage_field_id: int,
        demand_field: Field,
        usage_field: Field,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        super().__init__()
        self.id = id
        self.facility_id = facility_id
        self.name = name
        self.resource_type = resource_type
        self.demand_field_id = demand_field_id
        self.usage_field_id = usage_field_id
        self.demand_field = demand_field
        self.usage_field = demand_field
        self.created_at = created_at
        self.updated_at = updated_at


class Facility(ApiObject):
    _api_fields = (
        ApiField("id", data_type=int),
        ApiField("name"),
        ApiField("asset_id"),
        ApiField("organization_id"),
        ApiField("baseline", data_type=dict),
        ApiField("main_services", data_type=MainService),
        ApiField("created_at", data_type=Parsers.datetime),
        ApiField("updated_at", data_type=Parsers.datetime),
    )

    def __init__(
        self,
        id: int,
        name: str,
        asset_id: str,
        organization_id: str,
        baseline: str,
        main_services: List[MainService],
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        super().__init__()
        self.id = id
        self.name = name
        self.asset_id = asset_id
        self.organization_id = organization_id
        self.baseline = baseline
        self.main_services = main_services
        self.created_at = created_at
        self.updated_at = updated_at


class UtilitySpendPeriod(ApiObject):
    _api_fields = (
        ApiField("date"),
        ApiField("value"),
        ApiField("pro_forma_date", optional=True),
    )

    def __init__(
        self, date: str, value: str, pro_forma_date: Optional[str] = None
    ) -> None:
        super().__init__()
        self.date = date
        self.value = value
        self.pro_forma_date = pro_forma_date


class UtilitySpend(ApiObject):
    _api_fields = (
        ApiField("type"),
        ApiField("currency"),
        ApiField("values", data_type=UtilitySpendPeriod),
    )

    def __init__(
        self, type: str, currency: str, values: List[UtilitySpendPeriod]
    ) -> None:
        super().__init__()
        self.type = type
        self.currency = currency
        self.periods = values


class UtilityUsagePeriod(ApiObject):
    _api_fields = (
        ApiField("date"),
        ApiField("value"),
        ApiField("pro_forma_date", optional=True),
    )

    def __init__(
        self, date: str, value: str, pro_forma_date: Optional[str] = None
    ) -> None:
        super().__init__()
        self.date = date
        self.value = value
        self.pro_forma_date = pro_forma_date


class UtilityUsage(ApiObject):
    _api_fields = (
        ApiField("type"),
        ApiField("unit"),
        ApiField("values", data_type=UtilityUsagePeriod),
    )

    def __init__(self, type: str, unit: str, values: Dict) -> None:
        super().__init__()
        self.type = type
        self.unit = unit
        self.periods = values


class UtilityContractReminder(ApiObject):
    _api_fields = (
        ApiField("utility_contract_id", data_type=int),
        ApiField("user_id", data_type=str),
        ApiField("user_event_subscription_id", data_type=str),
        ApiField("created_at", data_type=Parsers.datetime),
        ApiField("updated_at", data_type=Parsers.datetime),
    )

    def __init__(
        self,
        utility_contract_id: int,
        user_id: str,
        user_event_subscription_id: str,
        created_at: datetime,
        updated_at: datetime,
    ):
        super().__init__()
        self.utility_contract_id = utility_contract_id
        self.user_id = user_id
        self.user_event_subscription_id = user_event_subscription_id
        self.created_at = created_at
        self.updated_at = updated_at


class UtilityContract(ApiObject):
    _api_fields = (
        ApiField("id", data_type=int),
        ApiField("name"),
        ApiField("facility_id", data_type=int),
        ApiField("status"),
        ApiField("start_date", data_type=Parsers.date),
        ApiField("end_date", data_type=Parsers.date),
        ApiField("rate_narrative"),
        ApiField("file_id"),
        ApiField("created_at", data_type=Parsers.datetime),
        ApiField("updated_at", data_type=Parsers.datetime),
        ApiField("created_by"),
        ApiField("utility_contract_reminders", data_type=UtilityContractReminder),
        ApiField("report_event_id"),
        ApiField("report_event", data_type=Event),
    )

    def __init__(
        self,
        id: int,
        name: str,
        facility_id: int,
        status: str,
        start_date: datetime,
        end_date: datetime,
        rate_narrative: str,
        file_id: str,
        created_at: datetime,
        updated_at: datetime,
        created_by: str,
        utility_contract_reminders: list,
        report_event_id: str,
        report_event: Event,
    ) -> None:
        super().__init__()
        self.id = id
        self.name = name
        self.facility_id = facility_id
        self.status = status
        self.start_date = start_date
        self.end_date = end_date
        self.rate_narrative = rate_narrative
        self.file_id = file_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by = created_by
        self.utility_contract_reminders = utility_contract_reminders
        self.report_event_id = report_event_id
        self.report_event = report_event
