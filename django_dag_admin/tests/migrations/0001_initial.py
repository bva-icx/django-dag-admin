# Generated by Django 2.2 on 2021-04-08 10:18

from django.db import migrations, models
import django.db.models.deletion
import django_dag.models.backends.standard


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ConcreteEdge',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=32, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ConcreteNode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=32)),
                ('children', models.ManyToManyField(blank=True, related_name='parents', through='tests.ConcreteEdge', to='tests.ConcreteNode')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, django_dag.models.backends.standard.ProtoNode),
        ),
        migrations.AddField(
            model_name='concreteedge',
            name='child',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parent_concreteedge_set', related_query_name='parent_concreteedges', to='tests.ConcreteNode'),
        ),
        migrations.AddField(
            model_name='concreteedge',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='child_concreteedge_set', related_query_name='child_concreteedges', to='tests.ConcreteNode'),
        ),
    ]