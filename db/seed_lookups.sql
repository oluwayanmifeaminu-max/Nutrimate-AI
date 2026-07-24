-- Fixed vocabulary tables. Kept in sync with the frontend:
--   Frontend/src/data/content.jsx -> DIET_LIST, ALLERGY_LIST

INSERT INTO cook_time_categories (id, label, min_minutes, max_minutes) VALUES
  ('fast',         'Fast cook',    5, 10),
  ('intermediate', 'Intermediate', 30, 60),
  ('long',         'Long cook',    60, 120);

INSERT INTO allergens (name) VALUES
  ('Peanuts'),
  ('Shellfish'),
  ('Dairy'),
  ('Gluten'),
  ('Eggs'),
  ('Soy');

INSERT INTO dietary_tags (name) VALUES
  ('Vegetarian'),
  ('Vegan'),
  ('Halal'),
  ('High Protein'),
  ('Low Carb'),
  ('Gluten Free');
