from app.services.rag.sql_validator import validate_sql


def test_safe_select_is_allowed():
    result = validate_sql('SELECT i.name_en FROM indicators i WHERE i.id = :id LIMIT :row_limit', {'id':'abc','row_limit':10})
    assert result.valid, result.errors


def test_drop_is_rejected():
    result = validate_sql('DROP TABLE users', {})
    assert not result.valid


def test_unapproved_table_is_rejected():
    result = validate_sql('SELECT * FROM users LIMIT 10', {})
    assert not result.valid


def test_multiple_statements_are_rejected():
    result = validate_sql('SELECT * FROM indicators; DELETE FROM indicators', {})
    assert not result.valid


def test_unapproved_column_is_rejected():
    result = validate_sql('SELECT i.password_hash FROM indicators i LIMIT 10', {})
    assert not result.valid
    assert any('Column is not allowed' in error for error in result.errors)


def test_safe_cte_over_allowlisted_columns_is_allowed():
    result = validate_sql(
        'WITH recent AS (SELECT iv.value AS value FROM indicator_values iv) SELECT recent.value FROM recent LIMIT 10',
        {},
    )
    assert result.valid, result.errors
