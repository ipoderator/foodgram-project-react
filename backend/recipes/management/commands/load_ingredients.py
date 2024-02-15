import logging
from csv import DictReader

from django.core.management.base import BaseCommand
from recipes.models import Ingredient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


class Command(BaseCommand):
    def handle(self, *args, **options):

        ingredient_list = []
        count = 0
        data = open("./data/ingredients.csv", encoding="utf-8")
        for row in DictReader(data):
            name, measurement_unit = row
            ingredient = Ingredient(
                name=name, measurement_unit=measurement_unit
            )
            ingredient_list.append(ingredient)
            count += 1

        Ingredient.objects.bulk_create(ingredient_list)
        logger.info(f"Успешно загружено {count} кол-во ингредиентов")
