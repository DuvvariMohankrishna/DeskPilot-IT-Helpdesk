from django.db import migrations

# Older seed data / manual inserts may have stored "Available" or "In Progress" instead of
# the canonical "AVAILABLE" / "IN_PROGRESS". The workflow code compares exact values, so tidy them up.
FIELDS = {
    'Asset': {'status': {'AVAILABLE', 'ASSIGNED', 'MAINTENANCE', 'DAMAGED', 'LOST', 'RETIRED'}},
    'Ticket': {
        'status': {'NEW', 'ASSIGNED', 'IN_PROGRESS', 'PENDING', 'RESOLVED', 'CLOSED', 'REOPENED'},
        'priority': {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'},
    },
    'AssetMaintenance': {'result': {'OPEN', 'COMPLETED'}},
    'User': {'role': {'ADMIN', 'AGENT', 'EMPLOYEE'}},
}
ALIASES = {'UNDER_MAINTENANCE': 'MAINTENANCE', 'IN_USE': 'ASSIGNED', 'ON_HOLD': 'PENDING', 'DONE': 'COMPLETED'}


def normalize(apps, schema_editor):
    for model_name, fields in FIELDS.items():
        Model = apps.get_model('core', model_name)
        for field, valid in fields.items():
            for value in Model.objects.values_list(field, flat=True).distinct():
                if value in valid or not value:
                    continue
                fixed = value.strip().upper().replace(' ', '_').replace('-', '_')
                fixed = ALIASES.get(fixed, fixed)
                if fixed in valid:
                    Model.objects.filter(**{field: value}).update(**{field: fixed})


class Migration(migrations.Migration):
    dependencies = [('core', '0002_deskpilot_workflow_upgrade')]
    operations = [migrations.RunPython(normalize, migrations.RunPython.noop)]
