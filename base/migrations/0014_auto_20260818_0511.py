from django.db import migrations


def copy_day_locations(
    apps,
    schema_editor,
):

    Day = apps.get_model(
        "base",
        "Day",
    )

    DayLocation = apps.get_model(
        "base",
        "DayLocation",
    )

    for day in Day.objects.all():

        location_order = 1

        for location in day.locations.all():

            DayLocation.objects.get_or_create(
                day_id=day.pk,
                location_id=location.pk,
                defaults={
                    "location_order": (
                        location_order
                    ),
                },
            )

            location_order += 1


def reverse_copy_day_locations(
    apps,
    schema_editor,
):

    DayLocation = apps.get_model(
        "base",
        "DayLocation",
    )

    DayLocation.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "base",
            "0013_daylocation",
        ),
    ]

    operations = [
        migrations.RunPython(
            copy_day_locations,
            reverse_copy_day_locations,
        ),
    ]