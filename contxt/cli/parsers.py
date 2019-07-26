from contxt.utils import make_logger

logger = make_logger(__name__)


def _get_organization_id(name, auth):
    from contxt.services import ContxtService

    contxt_service = ContxtService(auth)
    return contxt_service.get_organization_with_name(name).id


def _to_csv(self, filename, items):
    from csv import DictWriter
    from pathlib import Path

    with Path(filename).open("w") as f:
        writer = DictWriter(f, fieldnames=vars(items[0]))
        writer.writeheader()
        for item in items:
            writer.writerow(vars(item))


class ContxtArgParser:
    def __init__(self, subparsers):
        self.parser = self._init_parser(subparsers)

    def _init_parser(self, subparsers):
        raise NotImplementedError

    def _help(self, args, auth):
        self.parser.print_help()

    def parse(self, args, auth):
        if "func" in args:
            args.func(args, auth)


class AuthParser(ContxtArgParser):
    def _init_parser(self, subparsers):
        parser = subparsers.add_parser("auth", help="Authentication")
        parser.set_defaults(func=self._help)
        _subparsers = parser.add_subparsers(title="subcommands", dest="subcommand")

        # Login
        login_parser = _subparsers.add_parser("login", help="Login to contxt")
        login_parser.set_defaults(func=self._login)

        # Logout
        logout_parser = _subparsers.add_parser("logout", help="Logout of contxt")
        logout_parser.set_defaults(func=self._logout)

        return parser

    def _login(self, args, auth):
        auth.login()

    def _logout(self, args, auth):
        auth.logout()


class IotParser(ContxtArgParser):
    def _init_parser(self, subparsers):
        from contxt.models.iot import Window
        from contxt.utils import datetime_parse

        parser = subparsers.add_parser("iot", help="IOT service")
        parser.set_defaults(func=self._help)
        _subparsers = parser.add_subparsers(title="subcommands", dest="subcommand")

        # Groupings
        groupings_parser = _subparsers.add_parser("groupings", help="Get groupings")
        groupings_parser.add_argument("facility_id", type=int, help="Facility id")
        groupings_parser.set_defaults(func=self._groupings)

        # Feeds
        feeds_parser = _subparsers.add_parser("feeds", help="Get feeds")
        feeds_parser.add_argument("-f", "--facility-id", type=int, help="Facility id")
        feeds_parser.set_defaults(func=self._feeds)

        # Fields
        fields_parser = _subparsers.add_parser("fields", help="Get fields")
        fields_group = fields_parser.add_mutually_exclusive_group(required=True)
        fields_group.add_argument("-f", "--facility-id", type=int, help="Facility id")
        fields_group.add_argument("-g", "--grouping-id", help="Grouping id")
        fields_parser.set_defaults(func=self._fields)

        # Unprovisioned Fields
        unprovisioned_fields_parser = _subparsers.add_parser(
            "unprovisioned", help="Unprovisioned fields"
        )

        feeds_group = unprovisioned_fields_parser.add_mutually_exclusive_group(
            required=True
        )
        feeds_group.add_argument("--feed_key", help="Provide feed key")
        feeds_group.add_argument("--feed_id", type=int, help="Provide feed id")

        unprovisioned_fields_parser.add_argument(
            "--output", help="Dump results to csv if desired"
        )
        unprovisioned_fields_parser.set_defaults(func=self._unprovisioned_fields)

        # Field data
        field_data_parser = _subparsers.add_parser("field-data", help="Get field data")
        field_data_parser.add_argument("grouping_id", help="Grouping id")
        field_data_parser.add_argument(
            "start_time", type=datetime_parse, help="Data start time"
        )
        field_data_parser.add_argument(
            "window", type=Window, help="Data windowing period"
        )
        field_data_parser.add_argument(
            "-e", "--end-time", type=datetime_parse, help="Data end time"
        )
        field_data_parser.add_argument(
            "-p", "--plot", action="store_true", help="Plot data"
        )
        field_data_parser.set_defaults(func=self._field_data)

        return parser

    def _groupings(self, args, auth):
        from contxt.services import IotService

        iot_service = IotService(auth)
        groupings = iot_service.get_field_groupings_for_facility(args.facility_id)
        print(groupings)

    def _feeds(self, args, auth):
        from contxt.services import IotService

        iot_service = IotService(auth)
        feeds = iot_service.get_feeds(args.facility_id)
        print(feeds)

    def _fields(self, args, auth):
        from contxt.services import IotService

        iot_service = IotService(auth)
        if args.facility_id:
            # Get fields for facility
            fields = iot_service.get_fields_for_facility(args.facility_id)
        else:
            # Get fields for grouping
            fields = iot_service.get_field_grouping(args.grouping_id).fields
        print(fields)

    def _unprovisioned_fields(self, args, auth):
        from contxt.services import IotService

        iot_service = IotService(auth)
        fields = (
            iot_service.get_unprovisioned_fields_for_feed_id(args.feed_id)
            if args.feed_id
            else iot_service.get_unprovisioned_fields_for_feed_key(args.feed_key)
        )

        if args.output:
            _to_csv(args.output, fields)
        else:
            print(fields)

    def _field_data(self, args, auth):
        from contxt.services import IotService
        from tqdm import tqdm
        from pandas import DataFrame

        iot_service = IotService(auth)
        fields = iot_service.get_field_grouping(args.grouping_id).fields
        print(
            f"Fetching iot data for {len(fields)} tags for {args.start_time} - {args.end_time}..."
        )
        try:
            field_data = {
                field.field_human_name: {
                    d[0]: d[1]
                    for d in iot_service.get_time_series_for_field(
                        field=field,
                        start_time=args.start_time,
                        end_time=args.end_time,
                        window=args.resolution,
                    )
                }
                for field in tqdm(fields)
            }
        except MemoryError:
            print("ERROR: Ran out of memory. Trying fetching a smaller date range.")

        # Output to csv
        print(f"Writing tag data to {args.output}...")
        df = DataFrame(field_data)
        df.index.name = "timestamp"
        df.to_csv(args.output)



RESOURCE_TYPES = ["electric", "gas", "combined"]


class EmsParser(ContxtArgParser):
    def _init_parser(self, subparsers):
        parser = subparsers.add_parser("ems", help="EMS service")
        parser.set_defaults(func=self._help)
        _subparsers = parser.add_subparsers(title="subcommands", dest="subcommand")

        # Main Services
        mains_parser = _subparsers.add_parser("mains", help="Get Main Services")
        mains_parser.add_argument(
            "facility_id", type=int, help="Facility to get main services for"
        )
        mains_parser.add_argument(
            "--resource_type", choices=RESOURCE_TYPES, help="Filter by type of resource"
        )
        mains_parser.set_defaults(func=self._get_mains)

        # Get Main Service Data
        md_parser = _subparsers.add_parser(
            "main-data", help="Get main service data for a facility"
        )
        md_parser.add_argument("facility_id", type=int, help="Facility ID")
        md_parser.add_argument("resource_type", choices=RESOURCE_TYPES)
        md_parser.add_argument("start_date", help="Start month (YYYY-MM)")
        md_parser.add_argument("end_date", help="End month (YYYY-MM)")
        md_parser.set_defaults(func=self._get_main_data)

        # Spend
        spend_parser = _subparsers.add_parser("util-spend", help="Utility spend")
        spend_parser.add_argument(
            "interval", choices=["daily", "monthly"], help="Time interval"
        )
        spend_parser.add_argument(
            "resource_type", choices=RESOURCE_TYPES, help="Type of resource"
        )
        spend_parser.add_argument("start_date", help="Start month (YYYY-MM)")
        spend_parser.add_argument("end_date", help="End month (YYYY-MM)")

        spend_group = spend_parser.add_mutually_exclusive_group(required=True)
        spend_group.add_argument("-f", "--facility-id", type=int, help="Facility id")
        spend_group.add_argument("-g", "--org-id", help="Organization id")
        spend_group.add_argument("-n", "--org-name", help="Organization name")

        spend_parser.add_argument("-o", "--output", help="Filename to save data (csv)")
        spend_parser.add_argument(
            "-p",
            "--pro-forma",
            action="store_true",
            help="Include pro forma calculations",
        )
        spend_parser.set_defaults(func=self._utility_spend)

        # Usage
        usage_parser = _subparsers.add_parser("util-usage", help="Utility usage")
        usage_parser.add_argument(
            "interval", choices=["daily", "monthly"], help="Time interval"
        )
        usage_parser.add_argument(
            "resource_type",
            choices=["electric", "gas", "combined"],
            help="Type of resource",
        )
        usage_parser.add_argument("start_date", help="Start month (YYYY-MM)")
        usage_parser.add_argument("end_date", help="End month (YYYY-MM)")

        usage_group = usage_parser.add_mutually_exclusive_group(required=True)
        usage_group.add_argument("-f", "--facility-id", type=int, help="Facility id")
        usage_group.add_argument("-g", "--org-id", help="Organization id")
        usage_group.add_argument("-n", "--org-name", help="Organization name")

        usage_parser.add_argument("-o", "--output", help="Filename to save data (csv)")
        usage_parser.add_argument(
            "-p",
            "--pro-forma",
            action="store_true",
            help="Include pro forma calculations",
        )
        usage_parser.set_defaults(func=self._utility_usage)

        # Spend Metric Normalization
        spend_metrics_parser = _subparsers.add_parser(
            "util-spend-metrics", help="Utility spend metrics"
        )

        spend_metrics_parser.add_argument(
            "metric", help="Provide the metric you want to normalize against"
        )
        spend_metrics_parser.add_argument(
            "interval", choices=["daily", "monthly"], help="Time interval"
        )
        spend_metrics_parser.add_argument(
            "resource_type",
            choices=["electric", "gas", "combined"],
            help="Type of resource",
        )
        spend_metrics_parser.add_argument("start_date", help="Start month (YYYY-MM)")
        spend_metrics_parser.add_argument("end_date", help="End month (YYYY-MM)")

        spend_metrics_group = spend_metrics_parser.add_mutually_exclusive_group(
            required=True
        )
        spend_metrics_group.add_argument(
            "-f", "--facility-id", type=int, help="Facility id"
        )
        spend_metrics_group.add_argument("-g", "--org-id", help="Organization id")
        spend_metrics_group.add_argument("-n", "--org-name", help="Organization name")

        spend_metrics_parser.add_argument(
            "-o", "--output", help="Filename to save data (csv)"
        )
        spend_metrics_parser.add_argument(
            "-p",
            "--pro-forma",
            action="store_true",
            help="Include pro forma calculations",
        )
        spend_metrics_parser.add_argument(
            "--metric-scalar",
            type=float,
            help="Optionally scale the normalized metric by a float",
        )
        spend_metrics_parser.set_defaults(func=self._utility_spend_metrics)

        # Usage Metric Normalization
        usage_metrics_parser = _subparsers.add_parser(
            "util-usage-metrics", help="Utility usage metrics"
        )

        usage_metrics_parser.add_argument(
            "metric", help="Provide the metric you want to normalize against"
        )
        usage_metrics_parser.add_argument(
            "interval", choices=["daily", "monthly"], help="Time interval"
        )
        usage_metrics_parser.add_argument(
            "resource_type",
            choices=["electric", "gas", "combined"],
            help="Type of resource",
        )
        usage_metrics_parser.add_argument("start_date", help="Start month (YYYY-MM)")
        usage_metrics_parser.add_argument("end_date", help="End month (YYYY-MM)")

        usage_metrics_group = usage_metrics_parser.add_mutually_exclusive_group(
            required=True
        )
        usage_metrics_group.add_argument(
            "-f", "--facility-id", type=int, help="Facility id"
        )
        usage_metrics_group.add_argument("-g", "--org-id", help="Organization id")
        usage_metrics_group.add_argument("-n", "--org-name", help="Organization name")

        usage_metrics_parser.add_argument(
            "-o", "--output", help="Filename to save data (csv)"
        )
        usage_metrics_parser.add_argument(
            "-p",
            "--pro-forma",
            action="store_true",
            help="Include pro forma calculations",
        )
        usage_metrics_parser.add_argument(
            "--metric-scalar",
            type=float,
            help="Optionally scale the normalized metric by a float",
        )
        usage_metrics_parser.set_defaults(func=self._utility_usage_metrics)

        return parser

    def _get_mains(self, args, auth):
        from contxt.legacy.services.ems import EMSService

        ems = EMSService(auth)

        mains = ems.get_main_services(
            facility_id=args.facility_id, type=args.resource_type
        )
        print(mains)

    def _get_main_data(self, args, auth):
        from contxt.functions.ems import EMS

        ems = EMS(auth)

        data = ems.get_facility_main_data(
            facility_id=args.facility_id,
            resource_type=args.resource_type,
            start_date=args.start_date,
            end_date=args.end_date,
        )

        self.to_csv_main_service_data(data)

    def _utility_spend(self, args, auth):
        from contxt.functions.ems import EMS

        ems = EMS(auth)
        if args.facility_id:
            # Get facility spend
            spend = ems.get_facility_spend(
                facility_id=args.facility_id,
                interval=args.interval,
                resource_type=args.resource_type,
                start_date=args.start_date,
                end_date=args.end_date,
                pro_forma=args.pro_forma,
            )
            print(spend)
        else:
            # Get organization spend
            org_spend = ems.get_organization_spend(
                resource_type=args.resource_type,
                interval=args.interval,
                start_date=args.start_date,
                end_date=args.end_date,
                pro_forma=args.pro_forma,
                organization_id=args.org_id,
                organization_name=args.org_name,
            )

            # always write to file
            ems.write_organization_utility_data_to_file(org_spend, args.output)

    def _utility_usage(self, args, auth):
        from contxt.functions.ems import EMS

        ems = EMS(auth)
        if args.facility_id:
            # get facility usage
            usage = ems.get_facility_usage(
                facility_id=args.facility_id,
                interval=args.interval,
                resource_type=args.resource_type,
                start_date=args.start_date,
                end_date=args.end_date,
                pro_forma=args.pro_forma,
            )
            print(usage)
        else:
            org_usage = ems.get_organization_usage(
                resource_type=args.resource_type,
                interval=args.interval,
                start_date=args.start_date,
                end_date=args.end_date,
                pro_forma=args.pro_forma,
                organization_id=args.org_id,
                organization_name=args.org_name,
            )

            # always write to file
            ems.write_organization_utility_data_to_file(org_usage, args.output)

    def _utility_spend_metrics(self, args, auth):
        from contxt.functions.ems import EMS

        ems = EMS(auth)
        if args.facility_id:
            normalized_spend = ems.get_facility_spend_vs_monthly_metric(
                facility_id=args.facility_id,
                interval=args.interval,
                start_date=args.start_date,
                end_date=args.end_date,
                metric=args.metric,
                resource_type=args.resource_type,
                pro_forma=args.pro_forma,
                metric_scalar=args.metric_scalar or 1,
            )
            self._print_facility_normalized_metrics(normalized_spend, "spend")
        else:

            if not args.output:
                # TODO: this requirement should be enforced by argparse
                logger.critical(
                    "Please provide --output as an argument to specify report"
                    " export file"
                )
                return

            normalized_spend = ems.get_organization_spend_vs_monthly_metric(
                organization_name=args.org_name,
                organization_id=args.org_id,
                metric=args.metric,
                start_date=args.start_date,
                end_date=args.end_date,
                resource_type=args.resource_type,
                pro_forma=args.pro_forma,
                interval=args.interval,
                metric_scalar=args.metric_scalar or 1,
            )
            self.to_csv_organization_normalized_metric(args.output, normalized_spend)

    def _utility_usage_metrics(self, args, auth):
        from contxt.functions.ems import EMS

        ems = EMS(auth)
        if args.facility_id:
            normalized_usage = ems.get_facility_usage_vs_monthly_metric(
                facility_id=args.facility_id,
                interval=args.interval,
                start_date=args.start_date,
                end_date=args.end_date,
                metric=args.metric,
                resource_type=args.resource_type,
                pro_forma=args.pro_forma,
                metric_scalar=args.metric_scalar or 1,
            )
            self._print_facility_normalized_metrics(normalized_usage, "usage")
        else:

            if not args.output:
                # TODO: this requirement should be enforced by argparse
                logger.critical(
                    "Please provide --output as an argument to specify report"
                    " export file"
                )
                return

            normalized_usage = ems.get_organization_usage_vs_monthly_metric(
                organization_name=args.org_name,
                organization_id=args.org_id,
                metric=args.metric,
                start_date=args.start_date,
                end_date=args.end_date,
                resource_type=args.resource_type,
                pro_forma=args.pro_forma,
                interval=args.interval,
                metric_scalar=args.metric_scalar or 1,
            )
            self.to_csv_organization_normalized_metric(args.output, normalized_usage)

    @staticmethod
    def to_csv_main_service_data(main_service_data):
        from csv import DictWriter
        from datetime import datetime
        from pathlib import Path

        output_path = Path(
            f"main_service_export_{datetime.now().strftime('%m-%d_%H_%M_%S')}"
        )
        output_path.mkdir(parents=True, exist_ok=False)

        for service_name, data in main_service_data.items():
            filename = output_path / f"{service_name}.csv"
            with filename.open("w") as f:
                writer = DictWriter(f, fieldnames=["event_time", "value"])
                for row in reversed(data):
                    writer.writerow(row)

    @staticmethod
    def _print_facility_normalized_metrics(normalized_data_by_date, normalization_key):
        from tabulate import tabulate

        normalized_to_print = []

        for date, data in normalized_data_by_date.items():
            # TODO clean this up when we can properly filter metric value data
            # by start->end date
            if normalization_key in data:
                normalized_to_print.append(
                    [
                        date.strftime("%Y-%m"),
                        data[normalization_key],
                        data["metric_value"] if "metric_value" in data else None,
                        data["normalized"],
                        data["pro_forma_date"],
                    ]
                )

        print(
            tabulate(
                normalized_to_print,
                headers=[
                    "date",
                    normalization_key,
                    "metric-value",
                    "normalized",
                    "pro_forma_date",
                ],
            )
        )

    @staticmethod
    def to_csv_organization_normalized_metric(filename, normalized_data_by_facility):
        from csv import DictWriter

        to_csv_data = []

        unique_dates = []
        by_facility = {}

        # gotta organize by date so that all the dates match across facilities
        for facility_name in sorted(normalized_data_by_facility.keys()):
            data = normalized_data_by_facility[facility_name]

            by_facility[facility_name] = {}
            for date, spend in data.items():
                if date not in unique_dates:
                    unique_dates.append(date)

                by_facility[facility_name][date] = spend.get("normalized", "N/A")

        facility_data = {}
        for date in reversed(sorted(unique_dates)):
            for facility_name, date_data in by_facility.items():
                if facility_name not in facility_data:
                    facility_data[facility_name] = {}
                facility_data[facility_name][date] = date_data.get(date)

        for facility, date_dict in facility_data.items():
            date_dict["facility_name"] = facility
            to_csv_data.append(date_dict)

        with open(filename, "w") as f:

            fields = ["facility_name"]
            fields.extend(unique_dates)

            writer = DictWriter(f, fieldnames=fields)
            writer.writeheader()

            for row in to_csv_data:
                writer.writerow(row)


class AssetsParser(ContxtArgParser):
    def _init_parser(self, subparsers):
        parser = subparsers.add_parser("assets", help="Assets service")
        parser.set_defaults(func=self._help)
        _subparsers = parser.add_subparsers(title="subcommands", dest="subcommand")

        # Facilities
        # TODO: do we want this distinct from assets?
        fac_parser = _subparsers.add_parser("facilities", help="Get facility assets")
        fac_group = fac_parser.add_mutually_exclusive_group(required=True)
        fac_group.add_argument("-i", "--org-id", help="Organization id")
        fac_group.add_argument("-n", "--org-name", help="Organization name")
        fac_parser.set_defaults(func=self._facilities)

        # Asset types
        types_parser = _subparsers.add_parser("types", help="Get asset types")
        types_group = types_parser.add_mutually_exclusive_group(required=True)
        types_group.add_argument("-i", "--org-id", help="Organization id")
        types_group.add_argument("-n", "--org-name", help="Organization name")
        types_parser.add_argument("-t", "--type-label", help="Asset type label")
        types_parser.set_defaults(func=self._types)

        # Assets
        assets_parser = _subparsers.add_parser("assets", help="Get assets")
        assets_parser.add_argument("type_label", help="Asset type label")
        assets_group = assets_parser.add_mutually_exclusive_group(required=True)
        assets_group.add_argument("-i", "--org-id", help="Organization id")
        assets_group.add_argument("-n", "--org-name", help="Organization name")
        assets_parser.set_defaults(func=self._assets)

        # TODO: Attributes
        attr_parser = _subparsers.add_parser("attr", help="Get asset attributes")
        attr_parser.set_defaults(func=self._attributes)

        # TODO: Attribute values
        attr_vals_parser = _subparsers.add_parser(
            "attr-vals", help="Get asset attribute values"
        )
        attr_vals_parser.set_defaults(func=self._attribute_values)

        # TODO: Metrics
        metrics_parser = _subparsers.add_parser("metrics", help="Get asset metrics")
        metrics_parser.set_defaults(func=self._metrics)

        # Metric values
        metric_vals_parser = _subparsers.add_parser(
            "metric-vals", help="Get asset metric values"
        )
        metrics_group1 = metric_vals_parser.add_mutually_exclusive_group(required=True)
        metrics_group1.add_argument("-i", "--org_id", help="Organization id")
        metrics_group1.add_argument("-n", "--org_name", help="Organization name")
        metrics_group2 = metric_vals_parser.add_mutually_exclusive_group(required=True)
        metrics_group2.add_argument("-a", "--asset_id", help="Asset id")
        metrics_group2.add_argument("-t", "--type_label", help="Asset type label")
        metric_vals_parser.add_argument(
            "--metric_label", nargs="+", help="Metric label"
        )
        metric_vals_parser.add_argument(
            "-p", "--plot", action="store_true", help="Plot the values"
        )
        metric_vals_parser.set_defaults(func=self._metric_values)

        return parser

    def _facilities(self, args, auth):
        from contxt.services import FacilitiesService

        facilites_service = FacilitiesService(auth)

        organization_id = args.org_id or _get_organization_id(args.org_name, auth)
        facilities = facilites_service.get_facilities(organization_id)
        print(facilities)

    def _types(self, args, auth):
        from contxt.services import AssetsService

        organization_id = args.org_id or _get_organization_id(args.org_name, auth)
        assets_service = AssetsService(auth, organization_id)

        if not args.type_label:
            # Get all asset types
            asset_types = assets_service.types_by_id.values()
            print(asset_types)
        else:
            # Get single asset type
            asset_type = assets_service.asset_type_with_label(args.type_label)
            assets_service._cache_asset_type_full(asset_type)
            print(asset_type)

    def _assets(self, args, auth):
        from contxt.services import AssetsService

        organization_id = args.org_id or _get_organization_id(args.org_name, auth)
        assets_service = AssetsService(auth, organization_id)
        asset_type = assets_service.asset_type_with_label(args.type_label)
        assets = assets_service.get_assets(asset_type.id)
        print(assets)

    def _attributes(self, args, auth):
        raise NotImplementedError

    def _attribute_values(self, args, auth):
        raise NotImplementedError

    def _metrics(self, args, auth):
        raise NotImplementedError

    def _metric_values(self, args, auth):
        from contxt.services import AssetsService

        organization_id = args.org_id or _get_organization_id(args.org_name, auth)
        assets_service = AssetsService(auth, organization_id)

        if args.asset_id:
            # Get metric values for single asset
            asset = assets_service.get_complete_asset(args.asset_id)
            print(asset.metrics)
        else:
            # Get metric values for all assets of the specified type(s)
            asset_type = assets_service.asset_type_with_label(args.type_label)
            metrics = [
                assets_service.get_complete_asset(asset.id).metrics
                for asset in assets_service.get_assets(asset_type.id)
            ]
            if args.plot:
                raise NotImplementedError
            else:
                print(metrics)


class ContxtParser(ContxtArgParser):
    def _init_parser(self, subparsers):
        parser = subparsers.add_parser("contxt", help="Contxt service")
        parser.set_defaults(func=self._help)
        _subparsers = parser.add_subparsers(title="subcommands", dest="subcommand")

        # Organizations
        orgs_parser = _subparsers.add_parser("orgs", help="Get organizations")
        orgs_parser.set_defaults(func=self._organizations)

        # Make organization
        create_org_parser = _subparsers.add_parser("mk-org", help="Create organization")
        create_org_parser.add_argument("org_name", help="Organization name")
        create_org_parser.set_defaults(func=self._create_organization)

        # Users
        users_parser = _subparsers.add_parser("users", help="Get users")
        users_group = users_parser.add_mutually_exclusive_group(required=True)
        users_group.add_argument("-i", "--org-id", help="Organization id")
        users_group.add_argument("-n", "--org-name", help="Organization name")
        users_parser.set_defaults(func=self._users)

        # Add users
        add_user_parser = _subparsers.add_parser(
            "add-user", help="Add user to an organization"
        )
        add_user_parser.add_argument("org_id", help="Organization id")
        add_user_parser.add_argument("user_id", help="User id")
        add_user_parser.set_defaults(func=self._add_user)

        return parser

    def _organizations(self, args, auth):
        from contxt.services.contxt import ContxtService
        from contxt.utils.serializer import Serializer

        contxt_service = ContxtService(auth)
        orgs = contxt_service.get_organizations()
        print(Serializer.to_table(orgs))

    def _create_organization(self, args, auth):
        from contxt.services import ContxtService
        from contxt.models.contxt import Organization

        contxt_service = ContxtService(auth)
        org = contxt_service.create_organization(Organization(args.org_name))
        contxt_service.add_user_to_organization(
            user_id=auth.user_id, organization_id=org.id
        )
        print(org)

    def _users(self, args, auth):
        from contxt.services import ContxtService

        contxt_service = ContxtService(auth)
        organization_id = args.org_id or _get_organization_id(args.org_name, auth)
        users = contxt_service.get_users_for_organization(organization_id)
        print(users)

    def _add_user(self, args, auth):
        from contxt.services.contxt import ContxtService

        contxt_service = ContxtService(auth)
        contxt_service.add_user_to_organization(
            user_id=args.user_id, organization_id=args.org_id
        )


class BusParser(ContxtArgParser):
    def _init_parser(self, subparsers):
        parser = subparsers.add_parser("bus", help="Message bus service")
        parser.set_defaults(func=self._help)
        _subparsers = parser.add_subparsers(title="subcommands", dest="subcommand")

        # Channels
        channel_parser = _subparsers.add_parser("channels", help="Get channels")
        channel_group = channel_parser.add_mutually_exclusive_group(required=True)
        channel_group.add_argument("-I", "--org-id", help="Organization id")
        channel_group.add_argument("-N", "--org-name", help="Organization name")
        channel_parser.add_argument("service_id", help="Service id")
        channel_parser.set_defaults(func=self._channels)

        # Stats
        stats_parser = _subparsers.add_parser(
            "stats", help="View Message Bus Channel statistics"
        )
        stats_organization_group = stats_parser.add_mutually_exclusive_group(
            required=True
        )
        stats_organization_group.add_argument("-I", "--org-id", help="Organization id")
        stats_organization_group.add_argument(
            "-N", "--org-name", help="Organization name"
        )
        stats_channel_group = stats_parser.add_mutually_exclusive_group(required=True)
        stats_channel_group.add_argument("-i", "--channel-id", help="Channel id")
        stats_channel_group.add_argument("-n", "--channel-name", help="Channel name")
        stats_parser.add_argument("service_id", help="Service id")
        stats_parser.set_defaults(func=self._stats)

        return parser

    def _channels(self, args, auth):
        from contxt.services import MessageBusService
        from contxt.utils.serializer import Serializer

        organization_id = args.org_id or _get_organization_id(args.org_name, auth)
        bus_service = MessageBusService(auth, organization_id)
        channels = bus_service.get_channels_for_service(args.service_id)
        print(Serializer.to_table(channels))

    def _stats(self, args, auth):
        from contxt.services import MessageBusService

        organization_id = args.org_id or _get_organization_id(args.org_name, auth)
        bus_service = MessageBusService(auth, organization_id)
        channel_id = (
            args.channel_id
            or bus_service.get_channel_with_name_for_service(
                channel_name=args.channel_name, service_id=args.service_id
            ).id
        )
        stats = bus_service.get_stats_for_channel_and_service(
            channel_id=channel_id, service_id=args.service_id
        )
        print(stats)
