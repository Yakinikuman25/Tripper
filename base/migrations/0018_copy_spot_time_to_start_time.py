from django.db import migrations


def copy_spot_time_to_start_time(
    apps,
    schema_editor,
):

    Spot = apps.get_model(
        "base",
        "Spot",
    )

    # =====================================
    # 旧timeからstart_timeへコピー
    #
    # start_timeがまだ空欄の場合だけ
    # 旧timeを引き継ぐ
    # =====================================

    for spot in Spot.objects.all():

        if (
            spot.start_time is None
            and spot.time is not None
        ):

            spot.start_time = spot.time

            spot.save(
                update_fields=[
                    "start_time",
                ]
            )


def reverse_copy_spot_time(
    apps,
    schema_editor,
):

    Spot = apps.get_model(
        "base",
        "Spot",
    )

    # =====================================
    # migrateを戻した場合
    # start_timeから旧timeへ戻す
    # =====================================

    for spot in Spot.objects.all():

        if (
            spot.time is None
            and spot.start_time is not None
        ):

            spot.time = spot.start_time

            spot.save(
                update_fields=[
                    "time",
                ]
            )


class Migration(migrations.Migration):

    dependencies = [
        (
            "base",
            "0017_alter_spot_options_spot_end_time_spot_start_time_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(
            copy_spot_time_to_start_time,
            reverse_copy_spot_time,
        ),
    ]