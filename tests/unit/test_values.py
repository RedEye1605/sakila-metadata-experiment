from datetime import date, datetime, timedelta
from decimal import Decimal

from sakila_experiment.db.values import encode_value


def test_encoding_preserves_null_text_binary_and_numeric_distinctions():
    assert encode_value(None) != encode_value("NULL")
    assert encode_value(Decimal("1.00")) == encode_value(1)
    assert encode_value(Decimal("0.100000000000000000000000000001"))[1] == "0.100000000000000000000000000001"
    assert encode_value(b"\x00\xff")[0] == "bytes"
    assert encode_value(date(2005, 1, 1)) != encode_value(datetime(2005, 1, 1))
    assert encode_value(timedelta(hours=-25))[1] == -25 * 3600 * 1000000

from sakila_experiment.db.values import decode_value


def test_tagged_values_round_trip_for_stored_prediction_reevaluation():
    from datetime import date, datetime, time, timedelta
    from decimal import Decimal
    from sakila_experiment.db.values import encode_value
    import pytest
    for value in (None, 1, Decimal("1.234567890123456789"), 1.25, "NULL", b"\x00\xff", date(2026, 1, 2), datetime(2026, 1, 2, 3, 4), time(3, 4), timedelta(days=-1, microseconds=3)):
        assert encode_value(decode_value(encode_value(value))) == encode_value(value)
    for bad in (["number", "NaN"], ["float", "inf"], ["null", "0"], ["bytes", "!"], ["unknown", "x"]):
        with pytest.raises(ValueError): decode_value(bad)
