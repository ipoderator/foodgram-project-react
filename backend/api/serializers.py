import base64

from django.core.files.base import ContentFile
from django.db import transaction
from djoser.serializers import UserSerializer

from foodgram.settings import (MAX_COOKING_TIME, MAX_INGREDIENT_AMOUNT,
                               MIN_COOKING_TIME, MIN_INGREDIENT_AMOUNT)
from recipes.models import (Favorite, Ingredient, IngredientAmount, Recipe,
                            ShoppingCart, Tag)
from rest_framework import serializers
from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import ValidationError
from users.models import Subscribe, User


class Base64ImageField(serializers.ImageField):
    """Изображения."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class UserReadSerializer(UserSerializer):
    """Страница пользователя."""
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name',
                  'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscribe.objects.filter(
                user=request.user,
                author=obj).exists()
        return False


class IngredientSerializer(serializers.ModelSerializer):
    """Ингредиенты."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientsInRecipeSerializer(serializers.ModelSerializer):
    """Игредиенты в рецепте."""
    id = serializers.ReadOnlyField(
        source='ingredient.id',
    )
    name = serializers.ReadOnlyField(
        source='ingredient.name',
    )
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit',
    )

    class Meta:
        model = IngredientAmount
        fields = ('id', 'name', 'measurement_unit', 'amount')


class IngredientInRecipeWriteSerializer(serializers.ModelSerializer):
    """Игредиенты в рецепте."""
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = IngredientAmount
        fields = ('id', 'amount')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор модели тега."""

    class Meta:
        model = Tag
        fields = (
            'id',
            'name',
            'color',
            'slug',
        )
        read_only_fields = (
            'id',
            'name',
            'color',
            'slug',
        )


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Серилизатор для создания рецепта."""
    image = Base64ImageField()
    author = SlugRelatedField(
        slug_field='username',
        read_only=True
    )
    ingredients = IngredientInRecipeWriteSerializer(
        many=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )

    class Meta:
        model = Recipe
        fields = ('id', 'ingredients', 'tags',
                  'image', 'name', 'text',
                  'cooking_time', 'author')

    def create_ingredients_amount(self, ingredients: str, recipe: str):
        IngredientAmount.objects.bulk_create([
            IngredientAmount(
                ingredient=ingredient.get('id'),
                recipe=recipe,
                amount=ingredient.get('amount')
            )
            for ingredient in ingredients
        ])

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients_amount(ingredients, recipe)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        recipe = instance
        instance.image = validated_data.get('image', instance.image)
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.name)
        instance.cooking_time = validated_data.get('cooking_time',
                                                   instance.cooking_time)
        tags = validated_data.get('tags')
        if tags is not None:
            instance.tags.clear()
            instance.tags.set(tags)
        ingredients = validated_data.get('ingredients')
        if ingredients is not None:
            instance.ingredients.clear()
            IngredientAmount.objects.filter(recipe=recipe).delete()
            self.create_ingredients_amount(ingredients, recipe)
        instance.save()
        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context={
            'request': self.context.get('request')
        }).data

    def validate_min_max_ingredients(self, ingredients):
        if len(ingredients) < MIN_INGREDIENT_AMOUNT:
            raise ValidationError(f'Минимальное количество ингредиентов:'
                                  f'{MIN_INGREDIENT_AMOUNT}')
        if len(ingredients) > MAX_INGREDIENT_AMOUNT:
            raise ValidationError(f'Максимальное количество ингредиентов:'
                                  f'{MAX_INGREDIENT_AMOUNT}')
        return ingredients

    def validate_cooking_time(self, cooking_time: int):
        if cooking_time < MIN_COOKING_TIME:
            raise ValidationError(f'Минимальное время готовки:'
                                  f'{MIN_COOKING_TIME} минута')
        if cooking_time > MAX_COOKING_TIME:
            raise ValidationError(f'Максимальное время готовки:'
                                  f'{MAX_COOKING_TIME} минут (10 часов)')
        return cooking_time

    def validate_duplicate_ingredients(self, ingredients: str):
        if not ingredients:
            raise ValidationError('Нельзя создать рецепт без ингредиента')
        return ingredients

    def ingredients_no_repeated(self, ingredients: str):
        attrs_data = [attr.get('id') for attr in ingredients]
        if len(attrs_data) != len(set(attrs_data)):
            raise ValidationError('Ингредиенты для рецепта'
                                  'не должны повторяться')


class RecipeSerializer(serializers.ModelSerializer):
    """Серилизатор рецептов."""
    image = Base64ImageField(read_only=True)
    name = serializers.ReadOnlyField()
    cooking_time = serializers.ReadOnlyField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Игредиенты в рецепте."""
    id = serializers.ReadOnlyField(
        source='ingredient.id'
    )
    name = serializers.ReadOnlyField(
        source='ingredient.name'
    )
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientAmount
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeShopSerializer(serializers.ModelSerializer):
    """Cериализатор для списка покупок."""
    name = serializers.ReadOnlyField()
    cooking_time = serializers.ReadOnlyField()
    image = Base64ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Просмотр рецепта."""
    tags = TagSerializer(
        many=True,
    )
    ingredients = IngredientsInRecipeSerializer(
        many=True,
        source='recipes'
    )
    author = UserReadSerializer()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited',
            'name', 'image', 'text', 'cooking_time',
            'is_in_shopping_cart',
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request.user.is_anonymous:
            return False
        return Favorite.objects.filter(recipe=obj,
                                       user=request.user).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(recipe=obj,
                                           user=request.user).exists()


class SubscribeSerializer(serializers.ModelSerializer):
    """
    Данные о пользователе, на которого
    сделана подписка.
    """
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()

    def get_is_subscribed(self, obj):
        if (self.context.get('request')
           and not self.context['request'].user.is_anonymous):
            return Subscribe.objects.filter(user=self.context['request'].user,
                                            author=obj).exists()
        return False

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit_recipes = request.query_params.get('recipes_limit')
        if limit_recipes is not None:
            recipes = obj.author.all()[:(int(limit_recipes))]
        else:
            recipes = obj.favorite_recipes.all()
        context = {'request': request}
        return RecipeShortSerializer(recipes, many=True,
                                     context=context).data


class RecipeShortSerializer(serializers.ModelSerializer):
    """Класс сериализатора для представления краткой версии рецепта."""
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )
