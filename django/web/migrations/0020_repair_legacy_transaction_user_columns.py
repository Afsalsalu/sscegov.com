from django.db import migrations


def ensure_transaction_user_columns(apps, schema_editor):
    """Add missing Django FK columns to legacy transaction tables.

    Older databases contain legacy ``userid``/``user_id`` value columns, but
    the current models also define nullable foreign keys used by the wallet
    summary. Keep the legacy columns intact and add only the missing FK
    columns.
    """
    connection = schema_editor.connection
    repairs = (
        ("Table_DrCrNote", "user"),
        ("Table_Journal_Entry", "auth_user"),
        ("Table_Contra_Entry", "auth_user"),
    )

    existing_tables = set(connection.introspection.table_names())
    for model_name, field_name in repairs:
        model = apps.get_model("web", model_name)
        table_name = model._meta.db_table
        if table_name not in existing_tables:
            continue

        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, table_name
                )
            }

        field = model._meta.get_field(field_name)
        if field.column not in columns:
            schema_editor.add_field(model, field)


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0019_repair_table_voucher_user_column"),
    ]

    operations = [
        migrations.RunPython(
            ensure_transaction_user_columns,
            migrations.RunPython.noop,
        ),
    ]
