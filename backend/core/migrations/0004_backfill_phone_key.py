from django.db import migrations


def fill(apps, schema_editor):
    Lead = apps.get_model("core", "Lead")
    for lead in Lead.objects.only("id", "phone").iterator():
        key = "".join(c for c in (lead.phone or "") if c.isdigit())[-10:]
        Lead.objects.filter(pk=lead.pk).update(phone_key=key)


class Migration(migrations.Migration):
    dependencies = [("core", "0003_improvements")]
    operations = [migrations.RunPython(fill, migrations.RunPython.noop)]
