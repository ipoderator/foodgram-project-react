import django_filters as filters
from rest_framework.filters import SearchFilter

from recipes.models import Ingredient, Recipe
from users.models import User


class IngredientFilter(SearchFilter):
    """Фильтрация ингридиентов."""

    name = filters.CharFilter(lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(filters.FilterSet):
    """Фильтрация рецептов."""
    RECIPE_CHOICES = (
        (0, 'Not_In_List'),
        (1, 'In_List'),
    )
    author = filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )
    is_in_shopping_cart = filters.ChoiceFilter(
        choices=RECIPE_CHOICES,
        method='get_is_in'
    )
    is_favorited = filters.ChoiceFilter(
        choices=RECIPE_CHOICES,
        method='get_is_in'
    )
    tags = filters.AllValuesMultipleFilter(
        field_name='tags__slug',
        label='Ссылка'
    )

    def get_is_in(self, queryset: list, name: str, value: str):
        """
        Фильтрация рецептов по избранному и списку покупок.
        """
        user = self.request.user
        if user.is_authenticated:
            if value == '1':
                if name == 'is_favorited':
                    queryset = queryset.filter(favorite_recipes__user=user)
        return queryset

    class Meta:
        model = Recipe
        fields = ('is_favorited', 'is_in_shopping_cart', 'author', 'tags')
