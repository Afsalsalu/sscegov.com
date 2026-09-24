from django.db import migrations


def ensure_table_voucher_user_column(apps, schema_editor):
    """Repair databases created from the legacy Table_Voucher schema.

    The current model has always described ``user`` as a nullable foreign key,
    but some existing databases only contain the older ``UserID`` text column.
    Keep that legacy column intact and add the Django-managed FK column when it
    is missing.
    """
    table_voucher = apps.get_model("web", "Table_Voucher")
    connection = schema_editor.connection
    table_name = table_voucher._meta.db_table

    if table_name not in connection.introspection.table_names():
        return

    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, table_name
            )
        }

    user_field = table_voucher._meta.get_field("user")
    if user_field.column not in columns:
        schema_editor.add_field(table_voucher, user_field)


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0018_addstate_whatsapp_enabled_addstate_whatsapp_number"),
    ]

    operations = [
        migrations.RunPython(
            ensure_table_voucher_user_column,
            migrations.RunPython.noop,
        ),
    ]
