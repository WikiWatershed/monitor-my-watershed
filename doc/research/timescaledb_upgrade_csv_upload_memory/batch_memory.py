"""Measure the web-app memory of one CSV-upload flush batch.

Serves doc/research/timescaledb-upgrade-csv-upload-memory.md (section "Where the memory goes").
Run from the repo root with any Python >= 3.10, standard library only:

    python -I doc/research/timescaledb_upgrade_csv_upload_memory/batch_memory.py

It rebuilds, outside Django, what SensorDataUploadView.post holds just before a flush
(src/dataloaderservices/views.py at 82baf4d): a list of TimeseriesResultValueTechDebt objects,
then the StringIO that insert_timeseries_result_values_bulk writes for COPY. The class is copied
here verbatim (minus type hints) so the script does not import the app. Values are strings, as
csv.reader yields them; datetimes are distinct objects, as parse_datetime yields them per row.
"""

import tracemalloc
from datetime import datetime, timedelta
from io import StringIO

N_VALUES = 100_001  # the flush fires once the list exceeds 100,000
N_SENSORS = 8  # values per CSV row; one datetime object is shared by a row's values


class TimeseriesResultValueTechDebt:
    def __init__(
        self,
        result_id,
        data_value,
        value_datetime,
        utc_offset,
        censor_code,
        quality_code,
        time_aggregation_interval,
        time_aggregation_interval_unit,
    ):
        self.result_id = result_id
        self.data_value = data_value
        self.utc_offset = utc_offset
        self.value_datetime = value_datetime
        self.censor_code = censor_code
        self.quality_code = quality_code
        self.time_aggregation_interval = time_aggregation_interval
        self.time_aggregation_interval_unit = time_aggregation_interval_unit


def build_batch():
    start = datetime(2024, 1, 1)
    values = []
    row = 0
    while len(values) < N_VALUES:
        dt = start + timedelta(minutes=15 * row) - timedelta(hours=-5)
        for sensor in range(N_SENSORS):
            values.append(
                TimeseriesResultValueTechDebt(
                    result_id=1000 + sensor,
                    data_value=f"{12.3456 + row % 97 + sensor:.4f}",
                    utc_offset=-5,
                    value_datetime=dt,
                    censor_code="Not censored",
                    quality_code="None",
                    time_aggregation_interval=1,
                    time_aggregation_interval_unit=1,
                )
            )
        row += 1
    return values


def build_copy_buffer(values):
    buf = StringIO()
    for rv in values:
        buf.write(
            f"{rv.result_id}\t{rv.data_value}\t"
            f"{rv.value_datetime}\t{rv.utc_offset}\t{rv.censor_code}\t"
            f"{rv.quality_code}\t{rv.time_aggregation_interval}\t"
            f"{rv.time_aggregation_interval_unit}\n"
        )
    buf.seek(0)
    return buf


def main():
    tracemalloc.start()
    values = build_batch()
    list_bytes, _ = tracemalloc.get_traced_memory()
    buf = build_copy_buffer(values)
    both_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    n = len(values)
    text_bytes = len(buf.getvalue().encode())
    mib = 2**20
    print(f"values in batch:                  {n:,}")
    print(f"list of objects:                  {list_bytes / mib:6.1f} MiB  ({list_bytes / n:5.0f} B/value)")
    print(f"list + StringIO:                  {both_bytes / mib:6.1f} MiB")
    print(f"peak while building:              {peak_bytes / mib:6.1f} MiB")
    print(f"COPY text sent to the database:   {text_bytes / mib:6.1f} MiB  ({text_bytes / n:5.0f} B/value)")
    # The same batch as columns: int64 resultid, float64 value, int64 timestamp, int32 offset;
    # the constant text columns need not be materialised per value.
    columnar = n * (8 + 8 + 8 + 4)
    print(f"same batch as typed columns (calc): {columnar / mib:6.1f} MiB  ({columnar / n:5.0f} B/value)")


if __name__ == "__main__":
    main()
