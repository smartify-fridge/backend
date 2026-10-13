# Rough refrigerated shelf life per category, in days. These are conservative
# defaults loosely based on USDA FoodKeeper guidance -- review before relying on
# them. Set an item's expires_at to override for a specific item.
SHELF_LIFE_DAYS = {
    "Meat": 2,
    "Seafood": 2,
    "Dairy": 7,
    "Eggs": 21,
    "Fruit": 5,
    "Vegetable": 5,
    "Bakery": 5,
    "Leftovers": 3,
    "Beverage": 7,
    "Condiment": 60,
    "Other": None, # unknown, status will be "unknown" unless expires_at is set
}

CATEGORIES = list(SHELF_LIFE_DAYS)

# fallback when the cv service doesn't return a category
NAME_TO_CATEGORY = {
    "beef": "Meat", "steak": "Meat", "chicken": "Meat", "pork": "Meat",
    "bacon": "Meat", "ham": "Meat", "sausage": "Meat", "turkey": "Meat",
    "fish": "Seafood", "salmon": "Seafood", "tuna": "Seafood", "shrimp": "Seafood",
    "milk": "Dairy", "cheese": "Dairy", "yogurt": "Dairy", "butter": "Dairy", "cream": "Dairy",
    "egg": "Eggs", "eggs": "Eggs",
    "apple": "Fruit", "banana": "Fruit", "orange": "Fruit", "grapes": "Fruit",
    "strawberry": "Fruit", "strawberries": "Fruit", "lemon": "Fruit", "lime": "Fruit",
    "carrot": "Vegetable", "carrots": "Vegetable", "lettuce": "Vegetable", "broccoli": "Vegetable",
    "tomato": "Vegetable", "pepper": "Vegetable", "cucumber": "Vegetable", "spinach": "Vegetable",
    "bread": "Bakery", "tortilla": "Bakery",
    "juice": "Beverage", "soda": "Beverage", "water": "Beverage", "beer": "Beverage",
    "ketchup": "Condiment", "mustard": "Condiment", "mayonnaise": "Condiment", "jam": "Condiment",
}


def categorize(name):
    return NAME_TO_CATEGORY.get(name.strip().lower(), "Other")


def normalize(category):
    """Match a category case-insensitively, falling back to Other."""
    for c in CATEGORIES:
        if c.lower() == (category or "").strip().lower():
            return c
    return "Other"
