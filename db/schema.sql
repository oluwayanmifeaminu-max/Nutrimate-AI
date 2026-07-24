-- NutriMate AI — core database schema (SQLite)
--
-- This is the database Gemma's tool functions query:
--   get_foods(cook_time_category, pantry | list, preference, allergy)
--   get_recipe(food)
--   calculator()             -- pure compute over foods/ingredients, no dedicated table
--   get_shoplist_price()     -- sums ingredients.avg_price_naira for missing pantry items
--
-- Design notes:
--   - Allergens and dietary tags are normalized lookup tables (not free-text) so
--     get_foods can filter with plain joins/excludes instead of string matching.
--   - Their fixed vocabularies are seeded in seed_lookups.sql and are kept in sync
--     with the frontend's ALLERGY_LIST / DIET_LIST (Frontend/src/data/content.jsx).
--   - cook_time_category is a lookup table (not a CHECK constraint) so the exact
--     minute ranges from the "cook:" legend live in one place and are queryable.

PRAGMA foreign_keys = ON;

-- Fast / Intermediate / Long, per the whiteboard's cook-time legend.
CREATE TABLE cook_time_categories (
  id          TEXT PRIMARY KEY,   -- 'fast' | 'intermediate' | 'long'
  label       TEXT NOT NULL,
  min_minutes INTEGER NOT NULL,
  max_minutes INTEGER NOT NULL
);

CREATE TABLE allergens (
  id   INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE dietary_tags (
  id   INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

-- Reusable, priced ingredients — the building blocks of every food.
CREATE TABLE ingredients (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  name             TEXT NOT NULL UNIQUE,
  category         TEXT NOT NULL CHECK (category IN (
                      'grains','legumes','protein','vegetables','fruits',
                      'dairy','oils','spices','tubers','other'
                    )),
  default_unit     TEXT NOT NULL,        -- 'cup', 'kg', 'piece', 'bunch', 'tin', 'ml', ...
  avg_price_naira  REAL NOT NULL,        -- price per one default_unit
  shelf_life_days  INTEGER,              -- NULL = pantry-stable (rice, garri, seasoning...)
  notes            TEXT
);

-- A cookable dish, e.g. "Jollof Rice & Beans".
CREATE TABLE foods (
  id                    INTEGER PRIMARY KEY AUTOINCREMENT,
  name                  TEXT NOT NULL UNIQUE,
  meal_type             TEXT NOT NULL CHECK (meal_type IN ('breakfast','lunch','dinner','snack')),
  cook_time_category_id TEXT NOT NULL REFERENCES cook_time_categories(id),
  prep_time_minutes     INTEGER NOT NULL,
  calories              INTEGER NOT NULL,
  protein_g             REAL NOT NULL,
  carbs_g               REAL NOT NULL,
  fat_g                 REAL NOT NULL,
  fiber_g               REAL,
  estimated_cost_naira  INTEGER NOT NULL,   -- total cost to make `serves` portions
  serves                INTEGER NOT NULL DEFAULT 1,
  region                TEXT,               -- e.g. 'Yoruba', 'Igbo', 'Northern', 'Nationwide'
  instructions_summary  TEXT,               -- one-paragraph summary; see recipe_steps for detail
  notes                 TEXT,
  created_at            TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Food <-> ingredient, many-to-many, with quantities.
CREATE TABLE food_ingredients (
  food_id       INTEGER NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
  ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
  quantity      REAL NOT NULL,
  unit          TEXT NOT NULL,
  is_optional   INTEGER NOT NULL DEFAULT 0,  -- 0 = required, 1 = optional/garnish
  PRIMARY KEY (food_id, ingredient_id)
);

CREATE TABLE food_allergens (
  food_id     INTEGER NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
  allergen_id INTEGER NOT NULL REFERENCES allergens(id) ON DELETE CASCADE,
  PRIMARY KEY (food_id, allergen_id)
);

CREATE TABLE food_dietary_tags (
  food_id INTEGER NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
  tag_id  INTEGER NOT NULL REFERENCES dietary_tags(id) ON DELETE CASCADE,
  PRIMARY KEY (food_id, tag_id)
);

-- Ordered recipe steps, so get_recipe(food) can return real instructions.
CREATE TABLE recipe_steps (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  food_id       INTEGER NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
  step_number   INTEGER NOT NULL,
  instruction   TEXT NOT NULL,
  UNIQUE (food_id, step_number)
);

CREATE INDEX idx_foods_cook_time      ON foods(cook_time_category_id);
CREATE INDEX idx_foods_meal_type      ON foods(meal_type);
CREATE INDEX idx_food_ingredients_ing ON food_ingredients(ingredient_id);
CREATE INDEX idx_food_allergens_alg   ON food_allergens(allergen_id);
CREATE INDEX idx_food_dietary_tags_t  ON food_dietary_tags(tag_id);
